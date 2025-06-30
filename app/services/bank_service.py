"""
Bank service for handling transactions and Teller integration
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from difflib import SequenceMatcher
from ..config import Config

logger = logging.getLogger(__name__)

class BankService:
    """Service for handling bank transactions and Teller integration"""
    
    def __init__(self, db_client, teller_client):
        self.db = db_client
        self.teller = teller_client
    
    def _find_matching_csv_transaction(self, teller_tx: Dict, user_id: str) -> Optional[Dict]:
        """Find matching CSV transaction for a Teller transaction"""
        try:
            # Get potential matches based on amount and date
            amount = teller_tx.get('amount')
            date = teller_tx.get('date')
            description = teller_tx.get('description', '').lower()
            
            if not amount or not date:
                return None
            
            # Convert date to datetime if it's a string
            if isinstance(date, str):
                try:
                    date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                except:
                    return None
            
            # Look for CSV transactions with same amount and similar date (±3 days)
            date_start = date - timedelta(days=3)
            date_end = date + timedelta(days=3)
            
            csv_transactions = list(self.db.client.db.bank_transactions.find({
                'user_id': user_id,
                'source': 'csv_upload',
                'amount': amount,
                'date': {
                    '$gte': date_start,
                    '$lte': date_end
                }
            }))
            
            if not csv_transactions:
                return None
            
            # Find best match based on description similarity
            best_match = None
            best_score = 0
            
            for csv_tx in csv_transactions:
                csv_description = csv_tx.get('description', '').lower()
                
                # Calculate similarity score
                similarity = SequenceMatcher(None, description, csv_description).ratio()
                
                # Bonus for exact amount match
                if abs(csv_tx.get('amount', 0) - amount) < 0.01:
                    similarity += 0.1
                
                # Bonus for exact date match
                csv_date = csv_tx.get('date')
                if isinstance(csv_date, datetime) and abs((csv_date - date).days) == 0:
                    similarity += 0.1
                
                if similarity > best_score and similarity > 0.6:  # Minimum 60% similarity
                    best_score = similarity
                    best_match = csv_tx
            
            return best_match
            
        except Exception as e:
            logger.error(f"Error finding matching CSV transaction: {e}")
            return None
    
    def _merge_transaction_data(self, teller_tx: Dict, csv_tx: Dict) -> Dict:
        """Merge Teller and CSV transaction data, preferring Teller data"""
        merged = teller_tx.copy()
        
        # Keep CSV data that might be more detailed
        if csv_tx.get('category') and not merged.get('category'):
            merged['category'] = csv_tx['category']
        
        if csv_tx.get('merchant') and not merged.get('merchant'):
            merged['merchant'] = csv_tx['merchant']
        
        # Mark as matched
        merged['csv_matched'] = True
        merged['csv_transaction_id'] = csv_tx.get('transaction_id')
        merged['matched_at'] = datetime.now()
        
        return merged
    
    def sync_transactions(self, start_date: str = None, end_date: str = None) -> Dict:
        """Sync bank transactions with proper error handling and smart CSV matching"""
        try:
            if not self.db or not hasattr(self.db, 'client') or not self.db.client:
                return {"success": False, "error": "Database not connected"}
            
            # Get active Teller tokens
            tokens = self.db.get_teller_tokens()
            if not tokens:
                return {"success": False, "error": "No active bank connections"}
            
            total_transactions = 0
            new_transactions = 0
            matched_transactions = 0
            synced_accounts = []
            
            for token_record in tokens:
                access_token = token_record.get('access_token')
                user_id = token_record.get('user_id')
                
                if not access_token:
                    continue
                
                try:
                    # Validate token first
                    if not self.teller.validate_token(access_token):
                        logger.warning(f"Invalid token for user {user_id}")
                        continue
                    
                    # Get accounts for this token
                    accounts = self.teller.get_accounts(access_token)
                    
                    for account in accounts:
                        account_id = account.get('id')
                        if not account_id:
                            continue
                        
                        # Get transactions for this account
                        transactions = self.teller.get_transactions(
                            access_token,
                            account_id,
                            start_date,
                            end_date
                        )
                        
                        if transactions and isinstance(transactions, list):
                            # Process and store transactions
                            for tx in transactions:
                                # Add user_id, account info, and token info
                                tx['user_id'] = user_id
                                tx['token_id'] = token_record.get('_id')
                                tx['account_id'] = account_id
                                tx['account_name'] = account.get('name')
                                tx['institution_name'] = account.get('institution', {}).get('name')
                                tx['imported_at'] = datetime.now()
                                tx['source'] = 'teller'
                                
                                # Check if transaction already exists (exact match)
                                existing = self.db.client.db.bank_transactions.find_one({
                                    'transaction_id': tx.get('id'),
                                    'user_id': user_id,
                                    'account_id': account_id
                                })
                                
                                if existing:
                                    # Update existing transaction
                                    self.db.client.db.bank_transactions.update_one(
                                        {'_id': existing['_id']},
                                        {'$set': tx}
                                    )
                                    total_transactions += 1
                                else:
                                    # Check for smart matching with CSV transactions
                                    matching_csv = self._find_matching_csv_transaction(tx, user_id)
                                    
                                    if matching_csv:
                                        # Merge Teller and CSV data
                                        merged_tx = self._merge_transaction_data(tx, matching_csv)
                                        merged_tx['transaction_id'] = tx.get('id')  # Use Teller ID as primary
                                        
                                        # Insert merged transaction
                                        self.db.client.db.bank_transactions.insert_one(merged_tx)
                                        matched_transactions += 1
                                        logger.info(f"Matched Teller transaction {tx.get('id')} with CSV transaction {matching_csv.get('transaction_id')}")
                                    else:
                                        # Insert new Teller transaction
                                        self.db.client.db.bank_transactions.insert_one(tx)
                                        new_transactions += 1
                                    
                                    total_transactions += 1
                            
                            synced_accounts.append({
                                'account_name': account.get('name'),
                                'institution': account.get('institution', {}).get('name'),
                                'transactions_found': len(transactions)
                            })
                        
                except Exception as e:
                    logger.error(f"Error syncing transactions for user {user_id}: {e}")
                    continue
            
            return {
                "success": True,
                "total_transactions": total_transactions,
                "new_transactions": new_transactions,
                "matched_transactions": matched_transactions,
                "synced_accounts": synced_accounts
            }
            
        except Exception as e:
            logger.error(f"Bank sync error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_transactions(self, limit: int = 50, skip: int = 0) -> List[Dict]:
        """Get bank transactions from database"""
        if not self.db or not self.db.client.connected:
            return []
        
        return self.db.get_bank_transactions(limit, skip)
    
    def save_teller_token(self, token_data: Dict) -> Optional[str]:
        """Save Teller access token"""
        if not self.db or not self.db.connected:
            return None
        
        return self.db.save_teller_token(token_data)
    
    def get_connect_url(self, user_id: str) -> str:
        """Get Teller Connect URL"""
        return self.teller.get_connect_url(user_id) 
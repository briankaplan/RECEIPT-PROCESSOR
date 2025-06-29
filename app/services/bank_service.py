"""
Bank service for handling transactions and Teller integration
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..config import Config

logger = logging.getLogger(__name__)

class BankService:
    """Service for handling bank transactions and Teller integration"""
    
    def __init__(self, db_client, teller_client):
        self.db = db_client
        self.teller = teller_client
    
    def sync_transactions(self, start_date: str = None, end_date: str = None) -> Dict:
        """Sync bank transactions with proper error handling"""
        try:
            if not self.db or not self.db.connected:
                return {"success": False, "error": "Database not connected"}
            
            # Get active Teller tokens
            tokens = self.db.get_teller_tokens()
            if not tokens:
                return {"success": False, "error": "No active bank connections"}
            
            total_transactions = 0
            new_transactions = 0
            synced_accounts = []
            
            for token_record in tokens:
                access_token = token_record.get('access_token')
                user_id = token_record.get('user_id')
                
                if not access_token:
                    continue
                
                # Validate token
                if not self.teller.validate_token(access_token):
                    logger.warning(f"Invalid token for user {user_id}")
                    continue
                
                # Get accounts
                accounts = self.teller.get_accounts(access_token)
                account_transactions = 0
                account_new = 0
                
                for account in accounts:
                    # Get transactions for account
                    transactions = self.teller.get_transactions(
                        access_token, 
                        account['id'],
                        start_date,
                        end_date
                    )
                    
                    for transaction in transactions:
                        # Check if transaction already exists
                        existing = self.db.db.bank_transactions.find_one({
                            'transaction_id': transaction.get('id'),
                            'account_id': account['id']
                        })
                        
                        if not existing:
                            # Save new transaction
                            transaction_data = {
                                'transaction_id': transaction.get('id'),
                                'user_id': user_id,
                                'account_id': account['id'],
                                'date': transaction.get('date'),
                                'amount': transaction.get('amount'),
                                'description': transaction.get('description'),
                                'category': transaction.get('category'),
                                'institution_name': account.get('institution', {}).get('name'),
                                'account_name': account.get('name'),
                                'account_type': account.get('type'),
                                'currency': account.get('currency'),
                                'business_type': 'personal',
                                'synced_at': datetime.utcnow(),
                                'raw_data': transaction
                            }
                            
                            self.db.save_bank_transaction(transaction_data)
                            account_new += 1
                        
                        account_transactions += 1
                    
                    total_transactions += account_transactions
                    new_transactions += account_new
                    
                    synced_accounts.append({
                        'account_name': account.get('name'),
                        'institution': account.get('institution', {}).get('name'),
                        'transactions_found': account_transactions,
                        'new_transactions': account_new
                    })
            
            return {
                "success": True,
                "message": f"Successfully synced {new_transactions} new transactions",
                "synced": total_transactions,
                "new_transactions": new_transactions,
                "accounts": synced_accounts
            }
            
        except Exception as e:
            logger.error(f"Bank sync error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_transactions(self, limit: int = 50, skip: int = 0) -> List[Dict]:
        """Get bank transactions from database"""
        if not self.db or not self.db.connected:
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
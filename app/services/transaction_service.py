"""
Transaction service for managing transactions and syncing from bank data
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from bson import ObjectId

logger = logging.getLogger(__name__)

class TransactionService:
    """Service for managing transactions and syncing from bank data"""
    
    def __init__(self, db_client):
        self.db = db_client
    
    def sync_from_bank_transactions(self) -> Dict:
        """Sync transactions from bank_transactions to transactions with field mapping"""
        try:
            if not self.db or not hasattr(self.db, 'client') or not self.db.client:
                return {"success": False, "error": "Database not connected"}
            
            # Get all bank transactions
            bank_transactions = list(self.db.client.db.bank_transactions.find({}))
            
            synced = 0
            updated = 0
            
            for bank_tx in bank_transactions:
                # Create transaction record with field mapping
                transaction_data = self._map_bank_to_transaction(bank_tx)
                
                # Check if transaction already exists
                existing = self.db.client.db.transactions.find_one({
                    'transaction_id': transaction_data.get('transaction_id'),
                    'user_id': transaction_data.get('user_id')
                })
                
                if existing:
                    # Update existing transaction
                    self.db.client.db.transactions.update_one(
                        {'_id': existing['_id']},
                        {'$set': transaction_data}
                    )
                    updated += 1
                else:
                    # Insert new transaction
                    self.db.client.db.transactions.insert_one(transaction_data)
                    synced += 1
            
            return {
                "success": True,
                "synced": synced,
                "updated": updated,
                "total_processed": len(bank_transactions)
            }
            
        except Exception as e:
            logger.error(f"Error syncing transactions: {e}")
            return {"success": False, "error": str(e)}
    
    def _map_bank_to_transaction(self, bank_tx: Dict) -> Dict:
        """Map bank transaction to transaction format"""
        return {
            'transaction_id': bank_tx.get('id'),
            'user_id': bank_tx.get('user_id'),
            'account_id': bank_tx.get('account_id'),
            'transaction_date': bank_tx.get('date'),
            'amount': bank_tx.get('amount'),
            'merchant': bank_tx.get('description'),  # Bank description becomes merchant
            'description': bank_tx.get('description'),  # Keep original description
            'category': bank_tx.get('category', 'Uncategorized'),
            'institution_name': bank_tx.get('institution_name'),
            'account_name': bank_tx.get('account_name'),
            'currency': bank_tx.get('currency', 'USD'),
            'business_type': 'personal',
            'receipt_url': None,
            'notes': '',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'bank_transaction_id': bank_tx.get('id'),
            'raw_bank_data': bank_tx
        }
    
    def get_transactions(self, page: int = 1, page_size: int = 50, date_from: str = None, 
                        date_to: str = None, category: str = None, search: str = None) -> Dict:
        """Get transactions with pagination and filtering"""
        try:
            if not self.db or not hasattr(self.db, 'client') or not self.db.client:
                return {"success": False, "error": "Database not connected"}
            
            # Build query
            query = {}
            
            if date_from or date_to:
                date_query = {}
                if date_from:
                    try:
                        # Handle both date formats
                        if 'T' in date_from:
                            date_query['$gte'] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                        else:
                            date_query['$gte'] = datetime.strptime(date_from, '%Y-%m-%d')
                    except:
                        # If parsing fails, skip date filter
                        pass
                if date_to:
                    try:
                        if 'T' in date_to:
                            date_query['$lte'] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                        else:
                            date_query['$lte'] = datetime.strptime(date_to, '%Y-%m-%d')
                    except:
                        pass
                
                if date_query:
                    # Use transaction_date if available, otherwise fall back to date
                    query['$or'] = [
                        {'transaction_date': date_query},
                        {'date': date_query}
                    ]
            
            if category:
                query['category'] = category
            
            if search:
                search_query = {'$or': [
                    {'merchant': {'$regex': search, '$options': 'i'}},
                    {'description': {'$regex': search, '$options': 'i'}},
                    {'category': {'$regex': search, '$options': 'i'}}
                ]}
                
                # Combine with existing query
                if query:
                    query = {'$and': [query, search_query]}
                else:
                    query = search_query
            
            # Get total count
            total = self.db.client.db.transactions.count_documents(query)
            
            # Get paginated results
            skip = (page - 1) * page_size
            transactions = list(self.db.client.db.transactions.find(query)
                              .sort('transaction_date', -1)
                              .skip(skip)
                              .limit(page_size))
            
            # Convert ObjectId to string for JSON serialization
            for tx in transactions:
                if '_id' in tx:
                    tx['_id'] = str(tx['_id'])
                # Handle date fields
                for date_field in ['transaction_date', 'date', 'created_at', 'updated_at', 'bank_synced_at']:
                    if date_field in tx and tx[date_field]:
                        if isinstance(tx[date_field], datetime):
                            tx[date_field] = tx[date_field].isoformat()
                # Handle raw_bank_data datetime fields and ObjectId
                if 'raw_bank_data' in tx and tx['raw_bank_data']:
                    raw_data = tx['raw_bank_data']
                    if isinstance(raw_data, dict):
                        for key, value in raw_data.items():
                            if isinstance(value, datetime):
                                raw_data[key] = value.isoformat()
                            if key == '_id' and hasattr(value, '__str__'):
                                raw_data[key] = str(value)
            
            # Ensure the return value is serializable
            return {
                'transactions': transactions,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'pages': (total + page_size - 1) // page_size
                }
            }
            
        except Exception as e:
            logger.error(f"Get transactions error: {e}")
            return {"success": False, "error": str(e)}
    
    def update_transaction(self, transaction_id: str, updates: Dict) -> Dict:
        """Update a transaction"""
        try:
            if not self.db or not self.db.client.connected:
                return {"success": False, "error": "Database not connected"}
            
            # Remove fields that shouldn't be updated
            updates.pop('_id', None)
            updates.pop('bank_transaction_id', None)
            updates.pop('user_id', None)
            updates.pop('account_id', None)
            updates.pop('bank_synced_at', None)
            
            # Add updated timestamp
            updates['updated_at'] = datetime.utcnow()
            
            result = self.db.client.db.transactions.update_one(
                {'_id': ObjectId(transaction_id)},
                {'$set': updates}
            )
            
            if result.modified_count > 0:
                return {"success": True, "message": "Transaction updated successfully"}
            else:
                return {"success": False, "error": "Transaction not found or no changes made"}
                
        except Exception as e:
            logger.error(f"Error updating transaction: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_transaction(self, transaction_id: str) -> Dict:
        """Delete a transaction"""
        try:
            if not self.db or not self.db.client.connected:
                return {"success": False, "error": "Database not connected"}
            
            result = self.db.client.db.transactions.delete_one({'_id': ObjectId(transaction_id)})
            
            if result.deleted_count > 0:
                return {"success": True, "message": "Transaction deleted successfully"}
            else:
                return {"success": False, "error": "Transaction not found"}
                
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            return {"success": False, "error": str(e)}
    
    def get_categories(self) -> List[str]:
        """Get unique categories from transactions"""
        try:
            if not self.db or not self.db.client.connected:
                return []
            
            categories = self.db.client.db.transactions.distinct('category')
            return sorted(categories)
            
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return [] 
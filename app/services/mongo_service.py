"""
MongoDB service for the Receipt Processor application
"""

import logging
from typing import Dict, Optional
from pymongo import MongoClient
from ..config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class MongoService:
    """MongoDB service wrapper for the application"""
    
    def __init__(self):
        self.client = SafeMongoClient()
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        return self.client.get_stats()
    
    def save_receipt(self, receipt_data: Dict) -> Optional[str]:
        """Save receipt data to MongoDB"""
        return self.client.save_receipt(receipt_data)
    
    def get_receipts(self, limit: int = 50, skip: int = 0) -> list:
        """Get receipts from MongoDB"""
        return self.client.get_receipts(limit, skip)
    
    def save_bank_transaction(self, transaction_data: Dict) -> Optional[str]:
        """Save bank transaction to MongoDB"""
        return self.client.save_bank_transaction(transaction_data)
    
    def get_bank_transactions(self, limit: int = 50, skip: int = 0) -> list:
        """Get bank transactions from MongoDB"""
        return self.client.get_bank_transactions(limit, skip)
    
    def save_teller_token(self, token_data: Dict) -> Optional[str]:
        """Save Teller access token to MongoDB"""
        return self.client.save_teller_token(token_data)
    
    def get_teller_tokens(self) -> list:
        """Get Teller access tokens from MongoDB"""
        return self.client.get_teller_tokens()
    
    def clear_all_teller_tokens(self) -> bool:
        """Clear all Teller tokens from MongoDB"""
        return self.client.clear_all_teller_tokens()
    
    def deactivate_teller_tokens(self) -> bool:
        """Deactivate all Teller tokens (mark as inactive instead of deleting)"""
        return self.client.deactivate_teller_tokens()
    
    def keep_only_latest_teller_token(self) -> bool:
        """Keep only the most recent Teller token and deactivate others"""
        return self.client.keep_only_latest_teller_token()
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()

class SafeMongoClient:
    """MongoDB client with error handling and connection management"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Connect to MongoDB with proper error handling"""
        try:
            if not Config.MONGODB_URI:
                logger.warning("No MongoDB URI configured")
                return
            
            self.client = MongoClient(
                Config.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                maxPoolSize=10,
                retryWrites=True
            )
            
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[Config.MONGODB_DATABASE]
            self.connected = True
            logger.info("✅ MongoDB connected")
            
        except Exception as e:
            logger.warning(f"MongoDB connection failed: {e}")
            self.connected = False
    
    def get_stats(self) -> Dict:
        """Get database statistics safely"""
        try:
            if not self.connected:
                return {"connected": False, "collections": {}}
            
            return {
                "connected": True,
                "database": Config.MONGODB_DATABASE,
                "collections": {
                    "bank_transactions": self.db.bank_transactions.count_documents({}),
                    "receipts": self.db.receipts.count_documents({}),
                    "teller_tokens": self.db.teller_tokens.count_documents({}),
                    "teller_webhooks": self.db.teller_webhooks.count_documents({})
                }
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"connected": False, "error": str(e)}
    
    def save_receipt(self, receipt_data: Dict) -> Optional[str]:
        """Save receipt data to MongoDB"""
        try:
            if not self.connected:
                logger.error("MongoDB not connected")
                return None
            
            result = self.db.receipts.insert_one(receipt_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error saving receipt: {e}")
            return None
    
    def get_receipts(self, limit: int = 50, skip: int = 0) -> list:
        """Get receipts from MongoDB"""
        try:
            if not self.connected:
                return []
            
            cursor = self.db.receipts.find().sort('processed_at', -1).skip(skip).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Error getting receipts: {e}")
            return []
    
    def save_bank_transaction(self, transaction_data: Dict) -> Optional[str]:
        """Save bank transaction to MongoDB"""
        try:
            if not self.connected:
                logger.error("MongoDB not connected")
                return None
            
            result = self.db.bank_transactions.insert_one(transaction_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error saving transaction: {e}")
            return None
    
    def get_bank_transactions(self, limit: int = 50, skip: int = 0) -> list:
        """Get bank transactions from MongoDB"""
        try:
            if not self.connected:
                return []
            
            cursor = self.db.bank_transactions.find().sort('date', -1).skip(skip).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
    
    def save_teller_token(self, token_data: Dict) -> Optional[str]:
        """Save Teller access token to MongoDB"""
        try:
            if not self.connected:
                logger.error("MongoDB not connected")
                return None
            
            result = self.db.teller_tokens.insert_one(token_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error saving Teller token: {e}")
            return None
    
    def get_teller_tokens(self) -> list:
        """Get Teller access tokens from MongoDB"""
        try:
            if not self.connected:
                return []
            
            cursor = self.db.teller_tokens.find({'status': 'active'})
            return list(cursor)
        except Exception as e:
            logger.error(f"Error getting Teller tokens: {e}")
            return []
    
    def clear_all_teller_tokens(self) -> bool:
        """Clear all Teller tokens from MongoDB"""
        try:
            if not self.connected:
                logger.error("MongoDB not connected")
                return False
            
            result = self.db.teller_tokens.delete_many({})
            logger.info(f"🗑️ Cleared {result.deleted_count} Teller tokens")
            return True
        except Exception as e:
            logger.error(f"Error clearing Teller tokens: {e}")
            return False
    
    def deactivate_teller_tokens(self) -> bool:
        """Deactivate all Teller tokens (mark as inactive instead of deleting)"""
        try:
            if not self.connected:
                logger.error("MongoDB not connected")
                return False
            
            result = self.db.teller_tokens.update_many(
                {'status': 'active'},
                {'$set': {'status': 'inactive', 'deactivated_at': datetime.utcnow()}}
            )
            logger.info(f"🔒 Deactivated {result.modified_count} Teller tokens")
            return True
        except Exception as e:
            logger.error(f"Error deactivating Teller tokens: {e}")
            return False
    
    def keep_only_latest_teller_token(self) -> bool:
        """Keep only the most recent Teller token and deactivate others"""
        try:
            if not self.connected:
                logger.error("MongoDB not connected")
                return False
            
            # Get all active tokens sorted by creation date
            tokens = list(self.db.teller_tokens.find({'status': 'active'}).sort('created_at', -1))
            
            if len(tokens) <= 1:
                logger.info("✅ Only one or no active Teller tokens found")
                return True
            
            # Keep the most recent token, deactivate the rest
            latest_token = tokens[0]
            older_tokens = tokens[1:]
            
            # Deactivate older tokens
            for token in older_tokens:
                self.db.teller_tokens.update_one(
                    {'_id': token['_id']},
                    {'$set': {'status': 'inactive', 'deactivated_at': datetime.utcnow()}}
                )
            
            logger.info(f"✅ Kept latest Teller token, deactivated {len(older_tokens)} older tokens")
            return True
            
        except Exception as e:
            logger.error(f"Error keeping only latest Teller token: {e}")
            return False
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.connected = False 
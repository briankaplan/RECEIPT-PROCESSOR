import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

logger = logging.getLogger(__name__)

class MongoDBClient:
    """MongoDB client for storing receipts and bank statement data"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.receipts_collection = None
        self.bank_statements_collection = None
        self.processed_emails_collection = None
        
        self._connect()
    
    def _connect(self):
        """Connect to MongoDB"""
        try:
            # Get MongoDB connection string from environment
            mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
            
            if not mongo_uri:
                logger.warning("No MongoDB URI found in environment variables")
                return False
            
            # Connect to MongoDB
            self.client = MongoClient(mongo_uri)
            
            # Get database name from URI or use default
            db_name = os.getenv('MONGODB_DATABASE', 'gmail_receipt_processor')
            self.db = self.client[db_name]
            
            # Initialize collections
            self.receipts_collection = self.db['receipts']
            self.bank_statements_collection = self.db['bank_statements']
            self.processed_emails_collection = self.db['processed_emails']
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB database: {db_name}")
            
            # Create indexes for better performance
            self._create_indexes()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            self.client = None
            return False
    
    def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # Receipts collection indexes
            self.receipts_collection.create_index([('email_id', 1), ('account', 1)], unique=True)
            self.receipts_collection.create_index([('processed_at', -1)])
            self.receipts_collection.create_index([('merchant', 1)])
            self.receipts_collection.create_index([('total_amount', 1)])
            self.receipts_collection.create_index([('date', 1)])
            
            # Bank statements collection indexes
            self.bank_statements_collection.create_index([('date', 1)])
            self.bank_statements_collection.create_index([('amount', 1)])
            self.bank_statements_collection.create_index([('description', 1)])
            
            # Processed emails collection indexes
            self.processed_emails_collection.create_index([('email_id', 1), ('account', 1)], unique=True)
            self.processed_emails_collection.create_index([('processed_at', -1)])
            
            logger.info("Created MongoDB indexes")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
    
    def is_connected(self) -> bool:
        """Check if MongoDB is connected"""
        if not self.client:
            return False
        
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    def save_receipt(self, receipt_data: Dict, email_id: str, account: str) -> bool:
        """Save receipt data to MongoDB with comprehensive export schema"""
        if not self.is_connected():
            logger.error("MongoDB not connected")
            return False
        
        try:
            # Generate unique document ID
            doc_id = f"{email_id}_{account}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            document = {
                '_id': doc_id,
                'email_id': email_id,
                'account': account,
                'processed_at': datetime.utcnow(),
                
                # Core export fields
                'transaction_date': receipt_data.get('date'),
                'merchant': receipt_data.get('merchant', ''),
                'price': receipt_data.get('total_amount', receipt_data.get('amount', 0.0)),
                'description': self._generate_description(receipt_data),
                'receipt_url': receipt_data.get('r2_url', ''),
                'gmail_id': email_id,
                'gmail_link': f"https://mail.google.com/mail/u/0/#inbox/{email_id}",
                'match_status': 'Not Matched',
                'receipt_status': 'Found Receipt',
                'category': receipt_data.get('ai_category', 'Uncategorized'),
                'account_name': self._determine_account_name(account),
                'is_subscription': self._detect_subscription(receipt_data),
                'business_type': self._determine_business_type(account, receipt_data),
                
                # Additional processing fields
                'source_type': receipt_data.get('source_type', 'gmail'),
                'items': receipt_data.get('items', []),
                'raw_text': receipt_data.get('raw_text', ''),
                'file_path': receipt_data.get('source_file', ''),
                'ai_subcategory': receipt_data.get('ai_subcategory', ''),
                'business_purpose': receipt_data.get('business_purpose', ''),
                'tax_deductible': receipt_data.get('tax_deductible', False),
                'confidence_score': receipt_data.get('confidence_score', 0.0),
                'merchant_type': receipt_data.get('merchant_type', ''),
                'processing_status': 'completed',
                'bank_transaction_id': None,
                'matched_transaction_data': None,
                'payment_method': receipt_data.get('payment_method', ''),
                'receipt_data': receipt_data  # Keep original data for reference
            }
            
            result = self.receipts_collection.replace_one(
                {'email_id': email_id, 'account': account},
                document,
                upsert=True
            )
            
            logger.info(f"Saved receipt for email {email_id} from {account}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving receipt: {str(e)}")
            return False
    
    def _generate_description(self, receipt_data: Dict) -> str:
        """Generate auto description from receipt data"""
        merchant = receipt_data.get('merchant', '')
        items = receipt_data.get('items', [])
        raw_text = receipt_data.get('raw_text', '')
        
        if items and len(items) > 0:
            # Use items for description
            item_names = [item.get('name', '') for item in items[:3] if item.get('name')]
            if item_names:
                description = f"{merchant} - {', '.join(item_names)}"
                if len(items) > 3:
                    description += f" and {len(items) - 3} more items"
                return description[:200]
        
        # Fall back to raw text
        if raw_text:
            # Extract first meaningful line
            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            for line in lines:
                if len(line) > 10 and not line.replace('.', '').replace('$', '').replace(',', '').isdigit():
                    return f"{merchant} - {line}"[:200]
        
        return f"{merchant} - Transaction"[:200]
    
    def _determine_account_name(self, account: str) -> str:
        """Determine account name for export"""
        if '@' in account:
            return account.split('@')[0].replace('.', '_')
        return account
    
    def _detect_subscription(self, receipt_data: Dict) -> bool:
        """Detect if receipt is for a subscription service"""
        subscription_keywords = [
            'subscription', 'monthly', 'annual', 'recurring', 'netflix', 'spotify', 
            'adobe', 'microsoft', 'google', 'apple', 'amazon prime', 'office 365',
            'dropbox', 'zoom', 'slack', 'github', 'digital ocean', 'saas', 'software'
        ]
        
        text = (receipt_data.get('raw_text', '') + ' ' + 
               receipt_data.get('merchant', '') + ' ' +
               receipt_data.get('business_purpose', '')).lower()
        
        return any(keyword in text for keyword in subscription_keywords)
    
    def _determine_business_type(self, account: str, receipt_data: Dict) -> str:
        """Determine business type: Personal, Music City Rodeo, Down Home"""
        account_lower = account.lower()
        
        # Account-based determination
        if 'downhome' in account_lower:
            return 'Down Home'
        elif 'musiccity' in account_lower or 'rodeo' in account_lower:
            return 'Music City Rodeo'
        elif 'kaplan.brian' in account_lower:
            # Analyze receipt content for business indicators
            text = (receipt_data.get('raw_text', '') + ' ' + 
                   receipt_data.get('merchant', '') + ' ' +
                   receipt_data.get('business_purpose', '')).lower()
            
            # Music City Rodeo keywords
            music_keywords = ['music', 'rodeo', 'event', 'venue', 'concert', 'entertainment', 'sound', 'stage']
            if any(keyword in text for keyword in music_keywords):
                return 'Music City Rodeo'
            
            # Down Home keywords  
            food_keywords = ['restaurant', 'food', 'kitchen', 'dining', 'catering', 'grocery', 'supplies']
            if any(keyword in text for keyword in food_keywords):
                return 'Down Home'
            
            return 'Personal'
        
        return 'Personal'
    
    def save_bank_statements(self, statements: List[Dict]) -> bool:
        """Save bank statements to MongoDB"""
        if not self.is_connected():
            logger.error("MongoDB not connected")
            return False
        
        try:
            # Clear existing bank statements
            self.bank_statements_collection.delete_many({})
            
            # Add timestamps to statements
            for statement in statements:
                statement['uploaded_at'] = datetime.utcnow()
            
            # Insert new statements
            if statements:
                self.bank_statements_collection.insert_many(statements)
            
            logger.info(f"Saved {len(statements)} bank statements to MongoDB")
            return True
            
        except Exception as e:
            logger.error(f"Error saving bank statements: {str(e)}")
            return False
    
    def get_bank_statements(self) -> List[Dict]:
        """Get all bank statements from MongoDB"""
        if not self.is_connected():
            logger.error("MongoDB not connected")
            return []
        
        try:
            statements = list(self.bank_statements_collection.find({}, {'_id': 0}))
            return statements
            
        except Exception as e:
            logger.error(f"Error getting bank statements: {str(e)}")
            return []
    
    def mark_email_processed(self, email_id: str, account: str, status: str = 'processed') -> bool:
        """Mark email as processed or failed"""
        if not self.is_connected():
            logger.error("MongoDB not connected")
            return False
        
        try:
            document = {
                'email_id': email_id,
                'account': account,
                'status': status,
                'processed_at': datetime.utcnow()
            }
            
            self.processed_emails_collection.replace_one(
                {'email_id': email_id, 'account': account},
                document,
                upsert=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking email processed: {str(e)}")
            return False
    
    def get_processed_emails(self) -> Dict:
        """Get processed email statistics"""
        if not self.is_connected():
            logger.error("MongoDB not connected")
            return {'processed': [], 'failed': []}
        
        try:
            processed = list(self.processed_emails_collection.find(
                {'status': 'processed'}, 
                {'email_id': 1, 'account': 1, '_id': 0}
            ))
            
            failed = list(self.processed_emails_collection.find(
                {'status': 'failed'}, 
                {'email_id': 1, 'account': 1, '_id': 0}
            ))
            
            return {
                'processed': [f"{p['account']}:{p['email_id']}" for p in processed],
                'failed': [f"{f['account']}:{f['email_id']}" for f in failed]
            }
            
        except Exception as e:
            logger.error(f"Error getting processed emails: {str(e)}")
            return {'processed': [], 'failed': []}
    
    def get_receipts(self, limit: int = 100) -> List[Dict]:
        """Get recent receipts from MongoDB"""
        if not self.is_connected():
            logger.error("MongoDB not connected")
            return []
        
        try:
            receipts = list(self.receipts_collection.find(
                {}, 
                {'_id': 0}
            ).sort('processed_at', -1).limit(limit))
            
            return receipts
            
        except Exception as e:
            logger.error(f"Error getting receipts: {str(e)}")
            return []
    
    def search_receipts(self, query: Dict) -> List[Dict]:
        """Search receipts by criteria"""
        if not self.is_connected():
            logger.error("MongoDB not connected")
            return []
        
        try:
            receipts = list(self.receipts_collection.find(query, {'_id': 0}))
            return receipts
            
        except Exception as e:
            logger.error(f"Error searching receipts: {str(e)}")
            return []
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        if not self.is_connected():
            return {
                'connected': False,
                'receipts_count': 0,
                'bank_statements_count': 0,
                'processed_emails_count': 0,
                'failed_emails_count': 0
            }
        
        try:
            receipts_count = self.receipts_collection.count_documents({})
            bank_statements_count = self.bank_statements_collection.count_documents({})
            processed_count = self.processed_emails_collection.count_documents({'status': 'processed'})
            failed_count = self.processed_emails_collection.count_documents({'status': 'failed'})
            
            return {
                'connected': True,
                'receipts_count': receipts_count,
                'bank_statements_count': bank_statements_count,
                'processed_emails_count': processed_count,
                'failed_emails_count': failed_count
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {
                'connected': False,
                'receipts_count': 0,
                'bank_statements_count': 0,
                'processed_emails_count': 0,
                'failed_emails_count': 0
            }
#!/usr/bin/env python3
"""
Enhanced MongoDB Writer Module
Advanced MongoDB operations for expense data with comprehensive features
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import motor.motor_asyncio
from bson import ObjectId
import asyncio
from pymongo.errors import DuplicateKeyError, BulkWriteError, ConnectionFailure
import json

class EnhancedMongoWriter:
    def __init__(self, config: Dict):
        """Initialize enhanced MongoDB writer with advanced features"""
        self.config = config
        self.client = None
        self.db = None
        self.collections = {}
        
        # Performance tracking
        self.stats = {
            'documents_written': 0,
            'documents_updated': 0,
            'documents_failed': 0,
            'connection_attempts': 0,
            'last_operation_time': None
        }
        
        # Connection settings
        self.mongo_config = self.config.get('mongodb', {})
        self.retry_attempts = 3
        self.retry_delay = 1.0
        
    async def initialize(self) -> bool:
        """Initialize MongoDB connection with comprehensive setup"""
        try:
            self.stats['connection_attempts'] += 1
            
            # Validate configuration
            if not self.mongo_config:
                logging.error("❌ No MongoDB configuration found")
                return False
            
            uri = self.mongo_config.get('uri')
            if not uri or uri.strip() == "":
                logging.info("ℹ️ MongoDB URI is empty - MongoDB disabled")
                return False
            
            # Connect with proper options
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                maxPoolSize=10,
                retryWrites=True
            )
            
            # Get database
            database_name = self.mongo_config.get('database', 'expenses')
            self.db = self.client[database_name]
            
            # Initialize collections
            await self._setup_collections()
            
            # Test connection
            await self.db.command('ping')
            
            # Create indexes for performance
            await self._create_indexes()
            
            logging.info(f"✅ MongoDB connected to database: {database_name}")
            return True
            
        except ConnectionFailure as e:
            logging.error(f"❌ MongoDB connection failed: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ MongoDB initialization error: {e}")
            return False
    
    async def _setup_collections(self):
        """Setup collections with proper schema"""
        collection_configs = {
            'expenses': 'expenses',
            'receipts': 'receipts', 
            'transactions': 'transactions',
            'matches': 'matches',
            'analytics': 'analytics'
        }
        
        for name, collection_name in collection_configs.items():
            actual_name = self.mongo_config.get(f'{name}_collection', collection_name)
            self.collections[name] = self.db[actual_name]
    
    async def _create_indexes(self):
        """Create indexes for better performance"""
        try:
            # Expenses collection indexes
            if 'expenses' in self.collections:
                await self.collections['expenses'].create_index("expense_id", unique=True)
                await self.collections['expenses'].create_index("date")
                await self.collections['expenses'].create_index("merchant")
                await self.collections['expenses'].create_index("amount")
                await self.collections['expenses'].create_index("gmail_account")
                await self.collections['expenses'].create_index([("date", -1), ("amount", -1)])
            
            # Receipts collection indexes
            if 'receipts' in self.collections:
                await self.collections['receipts'].create_index("receipt_id", unique=True)
                await self.collections['receipts'].create_index("gmail_account")
                await self.collections['receipts'].create_index("processed_at")
            
            # Matches collection indexes
            if 'matches' in self.collections:
                await self.collections['matches'].create_index("match_id", unique=True)
                await self.collections['matches'].create_index("confidence")
                await self.collections['matches'].create_index("created_at")
            
            logging.info("📚 MongoDB indexes created successfully")
            
        except Exception as e:
            logging.warning(f"⚠️ Index creation warning: {e}")
    
    async def test_connection(self) -> bool:
        """Test MongoDB connection with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                if not self.client:
                    if not await self.initialize():
                        continue
                
                await self.db.command('ping')
                logging.info("✅ MongoDB connection test successful")
                return True
                
            except Exception as e:
                logging.warning(f"⚠️ Connection test attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        logging.error("❌ MongoDB connection test failed after all attempts")
        return False
    
    async def write_expense(self, expense_data: Dict) -> bool:
        """Write single expense with comprehensive validation"""
        try:
            if not await self._ensure_connection():
                return False
            
            # Validate and enhance expense data
            enhanced_data = await self._enhance_expense_data(expense_data)
            
            # Use upsert to handle duplicates
            result = await self.collections['expenses'].replace_one(
                {"expense_id": enhanced_data.get("expense_id")},
                enhanced_data,
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                self.stats['documents_written'] += 1
                self.stats['last_operation_time'] = datetime.now()
                logging.info(f"💾 Saved expense: {enhanced_data.get('merchant', 'Unknown')} ${enhanced_data.get('amount', 0):.2f}")
                return True
            else:
                self.stats['documents_failed'] += 1
                return False
                
        except Exception as e:
            logging.error(f"❌ Failed to write expense: {e}")
            self.stats['documents_failed'] += 1
            return False
    
    async def write_expenses_batch(self, expenses: List[Dict]) -> Dict[str, int]:
        """Write multiple expenses with batch processing"""
        if not expenses:
            return {"written": 0, "updated": 0, "failed": 0}
        
        try:
            if not await self._ensure_connection():
                return {"written": 0, "updated": 0, "failed": 0}
            
            # Enhance all expense data
            enhanced_expenses = []
            for expense in expenses:
                try:
                    enhanced = await self._enhance_expense_data(expense)
                    enhanced_expenses.append(enhanced)
                except Exception as e:
                    logging.warning(f"⚠️ Failed to enhance expense data: {e}")
                    continue
            
            if not enhanced_expenses:
                return {"written": 0, "updated": 0, "failed": 0}
            
            # Prepare bulk operations
            operations = []
            for expense in enhanced_expenses:
                operations.append({
                    "replaceOne": {
                        "filter": {"expense_id": expense.get("expense_id")},
                        "replacement": expense,
                        "upsert": True
                    }
                })
            
            # Execute bulk write
            result = await self.collections['expenses'].bulk_write(operations, ordered=False)
            
            written = result.upserted_count
            updated = result.modified_count
            failed = len(expenses) - written - updated
            
            self.stats['documents_written'] += written
            self.stats['documents_updated'] += updated
            self.stats['documents_failed'] += failed
            self.stats['last_operation_time'] = datetime.now()
            
            logging.info(f"📦 Batch operation: {written} written, {updated} updated, {failed} failed")
            
            return {"written": written, "updated": updated, "failed": failed}
            
        except BulkWriteError as e:
            logging.error(f"❌ Bulk write error: {e}")
            return {"written": 0, "updated": 0, "failed": len(expenses)}
        except Exception as e:
            logging.error(f"❌ Batch write failed: {e}")
            return {"written": 0, "updated": 0, "failed": len(expenses)}
    
    async def write_match(self, match_data: Dict) -> bool:
        """Write transaction match data"""
        try:
            if not await self._ensure_connection():
                return False
            
            # Enhance match data
            enhanced_match = {
                "match_id": match_data.get("match_id", f"match_{ObjectId()}"),
                "receipt_id": match_data.get("receipt_id"),
                "transaction_id": match_data.get("transaction_id"),
                "confidence": match_data.get("confidence", 0.0),
                "match_type": match_data.get("match_type", "unknown"),
                "reasoning": match_data.get("reasoning", ""),
                "receipt_data": match_data.get("receipt"),
                "transaction_data": match_data.get("transaction"),
                "ai_enhanced": match_data.get("ai_enhanced", False),
                "semantic_score": match_data.get("semantic_score"),
                "created_at": datetime.now().isoformat(),
                "processor_version": "enhanced_v2"
            }
            
            result = await self.collections['matches'].replace_one(
                {"match_id": enhanced_match["match_id"]},
                enhanced_match,
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                logging.info(f"🔗 Saved match: {enhanced_match['confidence']:.3f} confidence")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"❌ Failed to write match: {e}")
            return False
    
    async def write_matches_batch(self, matches: List[Dict]) -> int:
        """Write multiple matches efficiently"""
        if not matches:
            return 0
        
        try:
            if not await self._ensure_connection():
                return 0
            
            # Prepare match documents
            match_docs = []
            for match in matches:
                enhanced_match = {
                    "match_id": match.get("match_id", f"match_{ObjectId()}"),
                    "receipt_id": match.get("receipt_id"),
                    "transaction_id": match.get("transaction_id"),
                    "confidence": match.get("confidence", 0.0),
                    "match_type": match.get("match_type", "unknown"),
                    "reasoning": match.get("reasoning", ""),
                    "receipt_data": match.get("receipt"),
                    "transaction_data": match.get("transaction"),
                    "ai_enhanced": match.get("ai_enhanced", False),
                    "created_at": datetime.now().isoformat()
                }
                match_docs.append(enhanced_match)
            
            # Use insert_many with ordered=False for better performance
            result = await self.collections['matches'].insert_many(match_docs, ordered=False)
            
            logging.info(f"🔗 Saved {len(result.inserted_ids)} matches")
            return len(result.inserted_ids)
            
        except Exception as e:
            logging.error(f"❌ Failed to write matches batch: {e}")
            return 0
    
    async def get_expense_analytics(self, days: int = 30) -> Dict:
        """Get expense analytics from stored data"""
        try:
            if not await self._ensure_connection():
                return {}
            
            # Date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Aggregation pipeline
            pipeline = [
                {
                    "$match": {
                        "date": {
                            "$gte": start_date.strftime('%Y-%m-%d'),
                            "$lte": end_date.strftime('%Y-%m-%d')
                        }
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_amount": {"$sum": "$amount"},
                        "total_count": {"$sum": 1},
                        "avg_amount": {"$avg": "$amount"},
                        "max_amount": {"$max": "$amount"},
                        "min_amount": {"$min": "$amount"}
                    }
                }
            ]
            
            result = await self.collections['expenses'].aggregate(pipeline).to_list(1)
            
            if result:
                analytics = result[0]
                analytics.pop('_id', None)
                return analytics
            
            return {"total_amount": 0, "total_count": 0, "avg_amount": 0}
            
        except Exception as e:
            logging.error(f"❌ Analytics query failed: {e}")
            return {}
    
    async def get_top_merchants(self, limit: int = 10) -> List[Dict]:
        """Get top merchants by spending"""
        try:
            if not await self._ensure_connection():
                return []
            
            pipeline = [
                {
                    "$group": {
                        "_id": "$merchant",
                        "total_amount": {"$sum": "$amount"},
                        "transaction_count": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"total_amount": -1}
                },
                {
                    "$limit": limit
                }
            ]
            
            results = await self.collections['expenses'].aggregate(pipeline).to_list(limit)
            return results
            
        except Exception as e:
            logging.error(f"❌ Top merchants query failed: {e}")
            return []
    
    async def _enhance_expense_data(self, expense_data: Dict) -> Dict:
        """Enhance expense data with metadata"""
        enhanced = expense_data.copy()
        
        # Add timestamps
        if 'created_at' not in enhanced:
            enhanced['created_at'] = datetime.now().isoformat()
        
        enhanced['updated_at'] = datetime.now().isoformat()
        
        # Ensure required fields
        if 'expense_id' not in enhanced:
            enhanced['expense_id'] = f"exp_{ObjectId()}"
        
        # Type validation and conversion
        if 'amount' in enhanced:
            try:
                enhanced['amount'] = float(enhanced['amount'])
            except (ValueError, TypeError):
                enhanced['amount'] = 0.0
        
        if 'confidence' in enhanced:
            try:
                enhanced['confidence'] = float(enhanced['confidence'])
            except (ValueError, TypeError):
                enhanced['confidence'] = 0.0
        
        # Add processing metadata
        enhanced['processor_version'] = 'enhanced_v2'
        enhanced['data_version'] = '2.0'
        
        return enhanced
    
    async def _ensure_connection(self) -> bool:
        """Ensure MongoDB connection is active"""
        if not self.client:
            return await self.initialize()
        
        try:
            await self.db.command('ping')
            return True
        except Exception:
            logging.warning("⚠️ MongoDB connection lost, reconnecting...")
            return await self.initialize()
    
    def get_stats(self) -> Dict:
        """Get writer statistics"""
        return {
            **self.stats,
            'connection_status': 'connected' if self.client else 'disconnected',
            'database_name': self.mongo_config.get('database', 'expenses'),
            'collections_count': len(self.collections)
        }
    
    async def health_check(self) -> Dict:
        """Comprehensive health check"""
        health = {
            'status': 'unknown',
            'connection': False,
            'collections': {},
            'stats': self.get_stats(),
            'last_check': datetime.now().isoformat()
        }
        
        try:
            # Test connection
            if await self.test_connection():
                health['connection'] = True
                health['status'] = 'healthy'
                
                # Check collections
                for name, collection in self.collections.items():
                    try:
                        count = await collection.count_documents({})
                        health['collections'][name] = {
                            'document_count': count,
                            'status': 'accessible'
                        }
                    except Exception as e:
                        health['collections'][name] = {
                            'status': 'error',
                            'error': str(e)
                        }
            else:
                health['status'] = 'unhealthy'
                
        except Exception as e:
            health['status'] = 'error'
            health['error'] = str(e)
        
        return health
    
    async def close(self):
        """Close MongoDB connection gracefully"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self.collections = {}
            logging.info("📪 MongoDB connection closed")

# Integration helper for the expense processor
async def save_enhanced_results_to_mongo(matches: List[Dict], config: Dict) -> bool:
    """Helper function to save enhanced expense processor results"""
    
    if not config.get('mongodb', {}).get('uri'):
        logging.info("ℹ️ MongoDB not configured, skipping save")
        return True
    
    writer = EnhancedMongoWriter(config)
    
    try:
        if not await writer.initialize():
            return False
        
        # Save expenses
        expenses = []
        for match in matches:
            try:
                receipt = match.get('receipt', {})
                transaction = match.get('transaction', {})
                
                expense = {
                    'expense_id': f"exp_{receipt.get('id', ObjectId())}_{transaction.get('id', ObjectId())}",
                    'receipt_id': receipt.get('id'),
                    'transaction_id': transaction.get('id'),
                    'merchant': transaction.get('Description', ''),
                    'amount': abs(float(transaction.get('Amount', 0))),
                    'date': transaction.get('Transaction Date', ''),
                    'category': receipt.get('ai_category', transaction.get('Category', '')),
                    'subcategory': receipt.get('ai_subcategory', ''),
                    'payment_method': receipt.get('ai_payment_method', ''),
                    'confidence_score': match.get('confidence', 0),
                    'match_type': match.get('match_type', ''),
                    'gmail_account': receipt.get('gmail_account', ''),
                    'ai_enhanced': receipt.get('ai_enhanced', False),
                    'ai_confidence': receipt.get('ai_confidence', 0),
                    'items': receipt.get('ai_items', []),
                    'tax_amount': receipt.get('ai_tax_amount', 0),
                    'tip_amount': receipt.get('ai_tip_amount', 0),
                    'notes': match.get('match_details', ''),
                    'status': 'processed'
                }
                expenses.append(expense)
                
            except Exception as e:
                logging.error(f"Error preparing expense for MongoDB: {e}")
                continue
        
        # Batch write expenses
        if expenses:
            result = await writer.write_expenses_batch(expenses)
            logging.info(f"💾 MongoDB save result: {result}")
        
        # Save matches separately
        if matches:
            await writer.write_matches_batch(matches)
        
        return True
        
    except Exception as e:
        logging.error(f"❌ MongoDB save failed: {e}")
        return False
    finally:
        await writer.close()

# Test the enhanced MongoDB writer
if __name__ == "__main__":
    import asyncio
    
    async def test_mongo_writer():
        config = {
            "mongodb": {
                "uri": "mongodb://localhost:27017",
                "database": "test_expenses",
                "expenses_collection": "expenses",
                "matches_collection": "matches"
            }
        }
        
        writer = EnhancedMongoWriter(config)
        
        # Test initialization
        if await writer.initialize():
            print("✅ MongoDB writer initialized")
            
            # Test health check
            health = await writer.health_check()
            print(f"🏥 Health check: {health}")
            
            # Test writing an expense
            test_expense = {
                "expense_id": "test_exp_001",
                "merchant": "Test Merchant",
                "amount": 25.99,
                "date": "2025-06-12",
                "category": "Test",
                "confidence_score": 0.95
            }
            
            success = await writer.write_expense(test_expense)
            print(f"💾 Write test: {'✅ Success' if success else '❌ Failed'}")
            
            # Test analytics
            analytics = await writer.get_expense_analytics(30)
            print(f"📊 Analytics: {analytics}")
            
            # Test stats
            stats = writer.get_stats()
            print(f"📈 Stats: {stats}")
            
        else:
            print("❌ MongoDB writer initialization failed")
        
        await writer.close()
    
    # Run test
    print("🧪 Testing Enhanced MongoDB Writer")
    asyncio.run(test_mongo_writer())
#!/usr/bin/env python3
"""
Expense Database - MongoDB integration for expense data storage and retrieval
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from dataclasses import dataclass, asdict
import json

@dataclass
class ExpenseRecord:
    expense_id: str
    receipt_id: str
    transaction_id: Optional[str]
    merchant: str
    amount: float
    date: str
    category: str
    subcategory: Optional[str]
    payment_method: str
    tax_amount: float
    tip_amount: float
    items: List[str]
    location: str
    confidence_score: float
    gmail_account: str
    receipt_url: Optional[str]
    created_at: str
    updated_at: str
    tags: List[str]
    notes: str
    status: str  # 'processed', 'review_needed', 'approved', 'disputed'

class ExpenseDatabase:
    """
    MongoDB-based expense database with advanced querying and analytics
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.client = None
        self.db = None
        self.expenses_collection = None
        self.receipts_collection = None
        self.merchants_collection = None
        
        # Database stats
        self.stats = {
            'total_expenses': 0,
            'total_receipts': 0,
            'connection_status': 'disconnected'
        }
    
    async def initialize(self):
        """Initialize database connection and collections"""
        
        try:
            # Connect to MongoDB
            mongodb_uri = self.config.get('uri', 'mongodb://localhost:27017/')
            self.client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database
            db_name = self.config.get('database')
            if not db_name:
                raise ValueError("No database name provided in MongoDB configuration")
            self.db = self.client[db_name]
            
            # Get collections
            self.expenses_collection = self.db.expenses
            self.receipts_collection = self.db.receipts
            self.merchants_collection = self.db.merchants
            
            # Create indexes for better performance
            await self._create_indexes()
            
            # Update stats
            self.stats['connection_status'] = 'connected'
            self.stats['total_expenses'] = await self.get_expense_count()
            self.stats['total_receipts'] = await self.get_receipt_count()
            
            logging.info(f"💾 Database initialized: {db_name} ({self.stats['total_expenses']} expenses)")
            
        except ConnectionFailure as e:
            logging.error(f"❌ MongoDB connection failed: {e}")
            raise
        except Exception as e:
            logging.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def _create_indexes(self):
        """Create database indexes for optimal performance"""
        
        try:
            # Expenses collection indexes
            self.expenses_collection.create_index("expense_id", unique=True)
            self.expenses_collection.create_index("date")
            self.expenses_collection.create_index("merchant")
            self.expenses_collection.create_index("category")
            self.expenses_collection.create_index("amount")
            self.expenses_collection.create_index("gmail_account")
            self.expenses_collection.create_index([("date", -1), ("amount", -1)])
            
            # Receipts collection indexes
            self.receipts_collection.create_index("receipt_id", unique=True)
            self.receipts_collection.create_index("gmail_account")
            self.receipts_collection.create_index("processed_at")
            
            # Merchants collection indexes
            self.merchants_collection.create_index("name", unique=True)
            self.merchants_collection.create_index("category")
            
            logging.info("📚 Database indexes created")
            
        except Exception as e:
            logging.warning(f"⚠️ Index creation warning: {e}")
    
    async def save_expense(self, expense: ExpenseRecord) -> bool:
        """Save an expense record to the database"""
        
        try:
            expense_dict = asdict(expense)
            result = self.expenses_collection.replace_one(
                {"expense_id": expense.expense_id},
                expense_dict,
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                logging.info(f"💾 Saved expense: {expense.merchant} ${expense.amount}")
                return True
            else:
                logging.warning(f"⚠️ No changes made to expense: {expense.expense_id}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Failed to save expense {expense.expense_id}: {e}")
            return False
    
    async def save_expenses_batch(self, expenses: List[ExpenseRecord]) -> int:
        """Save multiple expenses in a batch operation"""
        
        if not expenses:
            return 0
        
        try:
            operations = []
            for expense in expenses:
                expense_dict = asdict(expense)
                operations.append({
                    "replaceOne": {
                        "filter": {"expense_id": expense.expense_id},
                        "replacement": expense_dict,
                        "upsert": True
                    }
                })
            
            result = self.expenses_collection.bulk_write(operations)
            saved_count = result.upserted_count + result.modified_count
            
            logging.info(f"💾 Batch saved {saved_count} expenses")
            return saved_count
            
        except Exception as e:
            logging.error(f"❌ Batch save failed: {e}")
            return 0
    
    async def get_expense(self, expense_id: str) -> Optional[ExpenseRecord]:
        """Get a specific expense by ID"""
        
        try:
            doc = self.expenses_collection.find_one({"expense_id": expense_id})
            if doc:
                # Remove MongoDB _id field
                doc.pop('_id', None)
                return ExpenseRecord(**doc)
            return None
            
        except Exception as e:
            logging.error(f"❌ Failed to get expense {expense_id}: {e}")
            return None
    
    async def get_expenses_by_date_range(self, start_date: str, end_date: str) -> List[ExpenseRecord]:
        """Get expenses within a date range"""
        
        try:
            cursor = self.expenses_collection.find({
                "date": {"$gte": start_date, "$lte": end_date}
            }).sort("date", -1)
            
            expenses = []
            for doc in cursor:
                doc.pop('_id', None)
                expenses.append(ExpenseRecord(**doc))
            
            return expenses
            
        except Exception as e:
            logging.error(f"❌ Failed to get expenses by date range: {e}")
            return []
    
    async def get_expenses_by_merchant(self, merchant: str) -> List[ExpenseRecord]:
        """Get all expenses for a specific merchant"""
        
        try:
            cursor = self.expenses_collection.find({
                "merchant": {"$regex": merchant, "$options": "i"}
            }).sort("date", -1)
            
            expenses = []
            for doc in cursor:
                doc.pop('_id', None)
                expenses.append(ExpenseRecord(**doc))
            
            return expenses
            
        except Exception as e:
            logging.error(f"❌ Failed to get expenses by merchant: {e}")
            return []
    
    async def get_expenses_by_category(self, category: str) -> List[ExpenseRecord]:
        """Get all expenses in a specific category"""
        
        try:
            cursor = self.expenses_collection.find({
                "category": category
            }).sort("date", -1)
            
            expenses = []
            for doc in cursor:
                doc.pop('_id', None)
                expenses.append(ExpenseRecord(**doc))
            
            return expenses
            
        except Exception as e:
            logging.error(f"❌ Failed to get expenses by category: {e}")
            return []
    
    async def search_expenses(self, query: Dict) -> List[ExpenseRecord]:
        """Advanced expense search with multiple criteria"""
        
        try:
            # Build MongoDB query
            mongo_query = {}
            
            # Text search
            if 'text' in query:
                mongo_query['$or'] = [
                    {"merchant": {"$regex": query['text'], "$options": "i"}},
                    {"items": {"$regex": query['text'], "$options": "i"}},
                    {"notes": {"$regex": query['text'], "$options": "i"}}
                ]
            
            # Amount range
            if 'min_amount' in query or 'max_amount' in query:
                amount_filter = {}
                if 'min_amount' in query:
                    amount_filter['$gte'] = query['min_amount']
                if 'max_amount' in query:
                    amount_filter['$lte'] = query['max_amount']
                mongo_query['amount'] = amount_filter
            
            # Date range
            if 'start_date' in query or 'end_date' in query:
                date_filter = {}
                if 'start_date' in query:
                    date_filter['$gte'] = query['start_date']
                if 'end_date' in query:
                    date_filter['$lte'] = query['end_date']
                mongo_query['date'] = date_filter
            
            # Category
            if 'category' in query:
                mongo_query['category'] = query['category']
            
            # Gmail account
            if 'gmail_account' in query:
                mongo_query['gmail_account'] = query['gmail_account']
            
            # Status
            if 'status' in query:
                mongo_query['status'] = query['status']
            
            # Tags
            if 'tags' in query:
                mongo_query['tags'] = {"$in": query['tags']}
            
            # Execute query
            cursor = self.expenses_collection.find(mongo_query).sort("date", -1)
            
            # Limit results
            limit = query.get('limit', 100)
            cursor = cursor.limit(limit)
            
            expenses = []
            for doc in cursor:
                doc.pop('_id', None)
                expenses.append(ExpenseRecord(**doc))
            
            return expenses
            
        except Exception as e:
            logging.error(f"❌ Expense search failed: {e}")
            return []
    
    async def get_expense_analytics(self, start_date: str, end_date: str) -> Dict:
        """Get expense analytics for a date range"""
        
        try:
            pipeline = [
                {
                    "$match": {
                        "date": {"$gte": start_date, "$lte": end_date}
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
            
            result = list(self.expenses_collection.aggregate(pipeline))
            
            if result:
                analytics = result[0]
                analytics.pop('_id', None)
                
                # Category breakdown
                category_pipeline = [
                    {"$match": {"date": {"$gte": start_date, "$lte": end_date}}},
                    {"$group": {"_id": "$category", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
                    {"$sort": {"total": -1}}
                ]
                
                category_breakdown = list(self.expenses_collection.aggregate(category_pipeline))
                analytics['category_breakdown'] = category_breakdown
                
                # Merchant breakdown
                merchant_pipeline = [
                    {"$match": {"date": {"$gte": start_date, "$lte": end_date}}},
                    {"$group": {"_id": "$merchant", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
                    {"$sort": {"total": -1}},
                    {"$limit": 10}
                ]
                
                merchant_breakdown = list(self.expenses_collection.aggregate(merchant_pipeline))
                analytics['top_merchants'] = merchant_breakdown
                
                return analytics
            else:
                return {
                    "total_amount": 0,
                    "total_count": 0,
                    "avg_amount": 0,
                    "max_amount": 0,
                    "min_amount": 0,
                    "category_breakdown": [],
                    "top_merchants": []
                }
                
        except Exception as e:
            logging.error(f"❌ Analytics query failed: {e}")
            return {}
    
    async def get_monthly_trends(self, months: int = 12) -> List[Dict]:
        """Get monthly spending trends"""
        
        try:
            start_date = (datetime.now() - timedelta(days=months * 30)).strftime('%Y-%m-%d')
            
            pipeline = [
                {
                    "$match": {
                        "date": {"$gte": start_date}
                    }
                },
                {
                    "$addFields": {
                        "year_month": {"$substr": ["$date", 0, 7]}
                    }
                },
                {
                    "$group": {
                        "_id": "$year_month",
                        "total_amount": {"$sum": "$amount"},
                        "transaction_count": {"$sum": 1},
                        "avg_amount": {"$avg": "$amount"}
                    }
                },
                {
                    "$sort": {"_id": 1}
                }
            ]
            
            result = list(self.expenses_collection.aggregate(pipeline))
            
            # Format results
            trends = []
            for item in result:
                trends.append({
                    "month": item["_id"],
                    "total_amount": round(item["total_amount"], 2),
                    "transaction_count": item["transaction_count"],
                    "avg_amount": round(item["avg_amount"], 2)
                })
            
            return trends
            
        except Exception as e:
            logging.error(f"❌ Monthly trends query failed: {e}")
            return []
    
    async def get_expense_count(self) -> int:
        """Get total number of expenses"""
        
        try:
            return self.expenses_collection.count_documents({})
        except Exception as e:
            logging.error(f"❌ Failed to get expense count: {e}")
            return 0
    
    async def get_receipt_count(self) -> int:
        """Get total number of receipts"""
        
        try:
            return self.receipts_collection.count_documents({})
        except Exception as e:
            logging.error(f"❌ Failed to get receipt count: {e}")
            return 0
    
    async def save_receipt_metadata(self, receipt_data: Dict) -> bool:
        """Save receipt metadata"""
        
        try:
            receipt_data['saved_at'] = datetime.now().isoformat()
            result = self.receipts_collection.replace_one(
                {"receipt_id": receipt_data.get("receipt_id")},
                receipt_data,
                upsert=True
            )
            
            return result.upserted_id is not None or result.modified_count > 0
            
        except Exception as e:
            logging.error(f"❌ Failed to save receipt metadata: {e}")
            return False
    
    async def update_expense_status(self, expense_id: str, status: str, notes: str = "") -> bool:
        """Update expense status and notes"""
        
        try:
            result = self.expenses_collection.update_one(
                {"expense_id": expense_id},
                {
                    "$set": {
                        "status": status,
                        "notes": notes,
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logging.error(f"❌ Failed to update expense status: {e}")
            return False
    
    async def add_expense_tags(self, expense_id: str, tags: List[str]) -> bool:
        """Add tags to an expense"""
        
        try:
            result = self.expenses_collection.update_one(
                {"expense_id": expense_id},
                {
                    "$addToSet": {"tags": {"$each": tags}},
                    "$set": {"updated_at": datetime.now().isoformat()}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logging.error(f"❌ Failed to add tags: {e}")
            return False
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        
        try:
            if self.db:
                db_stats = self.db.command("dbstats")
                return {
                    "connection_status": self.stats['connection_status'],
                    "total_expenses": self.stats['total_expenses'],
                    "total_receipts": self.stats['total_receipts'],
                    "database_size_mb": round(db_stats.get('dataSize', 0) / 1024 / 1024, 2),
                    "index_size_mb": round(db_stats.get('indexSize', 0) / 1024 / 1024, 2),
                    "collections": db_stats.get('collections', 0)
                }
            else:
                return {
                    "connection_status": self.stats['connection_status'],
                    "total_expenses": self.stats['total_expenses'],
                    "total_receipts": self.stats['total_receipts'],
                    "database_size_mb": 0,
                    "index_size_mb": 0,
                    "collections": 0
                }
        except Exception as e:
            logging.error(f"❌ Failed to get database stats: {e}")
            return {}
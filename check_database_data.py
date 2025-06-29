#!/usr/bin/env python3
"""
Check database connection and data
"""

import os
import sys
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

def check_database():
    """Check database connection and data"""
    print("🔍 Checking Database Connection and Data")
    print("=" * 50)
    
    # Get MongoDB connection string
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    db_name = os.getenv('MONGODB_DATABASE', 'expense')
    
    try:
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client[db_name]
        
        print(f"✅ Connected to MongoDB: {mongo_uri}")
        print(f"📊 Database: {db_name}")
        print()
        
        # Check collections
        collections = db.list_collection_names()
        print(f"📁 Collections found: {len(collections)}")
        for collection in collections:
            count = db[collection].count_documents({})
            print(f"   - {collection}: {count} documents")
        print()
        
        # Check specific collections for data
        collections_to_check = ['receipts', 'transactions', 'users', 'bank_accounts', 'teller_tokens']
        
        for collection_name in collections_to_check:
            if collection_name in collections:
                print(f"📋 {collection_name.upper()} Collection:")
                count = db[collection_name].count_documents({})
                print(f"   Total documents: {count}")
                
                if count > 0:
                    # Show sample documents
                    sample = list(db[collection_name].find().limit(3))
                    for i, doc in enumerate(sample, 1):
                        print(f"   Sample {i}:")
                        # Convert ObjectId to string for display
                        if '_id' in doc:
                            doc['_id'] = str(doc['_id'])
                        # Show key fields
                        for key, value in list(doc.items())[:5]:  # Show first 5 fields
                            if isinstance(value, datetime):
                                value = value.isoformat()
                            print(f"     {key}: {value}")
                        if len(doc) > 5:
                            print(f"     ... and {len(doc) - 5} more fields")
                        print()
                else:
                    print("   No documents found")
                print()
        
        # Check for any data that might be in other collections
        print("🔍 Checking for any data in other collections:")
        for collection in collections:
            if collection not in collections_to_check:
                count = db[collection].count_documents({})
                if count > 0:
                    print(f"   - {collection}: {count} documents")
        
        # Show a sample document from receipts to determine the R2 key field
        if 'receipts' in collections:
            print("\nSample document from receipts collection:")
            sample = db['receipts'].find_one()
            if sample:
                for k, v in sample.items():
                    print(f"  {k}: {v}")
            else:
                print("  No documents found.")
        
        print()
        print("=" * 50)
        print("📊 SUMMARY:")
        print(f"   - Total collections: {len(collections)}")
        total_docs = sum(db[coll].count_documents({}) for coll in collections)
        print(f"   - Total documents: {total_docs}")
        
        if total_docs == 0:
            print("⚠️  No data found in database!")
            print("   Consider running data import scripts or syncing with Teller")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_database() 
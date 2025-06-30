#!/usr/bin/env python3
"""
Script to clear all database collections for a fresh start with Teller
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.mongo_service import MongoService

def clear_database():
    """Clear all collections in the database"""
    try:
        mongo = MongoService()
        
        print("🗄️  Connecting to MongoDB...")
        
        # Get current counts
        bank_transactions = mongo.get_bank_transactions()
        teller_tokens = mongo.get_teller_tokens()
        receipts = mongo.get_receipts()
        
        print(f"📊 Current data:")
        print(f"   Bank transactions: {len(bank_transactions)}")
        print(f"   Teller tokens: {len(teller_tokens)}")
        print(f"   Receipts: {len(receipts)}")
        
        # Clear collections
        print("\n🧹 Clearing collections...")
        
        # Clear bank_transactions collection
        if bank_transactions:
            mongo.client[mongo.database_name]['bank_transactions'].delete_many({})
            print("   ✅ Cleared bank_transactions")
        
        # Clear transactions collection (if it exists)
        try:
            transactions_count = mongo.client[mongo.database_name]['transactions'].count_documents({})
            if transactions_count > 0:
                mongo.client[mongo.database_name]['transactions'].delete_many({})
                print(f"   ✅ Cleared transactions ({transactions_count} records)")
        except Exception as e:
            print(f"   ℹ️  No transactions collection or already empty")
        
        # Clear teller_tokens collection
        if teller_tokens:
            mongo.client[mongo.database_name]['teller_tokens'].delete_many({})
            print("   ✅ Cleared teller_tokens")
        
        # Clear receipts collection
        if receipts:
            mongo.client[mongo.database_name]['receipts'].delete_many({})
            print("   ✅ Cleared receipts")
        
        # Verify clearing
        print("\n🔍 Verifying clearing...")
        remaining_bank = len(mongo.get_bank_transactions())
        remaining_tokens = len(mongo.get_teller_tokens())
        remaining_receipts = len(mongo.get_receipts())
        
        print(f"📊 Remaining data:")
        print(f"   Bank transactions: {remaining_bank}")
        print(f"   Teller tokens: {remaining_tokens}")
        print(f"   Receipts: {remaining_receipts}")
        
        if remaining_bank == 0 and remaining_tokens == 0 and remaining_receipts == 0:
            print("\n✅ Database cleared successfully!")
            print("🚀 Ready for fresh Teller connection!")
        else:
            print("\n⚠️  Some data may still remain")
            
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🗑️  Database Clear Script")
    print("=" * 40)
    
    # Ask for confirmation
    response = input("Are you sure you want to clear ALL data? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        success = clear_database()
        if success:
            print("\n🎉 Database cleared! You can now connect Teller fresh.")
        else:
            print("\n❌ Failed to clear database.")
    else:
        print("❌ Operation cancelled.") 
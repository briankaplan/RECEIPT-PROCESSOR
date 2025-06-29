#!/usr/bin/env python3
"""Check if transactions have receipt URLs"""

import os
from pymongo import MongoClient

def check_receipt_urls():
    """Check if transactions have receipt URLs"""
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri:
            print("❌ No MongoDB URI configured")
            return
        
        client = MongoClient(mongo_uri)
        db = client.expense
        
        # Check transactions with receipt URLs
        transactions_with_receipts = list(db.bank_transactions.find({
            'receipt_url': {'$exists': True, '$ne': ''}
        }).limit(10))
        
        print(f"📊 Found {len(transactions_with_receipts)} transactions with receipt URLs:")
        for t in transactions_with_receipts:
            receipt_url = t.get('receipt_url', 'None')
            print(f"  ✅ {t.get('merchant', 'Unknown')} - ${t.get('amount', 0):.2f}")
            print(f"      Receipt URL: {receipt_url[:80]}...")
            print()
        
        # Check total transactions
        total_transactions = db.bank_transactions.count_documents({})
        print(f"📈 Total transactions: {total_transactions}")
        print(f"📈 Transactions with receipts: {len(transactions_with_receipts)}")
        print(f"📈 Receipt coverage: {(len(transactions_with_receipts) / total_transactions * 100):.1f}%")
        
        # Check receipts collection
        total_receipts = db.receipts.count_documents({})
        receipts_with_urls = list(db.receipts.find({
            'r2_url': {'$exists': True, '$ne': ''}
        }).limit(5))
        
        print(f"\n📧 Receipts collection:")
        print(f"  Total receipts: {total_receipts}")
        print(f"  Receipts with R2 URLs: {len(receipts_with_urls)}")
        
        for r in receipts_with_urls:
            print(f"  📄 {r.get('merchant', 'Unknown')} - {r.get('r2_url', 'None')[:80]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_receipt_urls() 
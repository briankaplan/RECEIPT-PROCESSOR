#!/usr/bin/env python3
"""Check for matching transactions and receipts"""

import os
from pymongo import MongoClient

def check_matches():
    """Check for matching transactions and receipts"""
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri:
            print("❌ No MongoDB URI configured")
            return
        
        client = MongoClient(mongo_uri)
        db = client.expense
        
        # Check for Midjourney and Anthropic transactions
        transactions = list(db.bank_transactions.find({
            'merchant': {'$regex': 'MIDJOURNEY|ANTHROPIC', '$options': 'i'}
        }).limit(10))
        
        print(f"💰 Found {len(transactions)} Midjourney/Anthropic transactions:")
        for t in transactions:
            print(f"  📊 {t.get('merchant', 'Unknown')} - ${t.get('amount', 0):.2f} - Date: {t.get('date', 'Unknown')}")
        
        # Check for receipts
        receipts = list(db.receipts.find({
            'merchant': {'$regex': 'Midjourney|Anthropic', '$options': 'i'}
        }).limit(10))
        
        print(f"\n📧 Found {len(receipts)} Midjourney/Anthropic receipts:")
        for r in receipts:
            print(f"  📄 {r.get('merchant', 'Unknown')} - Date: {r.get('date', 'Unknown')} - Transaction ID: {r.get('transaction_id', 'None')}")
        
        # Check for transactions with receipt URLs
        transactions_with_receipts = list(db.bank_transactions.find({
            'receipt_url': {'$exists': True, '$ne': ''}
        }).limit(5))
        
        print(f"\n🔗 Found {len(transactions_with_receipts)} transactions with receipt URLs:")
        for t in transactions_with_receipts:
            print(f"  ✅ {t.get('merchant', 'Unknown')} - ${t.get('amount', 0):.2f} - Receipt URL: {t.get('receipt_url', 'None')[:50]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_matches() 
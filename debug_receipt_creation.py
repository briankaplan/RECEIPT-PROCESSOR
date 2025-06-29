#!/usr/bin/env python3
"""Debug receipt creation process"""

import os
import logging
from datetime import datetime
from pymongo import MongoClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_receipt_creation():
    """Debug the receipt creation process"""
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri:
            print("❌ No MongoDB URI configured")
            return
        
        client = MongoClient(mongo_uri)
        db = client.expense
        
        print("🔍 DEBUGGING RECEIPT CREATION PROCESS")
        print("=" * 50)
        
        # 1. Check all receipts and their fields
        all_receipts = list(db.receipts.find({}))
        print(f"\n📧 ALL RECEIPTS ({len(all_receipts)} total):")
        
        for i, receipt in enumerate(all_receipts[:5], 1):
            print(f"\n  Receipt {i}:")
            print(f"    ID: {receipt.get('_id')}")
            print(f"    Merchant: {receipt.get('merchant', 'None')}")
            print(f"    Amount: {receipt.get('amount', 'None')}")
            print(f"    Transaction ID: {receipt.get('transaction_id', 'None')}")
            print(f"    Email ID: {receipt.get('email_id', 'None')}")
            print(f"    R2 URL: {receipt.get('r2_url', 'None')[:50] if receipt.get('r2_url') else 'None'}...")
            print(f"    Created at: {receipt.get('scanned_at', 'None')}")
            print(f"    All fields: {list(receipt.keys())}")
        
        # 2. Check transactions with receipt URLs
        transactions_with_receipts = list(db.bank_transactions.find({
            'receipt_url': {'$exists': True, '$ne': ''}
        }))
        print(f"\n💰 TRANSACTIONS WITH RECEIPT URLS ({len(transactions_with_receipts)} total):")
        
        for i, transaction in enumerate(transactions_with_receipts, 1):
            print(f"\n  Transaction {i}:")
            print(f"    ID: {transaction.get('_id')}")
            print(f"    Merchant: {transaction.get('merchant', 'None')}")
            print(f"    Amount: {transaction.get('amount', 'None')}")
            print(f"    Receipt URL: {transaction.get('receipt_url', 'None')[:50] if transaction.get('receipt_url') else 'None'}...")
            print(f"    Receipt ID: {transaction.get('receipt_id', 'None')}")
        
        # 3. Cross-reference: Find receipts that should be linked
        print(f"\n🔗 CROSS-REFERENCE ANALYSIS:")
        
        for receipt in all_receipts[:3]:
            receipt_merchant = receipt.get('merchant', '').lower()
            receipt_amount = receipt.get('amount', 0)
            
            # Find matching transactions
            matching_transactions = list(db.bank_transactions.find({
                'merchant': {'$regex': receipt_merchant, '$options': 'i'}
            }))
            
            print(f"\n  Receipt: {receipt.get('merchant', 'Unknown')} - ${receipt_amount}")
            print(f"    Transaction ID in receipt: {receipt.get('transaction_id', 'None')}")
            
            if matching_transactions:
                print(f"    Found {len(matching_transactions)} matching transactions:")
                for txn in matching_transactions[:3]:
                    print(f"      - {txn.get('merchant', 'Unknown')} - ${txn.get('amount', 0)} (ID: {txn.get('_id')})")
                    print(f"        Receipt URL: {txn.get('receipt_url', 'None')[:50] if txn.get('receipt_url') else 'None'}...")
            else:
                print(f"    No matching transactions found")
        
        # 4. Check if there are any receipts with transaction_id but no R2 URL
        receipts_with_txn_id = list(db.receipts.find({
            'transaction_id': {'$exists': True, '$ne': None}
        }))
        print(f"\n📊 RECEIPTS WITH TRANSACTION ID: {len(receipts_with_txn_id)}")
        
        # 5. Check if there are any transactions with receipt_id but no receipt_url
        transactions_with_receipt_id = list(db.bank_transactions.find({
            'receipt_id': {'$exists': True, '$ne': None}
        }))
        print(f"📊 TRANSACTIONS WITH RECEIPT ID: {len(transactions_with_receipt_id)}")
        
        # 6. Check the most recent receipts to see their creation pattern
        recent_receipts = list(db.receipts.find({}).sort('scanned_at', -1).limit(5))
        print(f"\n🕒 MOST RECENT RECEIPTS:")
        
        for receipt in recent_receipts:
            print(f"  {receipt.get('merchant', 'Unknown')} - {receipt.get('scanned_at', 'Unknown')}")
            print(f"    Transaction ID: {receipt.get('transaction_id', 'None')}")
            print(f"    R2 URL: {'Yes' if receipt.get('r2_url') else 'No'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_receipt_creation() 
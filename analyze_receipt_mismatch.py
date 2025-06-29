#!/usr/bin/env python3
"""Analyze the receipt/transaction mismatch"""

import os
from pymongo import MongoClient
from datetime import datetime

def analyze_mismatch():
    """Analyze the receipt/transaction mismatch"""
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri:
            print("❌ No MongoDB URI configured")
            return
        
        client = MongoClient(mongo_uri)
        db = client.expense
        
        print("🔍 DETAILED ANALYSIS OF RECEIPT/TRANSACTION MISMATCH")
        print("=" * 60)
        
        # 1. Check all receipts
        all_receipts = list(db.receipts.find({}))
        print(f"\n📧 ALL RECEIPTS ({len(all_receipts)} total):")
        for i, receipt in enumerate(all_receipts[:10], 1):
            transaction_id = receipt.get('transaction_id', 'None')
            r2_url = receipt.get('r2_url', 'None')
            print(f"  {i}. {receipt.get('merchant', 'Unknown')} - Transaction ID: {transaction_id}")
            print(f"     R2 URL: {r2_url[:50] if r2_url != 'None' else 'None'}...")
        
        # 2. Check receipts with transaction_id
        matched_receipts = [r for r in all_receipts if r.get('transaction_id')]
        print(f"\n🔗 MATCHED RECEIPTS ({len(matched_receipts)} total):")
        for receipt in matched_receipts:
            print(f"  ✅ {receipt.get('merchant', 'Unknown')} -> Transaction: {receipt.get('transaction_id')}")
        
        # 3. Check receipts without transaction_id
        unmatched_receipts = [r for r in all_receipts if not r.get('transaction_id')]
        print(f"\n❌ UNMATCHED RECEIPTS ({len(unmatched_receipts)} total):")
        for receipt in unmatched_receipts:
            print(f"  ❌ {receipt.get('merchant', 'Unknown')} - No transaction linked")
        
        # 4. Check transactions with receipt_url
        transactions_with_receipts = list(db.bank_transactions.find({
            'receipt_url': {'$exists': True, '$ne': ''}
        }))
        print(f"\n💰 TRANSACTIONS WITH RECEIPT URLS ({len(transactions_with_receipts)} total):")
        for transaction in transactions_with_receipts:
            receipt_url = transaction.get('receipt_url', 'None')
            print(f"  💰 {transaction.get('merchant', 'Unknown')} - ${transaction.get('amount', 0):.2f}")
            print(f"     Receipt URL: {receipt_url[:50] if receipt_url != 'None' else 'None'}...")
        
        # 5. Check transactions with receipt_id
        transactions_with_receipt_id = list(db.bank_transactions.find({
            'receipt_id': {'$exists': True, '$ne': ''}
        }))
        print(f"\n🆔 TRANSACTIONS WITH RECEIPT ID ({len(transactions_with_receipt_id)} total):")
        for transaction in transactions_with_receipt_id:
            receipt_id = transaction.get('receipt_id', 'None')
            receipt_url = transaction.get('receipt_url', 'None')
            print(f"  🆔 {transaction.get('merchant', 'Unknown')} - Receipt ID: {receipt_id}")
            print(f"     Receipt URL: {receipt_url[:50] if receipt_url != 'None' else 'None'}...")
        
        # 6. Cross-reference analysis
        print(f"\n🔍 CROSS-REFERENCE ANALYSIS:")
        
        # Find receipts that should be linked but aren't
        orphaned_receipts = []
        for receipt in unmatched_receipts:
            # Check if there's a matching transaction
            merchant = receipt.get('merchant', '').upper()
            matching_transactions = list(db.bank_transactions.find({
                'merchant': {'$regex': merchant, '$options': 'i'}
            }))
            if matching_transactions:
                orphaned_receipts.append((receipt, matching_transactions))
        
        print(f"  📊 Found {len(orphaned_receipts)} receipts that could be linked to transactions:")
        for receipt, transactions in orphaned_receipts[:5]:
            print(f"    📄 {receipt.get('merchant', 'Unknown')} could match:")
            for txn in transactions[:3]:
                print(f"      💰 {txn.get('merchant', 'Unknown')} - ${txn.get('amount', 0):.2f} - {txn.get('date', 'Unknown')}")
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"  📧 Total receipts: {len(all_receipts)}")
        print(f"  🔗 Matched receipts: {len(matched_receipts)}")
        print(f"  ❌ Unmatched receipts: {len(unmatched_receipts)}")
        print(f"  💰 Transactions with receipt URLs: {len(transactions_with_receipts)}")
        print(f"  🆔 Transactions with receipt IDs: {len(transactions_with_receipt_id)}")
        print(f"  📊 Potential matches found: {len(orphaned_receipts)}")
        
        if len(matched_receipts) != len(transactions_with_receipts):
            print(f"\n⚠️  MISMATCH DETECTED!")
            print(f"   Matched receipts ({len(matched_receipts)}) != Transactions with receipt URLs ({len(transactions_with_receipts)})")
            print(f"   This suggests the linking process is not working correctly.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    analyze_mismatch() 
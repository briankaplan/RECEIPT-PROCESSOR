#!/usr/bin/env python3
"""Test email subject extraction"""

import os
import logging
from datetime import datetime
from pymongo import MongoClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_email_subjects():
    """Test email subject extraction"""
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri:
            print("❌ No MongoDB URI configured")
            return
        
        client = MongoClient(mongo_uri)
        db = client.expense
        
        print("🔍 TESTING EMAIL SUBJECT EXTRACTION")
        print("=" * 50)
        
        # Get all receipts and their subjects
        all_receipts = list(db.receipts.find({}))
        print(f"\n📧 EMAIL SUBJECTS FROM RECEIPTS:")
        
        for i, receipt in enumerate(all_receipts[:10], 1):
            subject = receipt.get('subject', 'No subject')
            merchant = receipt.get('merchant', 'Unknown')
            amount = receipt.get('amount', 0)
            from_email = receipt.get('from_email', 'Unknown')
            
            print(f"\n  Receipt {i}:")
            print(f"    Subject: '{subject}'")
            print(f"    From: {from_email}")
            print(f"    Extracted Merchant: {merchant}")
            print(f"    Extracted Amount: ${amount}")
            
            # Test the extraction logic
            from enhanced_receipt_processor import EnhancedReceiptProcessor
            processor = EnhancedReceiptProcessor(client)
            
            test_merchant, test_amount = processor._extract_basic_info(subject)
            print(f"    Test Extraction - Merchant: {test_merchant}, Amount: ${test_amount}")
            
            if test_amount != amount:
                print(f"    ⚠️  EXTRACTION MISMATCH!")
        
        # Check if there are any receipts with non-zero amounts
        receipts_with_amounts = [r for r in all_receipts if r.get('amount', 0) > 0]
        print(f"\n📊 RECEIPTS WITH NON-ZERO AMOUNTS: {len(receipts_with_amounts)}")
        
        if receipts_with_amounts:
            for receipt in receipts_with_amounts:
                print(f"  ✅ {receipt.get('merchant', 'Unknown')} - ${receipt.get('amount', 0)}")
        else:
            print("  ❌ No receipts with non-zero amounts found")
        
        # Check transactions to see what amounts we should be looking for
        midjourney_transactions = list(db.bank_transactions.find({
            'merchant': {'$regex': 'midjourney', '$options': 'i'}
        }))
        anthropic_transactions = list(db.bank_transactions.find({
            'merchant': {'$regex': 'anthropic', '$options': 'i'}
        }))
        
        print(f"\n💰 TRANSACTION AMOUNTS TO MATCH:")
        print(f"  Midjourney transactions: {len(midjourney_transactions)}")
        for txn in midjourney_transactions[:3]:
            print(f"    ${abs(txn.get('amount', 0))}")
        
        print(f"  Anthropic transactions: {len(anthropic_transactions)}")
        for txn in anthropic_transactions[:3]:
            print(f"    ${abs(txn.get('amount', 0))}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_email_subjects() 
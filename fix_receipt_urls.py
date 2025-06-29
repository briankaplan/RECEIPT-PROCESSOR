#!/usr/bin/env python3
"""Fix matched receipts without URLs and ensure all receipts are properly linked"""

import os
import logging
from pymongo import MongoClient
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_and_fix_receipt_urls():
    """Check for matched receipts without URLs and fix them"""
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri:
            logger.error("❌ No MongoDB URI configured")
            return
        
        client = MongoClient(mongo_uri)
        db = client.expense
        
        logger.info("🔍 Checking for receipt URL issues...")
        
        # 1. Check receipts collection for issues
        all_receipts = list(db.receipts.find({}))
        logger.info(f"📧 Found {len(all_receipts)} total receipts")
        
        # Check for receipts without R2 URLs
        receipts_without_urls = [r for r in all_receipts if not r.get('r2_url')]
        logger.info(f"❌ Found {len(receipts_without_urls)} receipts without R2 URLs")
        
        # Check for receipts with transaction_id but no R2 URL
        matched_receipts_without_urls = [r for r in all_receipts if r.get('transaction_id') and not r.get('r2_url')]
        logger.info(f"⚠️ Found {len(matched_receipts_without_urls)} matched receipts without R2 URLs")
        
        # 2. Check transactions collection for issues
        all_transactions = list(db.bank_transactions.find({}))
        logger.info(f"💰 Found {len(all_transactions)} total transactions")
        
        # Check for transactions with receipt_id but no receipt_url
        transactions_with_receipt_id = [t for t in all_transactions if t.get('receipt_id')]
        transactions_without_receipt_url = [t for t in transactions_with_receipt_id if not t.get('receipt_url')]
        logger.info(f"⚠️ Found {len(transactions_without_receipt_url)} transactions with receipt_id but no receipt_url")
        
        # 3. Check for orphaned receipt references
        orphaned_receipts = []
        for receipt in all_receipts:
            if receipt.get('transaction_id'):
                # Check if the referenced transaction exists
                transaction = db.bank_transactions.find_one({'_id': receipt['transaction_id']})
                if not transaction:
                    orphaned_receipts.append(receipt)
        
        logger.info(f"⚠️ Found {len(orphaned_receipts)} receipts with non-existent transaction references")
        
        # 4. Fix issues
        fixes_applied = 0
        
        # Fix 1: Unmatch receipts without R2 URLs
        for receipt in matched_receipts_without_urls:
            logger.info(f"🔧 Unmatching receipt {receipt['_id']} (no R2 URL)")
            db.receipts.update_one(
                {'_id': receipt['_id']},
                {'$unset': {'transaction_id': '', 'match_confidence': '', 'match_type': '', 'matched_at': ''}}
            )
            fixes_applied += 1
        
        # Fix 2: Remove orphaned receipt references from transactions
        for receipt in orphaned_receipts:
            logger.info(f"🔧 Removing orphaned receipt reference {receipt['_id']}")
            db.receipts.update_one(
                {'_id': receipt['_id']},
                {'$unset': {'transaction_id': '', 'match_confidence': '', 'match_type': '', 'matched_at': ''}}
            )
            fixes_applied += 1
        
        # Fix 3: Remove receipt_id from transactions without receipt_url
        for transaction in transactions_without_receipt_url:
            logger.info(f"🔧 Removing receipt_id from transaction {transaction['_id']} (no receipt_url)")
            db.bank_transactions.update_one(
                {'_id': transaction['_id']},
                {'$unset': {'receipt_id': '', 'receipt_matched': '', 'receipt_matched_at': '', 'receipt_confidence': ''}}
            )
            fixes_applied += 1
        
        # 5. Verify R2 URLs are accessible
        logger.info("🔍 Verifying R2 URLs are accessible...")
        try:
            from r2_client import R2Client
            r2_client = R2Client()
            
            if r2_client.is_connected():
                receipts_with_urls = [r for r in all_receipts if r.get('r2_url')]
                logger.info(f"📄 Found {len(receipts_with_urls)} receipts with R2 URLs")
                
                # Test a few URLs
                for receipt in receipts_with_urls[:3]:
                    r2_key = receipt.get('r2_key')
                    if r2_key:
                        # Generate fresh URL
                        fresh_url = r2_client.get_file_url(r2_key)
                        if fresh_url:
                            logger.info(f"✅ R2 URL working for {receipt.get('merchant', 'Unknown')}")
                        else:
                            logger.warning(f"❌ R2 URL generation failed for {receipt.get('merchant', 'Unknown')}")
            else:
                logger.warning("⚠️ R2 client not connected")
                
        except Exception as e:
            logger.error(f"❌ Error checking R2 URLs: {e}")
        
        # 6. Final status report
        logger.info("📊 Final Status Report:")
        
        # Re-count after fixes
        final_receipts = list(db.receipts.find({}))
        final_transactions = list(db.bank_transactions.find({}))
        
        matched_receipts = [r for r in final_receipts if r.get('transaction_id')]
        transactions_with_receipts = [t for t in final_transactions if t.get('receipt_url')]
        
        logger.info(f"  📧 Total receipts: {len(final_receipts)}")
        logger.info(f"  📧 Matched receipts: {len(matched_receipts)}")
        logger.info(f"  📧 Receipts with R2 URLs: {len([r for r in final_receipts if r.get('r2_url')])}")
        logger.info(f"  💰 Total transactions: {len(final_transactions)}")
        logger.info(f"  💰 Transactions with receipt URLs: {len(transactions_with_receipts)}")
        logger.info(f"  🔧 Fixes applied: {fixes_applied}")
        
        if fixes_applied > 0:
            logger.info("✅ Database cleaned up successfully!")
            logger.info("🔄 You may want to re-run the personalized email search to re-match receipts")
        else:
            logger.info("✅ No issues found - database is clean!")
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    check_and_fix_receipt_urls() 
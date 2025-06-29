#!/usr/bin/env python3
"""
Clean up R2 URLs from database transactions
Removes receipt_url fields to avoid dangling links after R2 cleanup
"""

import os
import logging
from datetime import datetime
from mongo_client import MongoDBClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_database_r2_urls():
    """Remove R2 URLs from database transactions"""
    try:
        mongo_client = MongoDBClient()
        
        if not mongo_client.is_connected():
            logger.error("❌ MongoDB not connected")
            return
        
        logger.info("🔍 Finding transactions with R2 URLs...")
        
        # Find all transactions with receipt_url fields
        transactions_with_urls = mongo_client.db.bank_transactions.find({
            "receipt_url": {"$exists": True}
        })
        
        count = 0
        cleaned_count = 0
        
        for transaction in transactions_with_urls:
            count += 1
            receipt_url = transaction.get('receipt_url', '')
            
            # Check if it's an R2 URL
            if 'r2.cloudflarestorage.com' in receipt_url or 'cloudflare.com' in receipt_url:
                logger.info(f"🧹 Cleaning R2 URL from transaction: {transaction.get('description', 'Unknown')} - {transaction.get('amount', 0)}")
                
                # Remove the receipt_url field
                result = mongo_client.db.bank_transactions.update_one(
                    {"_id": transaction["_id"]},
                    {
                        "$unset": {"receipt_url": ""},
                        "$set": {
                            "r2_url_cleaned_at": datetime.utcnow(),
                            "r2_url_cleaned": True
                        }
                    }
                )
                
                if result.modified_count > 0:
                    cleaned_count += 1
                    logger.info(f"✅ Cleaned R2 URL from transaction {transaction['_id']}")
                else:
                    logger.warning(f"⚠️ Failed to clean R2 URL from transaction {transaction['_id']}")
        
        logger.info(f"📊 Database cleanup complete:")
        logger.info(f"   Total transactions with URLs: {count}")
        logger.info(f"   R2 URLs cleaned: {cleaned_count}")
        
        # Also clean up any receipt records that might have R2 URLs
        logger.info("🔍 Checking receipt records for R2 URLs...")
        
        receipts_with_urls = mongo_client.db.receipts.find({
            "r2_url": {"$exists": True}
        })
        
        receipt_count = 0
        receipt_cleaned = 0
        
        for receipt in receipts_with_urls:
            receipt_count += 1
            r2_url = receipt.get('r2_url', '')
            
            if 'r2.cloudflarestorage.com' in r2_url or 'cloudflare.com' in r2_url:
                logger.info(f"🧹 Cleaning R2 URL from receipt: {receipt.get('_id')}")
                
                result = mongo_client.db.receipts.update_one(
                    {"_id": receipt["_id"]},
                    {
                        "$unset": {"r2_url": ""},
                        "$set": {
                            "r2_url_cleaned_at": datetime.utcnow(),
                            "r2_url_cleaned": True
                        }
                    }
                )
                
                if result.modified_count > 0:
                    receipt_cleaned += 1
                    logger.info(f"✅ Cleaned R2 URL from receipt {receipt['_id']}")
        
        logger.info(f"📊 Receipt cleanup complete:")
        logger.info(f"   Total receipts with URLs: {receipt_count}")
        logger.info(f"   R2 URLs cleaned: {receipt_cleaned}")
        
        logger.info("🎉 Database R2 URL cleanup complete!")
        
    except Exception as e:
        logger.error(f"❌ Error cleaning database R2 URLs: {e}")

if __name__ == "__main__":
    clean_database_r2_urls() 
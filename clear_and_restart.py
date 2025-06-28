#!/usr/bin/env python3
"""
Clear R2 Storage and Restart System with Proper OCR and Matching
"""

import os
import sys
import logging
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_r2_storage():
    """Clear all files from R2 storage"""
    try:
        from r2_client import R2Client
        r2_client = R2Client()
        
        if not r2_client.is_connected():
            logger.error("❌ R2 client not connected")
            return False
        
        logger.info("🗑️ Clearing R2 storage...")
        
        # List all objects in the bucket
        objects = r2_client.list_files()
        
        if not objects:
            logger.info("✅ R2 storage is already empty")
            return True
        
        # Delete all objects
        deleted_count = 0
        for obj in objects:
            try:
                if r2_client.delete_file(obj['key']):
                    deleted_count += 1
                    logger.info(f"🗑️ Deleted: {obj['key']}")
                else:
                    logger.error(f"Failed to delete: {obj['key']}")
            except Exception as e:
                logger.error(f"Failed to delete {obj['key']}: {e}")
        
        logger.info(f"✅ Cleared {deleted_count} files from R2 storage")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to clear R2 storage: {e}")
        return False

def clear_database_receipts():
    """Clear receipt records from database"""
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri:
            logger.error("❌ No MongoDB URI configured")
            return False
        
        client = MongoClient(mongo_uri)
        db = client['expense']
        
        # Count receipts before deletion
        receipt_count = db.receipts.count_documents({})
        
        if receipt_count == 0:
            logger.info("✅ Database receipts already empty")
            return True
        
        # Delete all receipts
        result = db.receipts.delete_many({})
        
        logger.info(f"✅ Cleared {result.deleted_count} receipt records from database")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to clear database receipts: {e}")
        return False

def reset_transaction_receipt_links():
    """Reset receipt links in transactions"""
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri:
            logger.error("❌ No MongoDB URI configured")
            return False
        
        client = MongoClient(mongo_uri)
        db = client['expense']
        
        # Reset receipt_url field in transactions
        result = db.bank_transactions.update_many(
            {"receipt_url": {"$exists": True}},
            {"$unset": {"receipt_url": ""}}
        )
        
        logger.info(f"✅ Reset receipt links for {result.modified_count} transactions")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to reset transaction receipt links: {e}")
        return False

def main():
    """Main function to clear everything and restart"""
    logger.info("🚀 Starting system cleanup and restart...")
    
    # Step 1: Clear R2 storage
    logger.info("📦 Step 1: Clearing R2 storage...")
    if clear_r2_storage():
        logger.info("✅ R2 storage cleared successfully")
    else:
        logger.error("❌ Failed to clear R2 storage")
        return False
    
    # Step 2: Clear database receipts
    logger.info("🗄️ Step 2: Clearing database receipts...")
    if clear_database_receipts():
        logger.info("✅ Database receipts cleared successfully")
    else:
        logger.error("❌ Failed to clear database receipts")
        return False
    
    # Step 3: Reset transaction receipt links
    logger.info("🔗 Step 3: Resetting transaction receipt links...")
    if reset_transaction_receipt_links():
        logger.info("✅ Transaction receipt links reset successfully")
    else:
        logger.error("❌ Failed to reset transaction receipt links")
        return False
    
    logger.info("🎉 System cleanup complete! Ready for new workflow.")
    logger.info("📋 Next steps:")
    logger.info("   1. Run personalized email search with new workflow")
    logger.info("   2. Match receipts to transactions before R2 upload")
    logger.info("   3. Only upload matched receipts to R2")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("✅ Cleanup completed successfully")
    else:
        logger.error("❌ Cleanup failed")
        sys.exit(1) 
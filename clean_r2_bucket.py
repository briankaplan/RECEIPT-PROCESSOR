#!/usr/bin/env python3
"""
Fast R2 bucket cleanup script
Deletes all files in the bucket using bulk operations
"""

import os
import logging
from r2_client import R2Client

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_r2_bucket():
    """Clean all files from R2 bucket"""
    try:
        r2 = R2Client()
        
        # Get current stats
        stats = r2.get_stats()
        logger.info(f"Current bucket stats: {stats}")
        
        if stats['total_files'] == 0:
            logger.info("✅ Bucket is already empty")
            return
        
        # List all files
        logger.info("📋 Listing all files...")
        files = r2.list_files(limit=1000)
        
        if not files:
            logger.info("✅ No files found to delete")
            return
        
        # Extract file keys
        file_keys = [f['key'] for f in files]
        logger.info(f"🗑️ Deleting {len(file_keys)} files...")
        
        # Delete files in batches (R2 allows up to 1000 objects per delete request)
        batch_size = 1000
        deleted_count = 0
        
        for i in range(0, len(file_keys), batch_size):
            batch = file_keys[i:i + batch_size]
            
            # Use bulk delete if available, otherwise delete individually
            try:
                # Try bulk delete first
                deleted = r2.bulk_delete_files(batch)
                deleted_count += deleted
                logger.info(f"✅ Deleted batch {i//batch_size + 1}: {deleted} files")
            except AttributeError:
                # Fallback to individual deletes
                for key in batch:
                    if r2.delete_file(key):
                        deleted_count += 1
                logger.info(f"✅ Deleted batch {i//batch_size + 1}: {len(batch)} files")
        
        # Verify cleanup
        final_stats = r2.get_stats()
        logger.info(f"🎉 Cleanup complete! Final stats: {final_stats}")
        logger.info(f"📊 Total files deleted: {deleted_count}")
        
    except Exception as e:
        logger.error(f"❌ Error cleaning R2 bucket: {e}")

if __name__ == "__main__":
    clean_r2_bucket() 
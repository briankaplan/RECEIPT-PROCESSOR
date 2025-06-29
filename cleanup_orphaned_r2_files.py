#!/usr/bin/env python3
"""
Delete orphaned files from R2 that are not referenced in MongoDB receipts.r2_key
"""
import os
import sys
from pymongo import MongoClient

# Import the existing R2 client from your app
sys.path.append('.')
from app.services.r2_service import R2Service

# --- CONFIG ---
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'expense')

# --- GET REFERENCED KEYS FROM MONGODB ---
def get_referenced_r2_keys():
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]
    keys = set()
    for doc in db['receipts'].find({}, {'r2_key': 1}):
        if 'r2_key' in doc:
            keys.add(doc['r2_key'])
    client.close()
    return keys

# --- LIST ALL FILES IN R2 BUCKET ---
def list_r2_files():
    r2_service = R2Service()
    all_files = set()
    try:
        files = r2_service.list_files()
        # If files is a list of dicts, extract the 'key', 'Key', or 'filename' field
        if files and isinstance(files[0], dict):
            if 'key' in files[0]:
                all_files = set(f['key'] for f in files)
            elif 'Key' in files[0]:
                all_files = set(f['Key'] for f in files)
            elif 'filename' in files[0]:
                all_files = set(f['filename'] for f in files)
            else:
                print("Unknown file dict structure:", files[0])
                all_files = set()
        else:
            all_files = set(files)
    except Exception as e:
        print(f"Error listing R2 files: {e}")
        return set()
    return all_files

# --- DELETE ORPHANED FILES ---
def delete_orphaned_files(orphaned_keys):
    r2_service = R2Service()
    deleted_count = 0
    
    for key in orphaned_keys:
        try:
            print(f"Deleting: {key}")
            success = r2_service.delete_file(key)
            if success:
                deleted_count += 1
            else:
                print(f"Failed to delete: {key}")
        except Exception as e:
            print(f"Error deleting {key}: {e}")
    
    print(f"Successfully deleted {deleted_count} orphaned files from R2.")

if __name__ == "__main__":
    print("🔍 Finding orphaned files in R2...")
    
    # Get referenced keys from MongoDB
    referenced_keys = get_referenced_r2_keys()
    print(f"Found {len(referenced_keys)} referenced r2_key(s) in MongoDB.")
    
    # Get all files from R2
    all_r2_files = list_r2_files()
    print(f"Found {len(all_r2_files)} files in R2 bucket.")
    
    # Find orphaned files
    orphaned = sorted(all_r2_files - referenced_keys)
    print(f"Orphaned files (not in MongoDB): {len(orphaned)}")
    
    if orphaned:
        print("\nFirst 10 orphaned files:")
        for key in orphaned[:10]:
            print(f"  {key}")
        if len(orphaned) > 10:
            print(f"  ...and {len(orphaned)-10} more.")
        
        confirm = input(f"\nDelete {len(orphaned)} orphaned files from R2? (y/N): ")
        if confirm.lower() == 'y':
            delete_orphaned_files(orphaned)
        else:
            print("Aborted. No files deleted.")
    else:
        print("✅ No orphaned files to delete.") 
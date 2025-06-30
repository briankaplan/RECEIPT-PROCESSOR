#!/usr/bin/env python3
"""
Activate real user token and deactivate test token
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from config import Config
from pymongo import MongoClient
from datetime import datetime

def activate_real_user_token():
    """Deactivate test token and activate a real user token"""
    
    print("🔄 Activating Real User Token")
    print("=" * 40)
    
    # Connect to MongoDB
    client = MongoClient(Config.MONGODB_URI)
    db = client[Config.MONGODB_DATABASE]
    
    # First, deactivate the test token
    test_result = db.teller_tokens.update_one(
        {'user_id': 'test_user'},
        {'$set': {'status': 'inactive', 'deactivated_at': datetime.utcnow()}}
    )
    
    if test_result.modified_count > 0:
        print("✅ Deactivated test_user token")
    else:
        print("⚠️  No test_user token found to deactivate")
    
    # Find the most recent real user token
    real_tokens = list(db.teller_tokens.find({
        'user_id': {'$regex': '^usr_'},
        'status': 'inactive'
    }).sort('created_at', -1))
    
    if not real_tokens:
        print("❌ No real user tokens found")
        return
    
    # Activate the most recent real user token
    real_token = real_tokens[0]
    real_result = db.teller_tokens.update_one(
        {'_id': real_token['_id']},
        {'$set': {'status': 'active', 'activated_at': datetime.utcnow()}}
    )
    
    if real_result.modified_count > 0:
        print(f"✅ Activated real user token: {real_token['user_id']}")
        print(f"   Token ID: {real_token['_id']}")
        print(f"   Access Token: {real_token['access_token'][:20]}...")
    else:
        print("❌ Failed to activate real user token")
    
    # Verify the change
    active_tokens = list(db.teller_tokens.find({'status': 'active'}))
    print(f"\n📊 Current active tokens: {len(active_tokens)}")
    
    for token in active_tokens:
        print(f"   - User: {token['user_id']}")
        print(f"     Token: {token['access_token'][:20]}...")

if __name__ == "__main__":
    activate_real_user_token() 
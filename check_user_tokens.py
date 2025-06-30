#!/usr/bin/env python3
"""
Check user IDs in Teller tokens
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from config import Config
from pymongo import MongoClient

def check_user_tokens():
    """Check the user IDs in Teller tokens"""
    
    print("🔍 Checking User IDs in Teller Tokens")
    print("=" * 40)
    
    # Connect to MongoDB
    client = MongoClient(Config.MONGODB_URI)
    db = client[Config.MONGODB_DATABASE]
    
    # Get all tokens
    tokens = list(db.teller_tokens.find({}))
    print(f"Found {len(tokens)} total tokens in database")
    
    active_tokens = []
    for token in tokens:
        if token.get('status') == 'active':
            active_tokens.append(token)
            print(f"\n✅ Active Token:")
            print(f"  User ID: {token.get('user_id')}")
            print(f"  Token Type: {token.get('token_type')}")
            print(f"  Created At: {token.get('created_at')}")
            print(f"  Access Token (first 20 chars): {token.get('access_token', '')[:20]}...")
    
    if not active_tokens:
        print("\n❌ No active tokens found!")
        print("This means the system is using test_user instead of your real user ID.")
        print("\nTo fix this:")
        print("1. Go to the web interface")
        print("2. Click 'Connect Bank'")
        print("3. Complete the Teller Connect flow with your Chase credentials")
        print("4. This will create a new token with your real user ID")
    
    client.close()

if __name__ == "__main__":
    check_user_tokens() 
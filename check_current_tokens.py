#!/usr/bin/env python3
"""
Check current Teller tokens in database
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from config import Config
from pymongo import MongoClient

def check_current_tokens():
    """Check the current Teller tokens in the database"""
    
    print("🔍 Checking Current Teller Tokens in Database")
    print("=" * 50)
    
    # Connect to MongoDB
    client = MongoClient(Config.MONGODB_URI)
    db = client[Config.MONGODB_DATABASE]
    
    # Get all tokens
    tokens = list(db.teller_tokens.find({}))
    print(f"Found {len(tokens)} total tokens in database")
    
    for i, token in enumerate(tokens):
        print(f"\n--- Token {i+1} ---")
        print(f"ID: {token.get('_id')}")
        print(f"User ID: {token.get('user_id')}")
        print(f"Token Type: {token.get('token_type')}")
        print(f"Is Active: {token.get('is_active')}")
        print(f"Status: {token.get('status')}")
        print(f"Created At: {token.get('created_at')}")
        print(f"Access Token (first 20 chars): {token.get('access_token', '')[:20]}...")
        
        # Check if this token would be found by get_teller_tokens()
        if token.get('is_active') == True:
            print("✅ Would be found by get_teller_tokens()")
        else:
            print("❌ Would NOT be found by get_teller_tokens()")
    
    # Test the get_teller_tokens query
    print(f"\n🔍 Testing get_teller_tokens() query...")
    active_tokens = list(db.teller_tokens.find({'is_active': True}))
    print(f"Found {len(active_tokens)} active tokens with is_active=True")
    
    status_active_tokens = list(db.teller_tokens.find({'status': 'active'}))
    print(f"Found {len(status_active_tokens)} tokens with status='active'")
    
    client.close()

if __name__ == "__main__":
    check_current_tokens() 
#!/usr/bin/env python3
"""
Check Teller token in database
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from config import Config
from pymongo import MongoClient

def check_teller_token():
    """Check the current Teller token in the database"""
    
    print("🔍 Checking Teller Token in Database")
    print("=" * 40)
    
    # Connect to MongoDB
    client = MongoClient(Config.MONGODB_URI)
    db = client[Config.MONGODB_DATABASE]
    
    # Get all tokens
    tokens = list(db.teller_tokens.find({}))
    print(f"Found {len(tokens)} tokens in database")
    
    for i, token in enumerate(tokens):
        print(f"\n--- Token {i+1} ---")
        print(f"ID: {token.get('_id')}")
        print(f"User ID: {token.get('user_id')}")
        print(f"Active: {token.get('active', False)}")
        print(f"Token Type: {token.get('token_type', 'unknown')}")
        print(f"Created At: {token.get('created_at')}")
        print(f"Expires In: {token.get('expires_in')}")
        print(f"Scope: {token.get('scope')}")
        
        access_token = token.get('access_token')
        if access_token:
            print(f"Access Token: {access_token[:20]}...{access_token[-20:]}")
            print(f"Token Length: {len(access_token)}")
            
            # Check if it looks like a valid JWT token
            if access_token.count('.') == 2:
                print("✅ Token format looks like JWT (3 parts separated by dots)")
            else:
                print("❌ Token format doesn't look like JWT")
        else:
            print("❌ No access token found")
    
    # Check if we have any active tokens
    active_tokens = [t for t in tokens if t.get('active', False)]
    print(f"\nActive tokens: {len(active_tokens)}")
    
    if not active_tokens:
        print("❌ No active tokens found!")
        print("\nTo fix this:")
        print("1. Go to the web interface")
        print("2. Click 'Connect Bank'")
        print("3. Complete the Teller Connect flow")
        print("4. This will create a new active token")
    else:
        print("✅ Found active tokens")

if __name__ == "__main__":
    check_teller_token() 
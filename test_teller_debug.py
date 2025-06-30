#!/usr/bin/env python3
"""
Debug script to test Teller API calls directly
"""

import os
import sys
import requests
from datetime import datetime
from pymongo import MongoClient

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from config import Config

def test_teller_connection():
    """Test Teller API connection and get transactions"""
    
    # Connect to MongoDB
    client = MongoClient(Config.MONGODB_URI)
    db = client[Config.MONGODB_DATABASE]
    
    # Get active Teller tokens
    tokens = list(db.teller_tokens.find({'active': True}))
    print(f"Found {len(tokens)} active tokens")
    
    if not tokens:
        print("No active tokens found!")
        return
    
    for i, token in enumerate(tokens):
        print(f"\n--- Testing Token {i+1} ---")
        access_token = token.get('access_token')
        user_id = token.get('user_id', 'unknown')
        
        print(f"User ID: {user_id}")
        print(f"Token active: {token.get('active')}")
        
        # Test token validation
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(
                f"{Config.TELLER_API_URL}/accounts",
                headers=headers,
                timeout=10
            )
            print(f"Token validation status: {response.status_code}")
            
            if response.status_code == 200:
                accounts = response.json()
                print(f"Found {len(accounts)} accounts")
                
                for account in accounts:
                    account_id = account.get('id')
                    account_name = account.get('name', 'Unknown')
                    print(f"  Account: {account_name} (ID: {account_id})")
                    
                    # Test getting transactions for this account
                    params = {
                        'from': '2024-07-01',
                        'to': '2025-06-29'
                    }
                    
                    tx_response = requests.get(
                        f"{Config.TELLER_API_URL}/accounts/{account_id}/transactions",
                        headers=headers,
                        params=params,
                        timeout=30
                    )
                    
                    print(f"  Transactions API status: {tx_response.status_code}")
                    
                    if tx_response.status_code == 200:
                        transactions = tx_response.json()
                        print(f"  Found {len(transactions)} transactions")
                        
                        if transactions:
                            # Show first few transactions
                            for j, tx in enumerate(transactions[:3]):
                                print(f"    Transaction {j+1}: {tx.get('date')} - {tx.get('amount')} - {tx.get('description', 'No description')}")
                    else:
                        print(f"  Error: {tx_response.text}")
                        
            else:
                print(f"Token validation failed: {response.text}")
                
        except Exception as e:
            print(f"Error testing token: {e}")

if __name__ == "__main__":
    test_teller_connection() 
#!/usr/bin/env python3
"""
Test token validation for real Chase token
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from config import Config
from pymongo import MongoClient
from app.services.teller_service import TellerService

def test_token_validation():
    """Test token validation for the active Chase token"""
    
    print("🔍 Testing Token Validation")
    print("=" * 40)
    
    # Connect to MongoDB
    client = MongoClient(Config.MONGODB_URI)
    db = client[Config.MONGODB_DATABASE]
    
    # Get the active token
    active_token = db.teller_tokens.find_one({'status': 'active'})
    
    if not active_token:
        print("❌ No active token found")
        return
    
    print(f"✅ Found active token:")
    print(f"   User ID: {active_token.get('user_id')}")
    print(f"   Token (first 20 chars): {active_token.get('access_token', '')[:20]}...")
    print(f"   Status: {active_token.get('status')}")
    
    # Test token validation
    teller_service = TellerService()
    access_token = active_token.get('access_token')
    
    print(f"\n🔐 Testing token validation...")
    is_valid = teller_service.validate_token(access_token)
    
    if is_valid:
        print("✅ Token is valid!")
        
        # Test getting accounts
        print(f"\n🏦 Testing account retrieval...")
        accounts = teller_service.get_accounts(access_token)
        
        if accounts:
            print(f"✅ Found {len(accounts)} accounts:")
            for account in accounts:
                print(f"   - {account.get('name')} ({account.get('id')})")
                print(f"     Institution: {account.get('institution', {}).get('name', 'Unknown')}")
                print(f"     Type: {account.get('type')}")
                print(f"     Subtype: {account.get('subtype')}")
        else:
            print("❌ No accounts found")
            
        # Test getting transactions for recent period
        if accounts:
            account_id = accounts[0].get('id')
            print(f"\n💳 Testing transaction retrieval for account {account_id}...")
            
            transactions = teller_service.get_transactions(
                access_token, 
                account_id, 
                "2025-05-01", 
                "2025-06-29"
            )
            
            if transactions:
                print(f"✅ Found {len(transactions)} transactions")
                for i, tx in enumerate(transactions[:3]):  # Show first 3
                    print(f"   {i+1}. {tx.get('date')} - {tx.get('description')} - ${tx.get('amount')}")
            else:
                print("❌ No transactions found for this period")
    else:
        print("❌ Token validation failed")
        
        # Try to get more details about the failure
        print(f"\n🔍 Testing API endpoint directly...")
        try:
            import requests
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                f"{Config.TELLER_API_URL}/accounts",
                headers=headers,
                timeout=10
            )
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    test_token_validation() 
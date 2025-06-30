#!/usr/bin/env python3
"""
Test Teller certificates with API calls
"""

import os
import base64
import tempfile
import requests
from pymongo import MongoClient

# Add the app directory to the path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from config import Config

def test_certificates():
    """Test Teller certificates with API calls"""
    
    # Connect to MongoDB
    client = MongoClient(Config.MONGODB_URI)
    db = client[Config.MONGODB_DATABASE]
    
    # Get active Teller tokens
    tokens = list(db.teller_tokens.find({'active': True}))
    print(f"Found {len(tokens)} active tokens")
    
    if not tokens:
        print("No active tokens found!")
        return
    
    # Setup certificates
    cert_path = './credentials/teller_certificate.b64'
    key_path = './credentials/teller_private_key.b64'
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print("Certificate files not found!")
        return
    
    # Read and decode certificates
    with open(cert_path, 'r') as f:
        cert_b64 = f.read().strip()
    
    with open(key_path, 'r') as f:
        key_b64 = f.read().strip()
    
    # Decode base64 to PEM format
    cert_pem = base64.b64decode(cert_b64).decode('utf-8')
    key_pem = base64.b64decode(key_b64).decode('utf-8')
    
    # Create temporary files for requests
    cert_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
    key_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
    
    cert_file.write(cert_pem)
    key_file.write(key_pem)
    
    cert_file.close()
    key_file.close()
    
    # Set secure permissions
    os.chmod(cert_file.name, 0o600)
    os.chmod(key_file.name, 0o600)
    
    cert_files = (cert_file.name, key_file.name)
    print("✅ Certificates loaded successfully")
    
    # Test with first token
    token = tokens[0]
    access_token = token.get('access_token')
    user_id = token.get('user_id', 'unknown')
    
    print(f"\n--- Testing Token for {user_id} ---")
    
    # Test token validation with certificates
    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        response = requests.get(
            f"{Config.TELLER_API_URL}/accounts",
            headers=headers,
            cert=cert_files,
            timeout=10
        )
        print(f"Token validation status: {response.status_code}")
        
        if response.status_code == 200:
            accounts = response.json()
            print(f"✅ Found {len(accounts)} accounts")
            
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
                    cert=cert_files,
                    timeout=30
                )
                
                print(f"  Transactions API status: {tx_response.status_code}")
                
                if tx_response.status_code == 200:
                    transactions = tx_response.json()
                    print(f"  ✅ Found {len(transactions)} transactions")
                    
                    if transactions:
                        # Show first few transactions
                        for j, tx in enumerate(transactions[:3]):
                            print(f"    Transaction {j+1}: {tx.get('date')} - {tx.get('amount')} - {tx.get('description', 'No description')}")
                else:
                    print(f"  ❌ Error: {tx_response.text}")
                    
        else:
            print(f"❌ Token validation failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing token: {e}")
    
    # Clean up temporary files
    os.unlink(cert_file.name)
    os.unlink(key_file.name)

if __name__ == "__main__":
    test_certificates() 
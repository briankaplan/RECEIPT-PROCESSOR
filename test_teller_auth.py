#!/usr/bin/env python3
"""
Test Teller API authentication and understand the correct authentication method
"""

import os
import requests
import base64
import tempfile
import json
from datetime import datetime

# Add the app directory to the path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from config import Config

def test_teller_auth_methods():
    """Test different Teller API authentication methods"""
    
    print("🔐 Testing Teller API Authentication Methods")
    print("=" * 50)
    
    # Check configuration
    print(f"Application ID: {Config.TELLER_APPLICATION_ID}")
    print(f"API URL: {Config.TELLER_API_URL}")
    print(f"Environment: {Config.TELLER_ENVIRONMENT}")
    
    # Check certificate files
    cert_path = './credentials/teller_certificate.b64'
    key_path = './credentials/teller_private_key.b64'
    
    print(f"\nCertificate files:")
    print(f"  Certificate: {cert_path} {'✅' if os.path.exists(cert_path) else '❌'}")
    print(f"  Private Key: {key_path} {'✅' if os.path.exists(key_path) else '❌'}")
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print("\n❌ Certificate files not found!")
        return
    
    # Load certificates
    try:
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
        
    except Exception as e:
        print(f"❌ Error loading certificates: {e}")
        return
    
    # Test different authentication methods
    test_urls = [
        f"{Config.TELLER_API_URL}/health",
        f"{Config.TELLER_API_URL}/accounts"
    ]
    
    for url in test_urls:
        print(f"\n--- Testing {url} ---")
        
        # Method 1: No authentication
        print("1. No authentication:")
        try:
            response = requests.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Method 2: Bearer token (with dummy token)
        print("2. Bearer token (dummy):")
        try:
            headers = {'Authorization': 'Bearer dummy_token'}
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Method 3: Client certificates only
        print("3. Client certificates only:")
        try:
            response = requests.get(url, cert=cert_files, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Method 4: Client certificates + Bearer token
        print("4. Client certificates + Bearer token:")
        try:
            headers = {'Authorization': 'Bearer dummy_token'}
            response = requests.get(url, headers=headers, cert=cert_files, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Method 5: Application ID in headers
        print("5. Application ID in headers:")
        try:
            headers = {'Teller-Application-ID': Config.TELLER_APPLICATION_ID}
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Method 6: Application ID + Client certificates
        print("6. Application ID + Client certificates:")
        try:
            headers = {'Teller-Application-ID': Config.TELLER_APPLICATION_ID}
            response = requests.get(url, headers=headers, cert=cert_files, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
        except Exception as e:
            print(f"   Error: {e}")
    
    # Clean up temporary files
    try:
        os.unlink(cert_file.name)
        os.unlink(key_file.name)
    except:
        pass

def test_with_real_token():
    """Test with a real access token from the database"""
    print("\n🔑 Testing with Real Access Token")
    print("=" * 40)
    
    try:
        from pymongo import MongoClient
        
        # Connect to MongoDB
        client = MongoClient(Config.MONGODB_URI)
        db = client[Config.MONGODB_DATABASE]
        
        # Get active tokens
        tokens = list(db.teller_tokens.find({'active': True}))
        print(f"Found {len(tokens)} active tokens")
        
        if not tokens:
            print("No active tokens found!")
            return
        
        # Use first token
        token = tokens[0]
        access_token = token.get('access_token')
        user_id = token.get('user_id', 'unknown')
        
        print(f"Testing with token for user: {user_id}")
        
        # Load certificates
        cert_path = './credentials/teller_certificate.b64'
        key_path = './credentials/teller_private_key.b64'
        
        with open(cert_path, 'r') as f:
            cert_b64 = f.read().strip()
        
        with open(key_path, 'r') as f:
            key_b64 = f.read().strip()
        
        cert_pem = base64.b64decode(cert_b64).decode('utf-8')
        key_pem = base64.b64decode(key_b64).decode('utf-8')
        
        cert_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
        key_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
        
        cert_file.write(cert_pem)
        key_file.write(key_pem)
        
        cert_file.close()
        key_file.close()
        
        os.chmod(cert_file.name, 0o600)
        os.chmod(key_file.name, 0o600)
        
        cert_files = (cert_file.name, key_file.name)
        
        # Test accounts endpoint with real token
        print("\nTesting /accounts endpoint:")
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                f"{Config.TELLER_API_URL}/accounts",
                headers=headers,
                cert=cert_files,
                timeout=10
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            
            if response.status_code == 200:
                accounts = response.json()
                print(f"✅ Found {len(accounts)} accounts")
                
                # Test transactions for first account
                if accounts:
                    account_id = accounts[0]['id']
                    print(f"\nTesting transactions for account: {account_id}")
                    
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
                    
                    print(f"Transactions status: {tx_response.status_code}")
                    print(f"Transactions response: {tx_response.text[:500]}...")
                    
                    if tx_response.status_code == 200:
                        transactions = tx_response.json()
                        print(f"✅ Found {len(transactions)} transactions")
            
        except Exception as e:
            print(f"Error: {e}")
        
        # Clean up
        os.unlink(cert_file.name)
        os.unlink(key_file.name)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_teller_auth_methods()
    test_with_real_token() 
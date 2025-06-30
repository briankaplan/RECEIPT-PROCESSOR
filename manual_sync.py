#!/usr/bin/env python3
"""
Manual sync script to fetch Teller transactions with certificates
"""

import os
import base64
import tempfile
import requests
from datetime import datetime
from pymongo import MongoClient

# Add the app directory to the path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from config import Config

def manual_sync():
    """Manually sync transactions from July 1, 2024 to today"""
    
    print("🔄 Manual Teller Sync - July 1, 2024 to June 29, 2025")
    print("=" * 60)
    
    # Connect to MongoDB
    client = MongoClient(Config.MONGODB_URI)
    db = client[Config.MONGODB_DATABASE]
    
    # Get active Teller tokens
    tokens = list(db.teller_tokens.find({'active': True}))
    print(f"Found {len(tokens)} active tokens")
    
    if not tokens:
        print("❌ No active tokens found!")
        return
    
    # Setup certificates
    cert_path = './credentials/teller_certificate.b64'
    key_path = './credentials/teller_private_key.b64'
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print("❌ Certificate files not found!")
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
    
    total_new_transactions = 0
    total_updated_transactions = 0
    
    # Process each token
    for i, token in enumerate(tokens):
        access_token = token.get('access_token')
        user_id = token.get('user_id', 'unknown')
        
        print(f"\n--- Processing Token {i+1} for {user_id} ---")
        
        # Test token validation with certificates
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(
                f"{Config.TELLER_API_URL}/accounts",
                headers=headers,
                cert=cert_files,
                timeout=10
            )
            
            if response.status_code == 200:
                accounts = response.json()
                print(f"✅ Found {len(accounts)} accounts")
                
                for account in accounts:
                    account_id = account.get('id')
                    account_name = account.get('name', 'Unknown')
                    print(f"  📊 Processing account: {account_name}")
                    
                    # Get transactions for this account
                    params = {
                        'from': '2024-07-01',
                        'to': '2025-06-29'
                    }
                    
                    tx_response = requests.get(
                        f"{Config.TELLER_API_URL}/accounts/{account_id}/transactions",
                        headers=headers,
                        params=params,
                        cert=cert_files,
                        timeout=60
                    )
                    
                    if tx_response.status_code == 200:
                        transactions = tx_response.json()
                        print(f"  ✅ Retrieved {len(transactions)} transactions from Teller")
                        
                        # Process each transaction
                        for tx in transactions:
                            # Add metadata
                            tx['user_id'] = user_id
                            tx['token_id'] = str(token['_id'])
                            tx['account_id'] = account_id
                            tx['account_name'] = account_name
                            tx['institution_name'] = account.get('institution', {}).get('name')
                            tx['imported_at'] = datetime.now()
                            tx['source'] = 'teller'
                            
                            # Check if transaction already exists
                            existing = db.bank_transactions.find_one({
                                'transaction_id': tx.get('id'),
                                'user_id': user_id,
                                'account_id': account_id
                            })
                            
                            if existing:
                                # Update existing transaction
                                db.bank_transactions.update_one(
                                    {'_id': existing['_id']},
                                    {'$set': tx}
                                )
                                total_updated_transactions += 1
                            else:
                                # Insert new transaction
                                db.bank_transactions.insert_one(tx)
                                total_new_transactions += 1
                        
                        print(f"  📈 Processed: {len(transactions)} transactions")
                        
                    else:
                        print(f"  ❌ Error getting transactions: {tx_response.status_code} - {tx_response.text}")
                        
            else:
                print(f"❌ Token validation failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error processing token: {e}")
    
    # Clean up temporary files
    os.unlink(cert_file.name)
    os.unlink(key_file.name)
    
    # Summary
    print(f"\n🎉 Sync Complete!")
    print(f"📊 New transactions: {total_new_transactions}")
    print(f"🔄 Updated transactions: {total_updated_transactions}")
    print(f"📈 Total processed: {total_new_transactions + total_updated_transactions}")
    
    # Trigger transaction sync
    print("\n🔄 Triggering transaction sync...")
    try:
        # Import and run transaction sync
        from app.services.transaction_service import TransactionService
        from app.services.mongo_service import MongoService
        
        mongo_service = MongoService()
        transaction_service = TransactionService(mongo_service)
        
        sync_result = transaction_service.sync_from_bank_transactions()
        if sync_result.get('success'):
            print(f"✅ Transaction sync complete: {sync_result.get('synced', 0)} synced, {sync_result.get('updated', 0)} updated")
        else:
            print(f"❌ Transaction sync failed: {sync_result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error triggering transaction sync: {e}")

if __name__ == "__main__":
    manual_sync() 
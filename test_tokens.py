#!/usr/bin/env python3
"""
Test Gmail token loading and validation
"""

import pickle
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from utils import load_config
import os

def test_token(token_path, email):
    """Test loading and validating a Gmail token"""
    print(f"\n🔑 Testing token for {email}")
    print(f"📁 Token path: {token_path}")
    
    try:
        # Load token
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
            
        print("✅ Token loaded successfully")
        print(f"Token type: {type(creds)}")
        print(f"Has refresh token: {bool(creds.refresh_token)}")
        print(f"Expired: {creds.expired}")
        
        # Test Gmail API
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        
        print("\n📧 Gmail API Test:")
        print(f"Email: {profile['emailAddress']}")
        print(f"Messages: {profile['messagesTotal']}")
        print(f"Threads: {profile['threadsTotal']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    config = load_config("config/config_perfect.json")
    print("\n🔍 Testing Gmail Tokens\n" + "="*50)
    # Use new config structure
    total_accounts = len(config["gmail"])
    for email, account in config["gmail"].items():
        token_file = account["token_file"]
        print(f"Checking token for {email}: {token_file}")
        assert os.path.exists(token_file), f"Token file missing: {token_file}"
    print(f"✅ All {total_accounts} Gmail tokens found!")

if __name__ == "__main__":
    main() 
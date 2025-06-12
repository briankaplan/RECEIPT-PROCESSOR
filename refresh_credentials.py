#!/usr/bin/env python3
"""
Credential Refresh Utility - Updates pickle files with missing OAuth fields
"""

import pickle
import os
from pathlib import Path
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import json

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

def refresh_pickle_credentials():
    """Refresh credentials in pickle files if needed"""
    
    # Load clients.json for OAuth details
    clients_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
    if not clients_path or not Path(clients_path).exists():
        print(f"❌ Clients file not found: {clients_path}")
        return False
    
    with open(clients_path, 'r') as f:
        clients = json.load(f)
    
    for i in range(1, 4):
        email = os.getenv(f'GMAIL_ACCOUNT_{i}_EMAIL')
        pickle_file = os.getenv(f'GMAIL_ACCOUNT_{i}_PICKLE_FILE')
        
        if not email or not pickle_file:
            continue
            
        if not Path(pickle_file).exists():
            print(f"❌ Pickle file not found for {email}: {pickle_file}")
            continue
        
        print(f"🔧 Checking credentials for {email}...")
        
        try:
            # Load existing credentials
            with open(pickle_file, 'rb') as token:
                creds = pickle.load(token)
            
            # Check if refresh is needed
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    print(f"🔄 Refreshing expired credentials for {email}...")
                    creds.refresh(Request())
                    
                    # Save refreshed credentials
                    with open(pickle_file, 'wb') as token:
                        pickle.dump(creds, token)
                    
                    print(f"✅ Credentials refreshed for {email}")
                else:
                    print(f"⚠️  Invalid credentials for {email} - may need re-authentication")
            else:
                print(f"✅ Credentials valid for {email}")
                
        except Exception as e:
            print(f"❌ Error processing {email}: {e}")
    
    return True

if __name__ == "__main__":
    refresh_pickle_credentials()

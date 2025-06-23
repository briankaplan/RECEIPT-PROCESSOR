#!/usr/bin/env python3
"""
Gmail Token Setup for Render.com Deployment
Generates authentication tokens that work with /etc/secrets/ paths
"""

import os
import sys
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Gmail accounts configuration for Render
ACCOUNTS = [
    {
        'email': 'kaplan.brian@gmail.com',
        'credentials_file': './credentials/gmail_credentials.json',
        'token_file': './gmail_tokens/kaplan_brian_gmail.pickle',
        'render_token_file': 'kaplan_brian_gmail.pickle',
        'display_name': 'Personal Gmail'
    },
    {
        'email': 'brian@downhome.com', 
        'credentials_file': './credentials/gmail_credentials.json',
        'token_file': './gmail_tokens/brian_downhome.pickle',
        'render_token_file': 'brian_downhome.pickle',
        'display_name': 'Down Home Business'
    },
    {
        'email': 'brian@musiccityrodeo.com',
        'credentials_file': './credentials/gmail_credentials.json', 
        'token_file': './gmail_tokens/brian_musiccityrodeo.pickle',
        'render_token_file': 'brian_musiccityrodeo.pickle',
        'display_name': 'Music City Rodeo'
    }
]

def authenticate_account(account_config):
    """Authenticate a Gmail account and save tokens"""
    print(f"\n🔐 Authenticating {account_config['display_name']} ({account_config['email']})")
    
    creds = None
    token_file = account_config['token_file']
    credentials_file = account_config['credentials_file']
    
    # Check if token file exists
    if os.path.exists(token_file):
        print(f"📁 Loading existing token from {token_file}")
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            try:
                creds.refresh(Request())
                print("✅ Token refreshed successfully")
            except Exception as e:
                print(f"❌ Token refresh failed: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists(credentials_file):
                print(f"❌ Credentials file not found: {credentials_file}")
                print("Please ensure Gmail API credentials are in the credentials folder")
                return False
                
            print("🌐 Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
            print("✅ OAuth flow completed")
    
    # Save the credentials for future use
    os.makedirs(os.path.dirname(token_file), exist_ok=True)
    with open(token_file, 'wb') as token:
        pickle.dump(creds, token)
    print(f"💾 Token saved to {token_file}")
    
    # Test the connection
    try:
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile.get('emailAddress')
        
        print(f"✅ Successfully connected to {email_address}")
        print(f"📊 Total messages: {profile.get('messagesTotal', 'Unknown')}")
        
        # Verify this is the expected account
        if email_address.lower() != account_config['email'].lower():
            print(f"⚠️  WARNING: Expected {account_config['email']}, got {email_address}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to Gmail API: {e}")
        return False

def create_render_ready_tokens():
    """Create tokens ready for Render deployment"""
    print("🚀 Setting up Gmail tokens for Render.com deployment")
    print("=" * 60)
    
    # Ensure directories exist
    os.makedirs('./gmail_tokens', exist_ok=True)
    os.makedirs('./render_tokens', exist_ok=True)
    
    successful_accounts = 0
    
    for account in ACCOUNTS:
        if authenticate_account(account):
            successful_accounts += 1
            
            # Copy token for Render upload
            render_token_path = f"./render_tokens/{account['render_token_file']}"
            if os.path.exists(account['token_file']):
                import shutil
                shutil.copy2(account['token_file'], render_token_path)
                print(f"📋 Render token created: {render_token_path}")
        else:
            print(f"❌ Failed to authenticate {account['display_name']}")
    
    print("\n" + "=" * 60)
    print(f"✅ Successfully authenticated {successful_accounts}/{len(ACCOUNTS)} accounts")
    
    if successful_accounts > 0:
        print("\n📤 NEXT STEPS FOR RENDER DEPLOYMENT:")
        print("1. Upload the following files to Render's Secret Files:")
        for account in ACCOUNTS:
            render_token = f"./render_tokens/{account['render_token_file']}"
            if os.path.exists(render_token):
                print(f"   - {render_token} → {account['render_token_file']}")
        
        print("\n2. These files will be available at /etc/secrets/ in Render")
        print("3. Your environment variables are already configured correctly")
        
        return True
    else:
        print("\n❌ No accounts were successfully authenticated")
        return False

if __name__ == '__main__':
    print("Gmail Authentication Setup for Render.com")
    print("This will generate fresh OAuth tokens for deployment")
    print("\n⚠️  Make sure you have:")
    print("1. Gmail API credentials in ./credentials/gmail_credentials.json")
    print("2. Internet connection for OAuth flow")
    print("3. A web browser available")
    
    input("\nPress Enter to continue...")
    
    success = create_render_ready_tokens()
    
    if success:
        print("\n🎉 Setup complete! Upload the render_tokens/ files to Render Secret Files")
    else:
        print("\n💔 Setup failed. Check the errors above and try again")
        sys.exit(1) 
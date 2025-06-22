#!/usr/bin/env python3
"""
Gmail Token Setup for Receipt Processor
This script helps you generate OAuth2 tokens for the 3 Gmail accounts
"""

import os
import pickle
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

class GmailTokenSetup:
    def __init__(self):
        self.accounts = {
            'kaplan.brian@gmail.com': {
                'email': 'kaplan.brian@gmail.com',
                'pickle_file': 'gmail_tokens/kaplan.brian_at_gmail.com.pickle',
                'port': 8080
            },
            'brian@downhome.com': {
                'email': 'brian@downhome.com',
                'pickle_file': 'gmail_tokens/brian_at_downhome.com.pickle',
                'port': 8082
            },
            'brian@musiccityrodeo.com': {
                'email': 'brian@musiccityrodeo.com',
                'pickle_file': 'gmail_tokens/brian_at_musiccityrodeo.com.pickle',
                'port': 8081
            }
        }
        
        # Create tokens directory if it doesn't exist
        Path('gmail_tokens').mkdir(exist_ok=True)
    
    def create_credentials_template(self):
        """Create a template credentials.json file"""
        template = {
            "installed": {
                "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
                "project_id": "YOUR_PROJECT_ID",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_CLIENT_SECRET",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
            }
        }
        
        with open('gmail_tokens/credentials_template.json', 'w') as f:
            json.dump(template, f, indent=2)
        
        print("✅ Created credentials_template.json")
        print("📝 Please update with your actual Google Cloud Console credentials")
        print("   1. Go to https://console.cloud.google.com/")
        print("   2. Create a new project or select existing")
        print("   3. Enable Gmail API")
        print("   4. Create OAuth2 credentials")
        print("   5. Download and replace credentials_template.json")
    
    def generate_token_for_account(self, email, credentials_file='gmail_tokens/credentials.json'):
        """Generate OAuth token for a specific account"""
        if not os.path.exists(credentials_file):
            print(f"❌ Credentials file not found: {credentials_file}")
            print("📝 Please create credentials.json from Google Cloud Console")
            print("   Run setup with option 2 to create template")
            return False
        
        account = self.accounts[email]
        pickle_file = account['pickle_file']
        port = account['port']
        
        creds = None
        
        # Load existing token if available
        if os.path.exists(pickle_file):
            with open(pickle_file, 'rb') as token:
                creds = pickle.load(token)
                print(f"📁 Loaded existing token for {email}")
        
        # Refresh or create new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print(f"🔄 Refreshing token for {email}")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"❌ Failed to refresh token: {e}")
                    print("🌐 Creating new token instead...")
                    creds = None
            
            if not creds:
                print(f"🌐 Creating new token for {email}")
                print(f"🚀 Browser will open on port {port}")
                print(f"⚠️  Please log in with {email} when prompted")
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, SCOPES)
                    creds = flow.run_local_server(port=port)
                except Exception as e:
                    print(f"❌ Authentication failed: {e}")
                    return False
            
            # Save the token
            with open(pickle_file, 'wb') as token:
                pickle.dump(creds, token)
            print(f"💾 Saved token for {email}")
        
        # Test the token
        try:
            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            actual_email = profile['emailAddress']
            
            if actual_email.lower() == email.lower():
                print(f"✅ Token verified for {email}")
                return True
            else:
                print(f"⚠️  Warning: Token is for {actual_email}, expected {email}")
                print("   The token works but may be for wrong account")
                return True
                
        except Exception as e:
            print(f"❌ Token verification failed for {email}: {e}")
            return False
    
    def generate_all_tokens(self):
        """Generate tokens for all accounts"""
        print("🚀 Starting token generation for all accounts...")
        print("⚠️  You'll need to authenticate each account separately")
        print()
        
        credentials_file = 'gmail_tokens/credentials.json'
        if not os.path.exists(credentials_file):
            print(f"❌ Main credentials file not found: {credentials_file}")
            self.create_credentials_template()
            return
        
        success_count = 0
        for email in self.accounts.keys():
            print(f"\n📧 Processing {email}...")
            print("-" * 50)
            success = self.generate_token_for_account(email, credentials_file)
            if success:
                success_count += 1
            else:
                print(f"❌ Failed to generate token for {email}")
            print()
        
        print(f"✅ Successfully set up {success_count}/{len(self.accounts)} accounts")
    
    def check_all_tokens(self):
        """Check status of all tokens"""
        print("🔍 Checking status of all tokens...\n")
        
        for email, account in self.accounts.items():
            pickle_file = account['pickle_file']
            
            print(f"📧 {email}:")
            
            if os.path.exists(pickle_file):
                try:
                    with open(pickle_file, 'rb') as token:
                        creds = pickle.load(token)
                    
                    if creds.valid:
                        print("   ✅ Valid token")
                        
                        # Test with Gmail API
                        try:
                            service = build('gmail', 'v1', credentials=creds)
                            profile = service.users().getProfile(userId='me').execute()
                            print(f"   📬 Connected to: {profile['emailAddress']}")
                        except Exception as e:
                            print(f"   ⚠️  Token exists but API test failed: {e}")
                            
                    elif creds.expired:
                        if creds.refresh_token:
                            print("   🔄 Expired but can refresh")
                        else:
                            print("   ❌ Expired, needs re-authentication")
                    else:
                        print("   ❓ Invalid token")
                        
                except Exception as e:
                    print(f"   ❌ Error reading token - {e}")
            else:
                print("   ❌ No token file found")
            
            print()

def main():
    setup = GmailTokenSetup()
    
    print("Gmail Token Setup for Receipt Processor")
    print("=" * 50)
    print()
    print("This tool will help you set up OAuth2 tokens for:")
    for email in setup.accounts.keys():
        print(f"  • {email}")
    print()
    print("1. Check all tokens")
    print("2. Create credentials template")
    print("3. Generate tokens for all accounts")
    print("4. Generate token for specific account")
    print("5. Environment variables guide")
    print()
    
    choice = input("Choose an option (1-5): ").strip()
    
    if choice == '1':
        setup.check_all_tokens()
    
    elif choice == '2':
        setup.create_credentials_template()
    
    elif choice == '3':
        setup.generate_all_tokens()
    
    elif choice == '4':
        print("\nAvailable accounts:")
        emails = list(setup.accounts.keys())
        for i, email in enumerate(emails, 1):
            print(f"{i}. {email}")
        
        try:
            account_choice = int(input("\nChoose account number: ")) - 1
            if 0 <= account_choice < len(emails):
                email = emails[account_choice]
                setup.generate_token_for_account(email)
            else:
                print("❌ Invalid choice")
        except ValueError:
            print("❌ Invalid choice")
    
    elif choice == '5':
        print("\nEnvironment Variables Setup Guide")
        print("=" * 40)
        print()
        print("For full functionality, set these environment variables:")
        print()
        print("📧 Gmail (handled by this script):")
        print("   • Token files will be created in gmail_tokens/")
        print()
        print("🗄️  MongoDB:")
        print("   • MONGODB_URI=mongodb://username:password@host:port/database")
        print("   • MONGODB_DATABASE=gmail_receipt_processor")
        print()
        print("☁️  Cloudflare R2:")
        print("   • R2_ACCOUNT_ID=your_account_id")
        print("   • R2_ACCESS_KEY_ID=your_access_key")
        print("   • R2_SECRET_ACCESS_KEY=your_secret_key")
        print("   • R2_BUCKET_NAME=gmail-receipts")
        print()
        print("📊 Google Sheets:")
        print("   • GOOGLE_SHEETS_CREDENTIALS='{\"type\":\"service_account\",...}'")
        print()
        print("💡 In Replit, add these in the Secrets tab")
    
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Gmail Token Setup for Receipt Processor
Generates OAuth2 tokens for multiple Gmail accounts.
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
                'pickle_file': 'gmail_tokens/kaplan_brian_gmail.pickle',
                'credentials_file': 'gmail_tokens/credentials_kaplan.json',
                'port': 8080
            },
            'brian@downhome.com': {
                'email': 'brian@downhome.com',
                'pickle_file': 'gmail_tokens/brian_downhome.pickle',
                'credentials_file': 'gmail_tokens/credentials_downhome.json',
                'port': 8082
            },
            'brian@musiccityrodeo.com': {
                'email': 'brian@musiccityrodeo.com',
                'pickle_file': 'gmail_tokens/brian_musiccityrodeo.pickle',
                'credentials_file': 'gmail_tokens/credentials_mcr.json',
                'port': 8081
            }
        }

        Path('gmail_tokens').mkdir(exist_ok=True)

    def create_credentials_template(self):
        template = {
            "installed": {
                "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
                "project_id": "YOUR_PROJECT_ID",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_CLIENT_SECRET",
                "redirect_uris": [
                    "urn:ietf:wg:oauth:2.0:oob", 
                    "http://localhost"
                ]
            }
        }

        with open('gmail_tokens/credentials_template.json', 'w') as f:
            json.dump(template, f, indent=2)

        print("✅ Template created at gmail_tokens/credentials_template.json")
        print("⚠️  Replace this with your actual Google Cloud credentials.")

    def generate_token_for_account(self, email, credentials_file=None):
        account = self.accounts[email]
        
        # Use account-specific credentials file
        if credentials_file is None:
            credentials_file = account['credentials_file']
            
        if not os.path.exists(credentials_file):
            print(f"❌ Missing credentials file: {credentials_file}")
            return False

        pickle_file = account['pickle_file']
        port = account['port']
        creds = None

        if os.path.exists(pickle_file):
            with open(pickle_file, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"❌ Token refresh failed: {e}")
                    creds = None

            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                    # Force offline access to get refresh token
                    flow.redirect_uri = f'http://localhost:{port}'
                    creds = flow.run_local_server(port=port, access_type='offline', prompt='consent')
                except Exception as e:
                    print(f"❌ OAuth flow failed: {e}")
                    return False

            with open(pickle_file, 'wb') as token:
                pickle.dump(creds, token)
            print(f"💾 Token saved for {email}")

        # Verify the token
        try:
            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            actual_email = profile['emailAddress']
            if actual_email.lower() == email.lower():
                print(f"✅ Verified token for {email}")
                return True
            else:
                print(f"⚠️ Token is for {actual_email}, expected {email}")
                return True
        except Exception as e:
            print(f"❌ Gmail API test failed: {e}")
            return False

    def generate_all_tokens(self):
        print("🚀 Generating tokens for all accounts...")
        success = 0
        for email in self.accounts.keys():
            print(f"\n📧 Processing {email}")
            print("-" * 40)
            if self.generate_token_for_account(email):
                success += 1
        print(f"\n✅ Done. {success}/{len(self.accounts)} tokens created successfully.")

    def check_all_tokens(self):
        print("🔍 Checking all Gmail tokens...\n")
        for email, account in self.accounts.items():
            pickle_file = account['pickle_file']
            print(f"📧 {email}:")
            if os.path.exists(pickle_file):
                try:
                    with open(pickle_file, 'rb') as token:
                        creds = pickle.load(token)
                    if creds.valid:
                        service = build('gmail', 'v1', credentials=creds)
                        profile = service.users().getProfile(userId='me').execute()
                        print(f"   ✅ Token is valid. Linked to: {profile['emailAddress']}")
                    elif creds.expired:
                        print("   🔄 Expired, but refreshable.")
                    else:
                        print("   ❌ Token is invalid.")
                except Exception as e:
                    print(f"   ❌ Failed to read or test token: {e}")
            else:
                print("   ❌ No token found.")
            print()

def main():
    setup = GmailTokenSetup()
    print("\nGmail Token Setup")
    print("=" * 30)
    print("1. Check all tokens")
    print("2. Create credentials template")
    print("3. Generate all tokens")
    print("4. Generate one token\n")

    choice = input("Choose an option (1–4): ").strip()
    if choice == '1':
        setup.check_all_tokens()
    elif choice == '2':
        setup.create_credentials_template()
    elif choice == '3':
        setup.generate_all_tokens()
    elif choice == '4':
        emails = list(setup.accounts.keys())
        for idx, email in enumerate(emails, 1):
            print(f"{idx}. {email}")
        try:
            i = int(input("Pick account number: ").strip()) - 1
            if 0 <= i < len(emails):
                setup.generate_token_for_account(emails[i])
        except:
            print("❌ Invalid selection.")
    else:
        print("❌ Invalid choice.")

if __name__ == "__main__":
    main()
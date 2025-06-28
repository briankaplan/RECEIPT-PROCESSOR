#!/usr/bin/env python3
"""
Calendar Scope Setup for Receipt Processor
Adds calendar scopes to existing OAuth tokens for brian@downhome.com
"""

import os
import pickle
import json
import base64
import logging
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Combined scopes for Gmail + Calendar
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events.readonly'
]

logger = logging.getLogger(__name__)

class CalendarScopeSetup:
    def __init__(self):
        self.account_email = 'brian@downhome.com'
        self.token_paths = [
            'gmail_tokens/brian_downhome.pickle',  # Local development
            '/etc/secrets/brian_downhome.b64',     # Render deployment
        ]
        self.credentials_files = [
            'gmail_tokens/credentials_downhome.json',
            'credentials/gmail_credentials.json',
            'credentials/oauth_credentials.json'
        ]
        
        Path('gmail_tokens').mkdir(exist_ok=True)

    def find_existing_token(self):
        """Find existing OAuth token for brian@downhome.com"""
        for token_path in self.token_paths:
            if token_path and os.path.exists(token_path):
                logger.info(f"📁 Found existing token: {token_path}")
                return token_path
        return None

    def find_credentials_file(self):
        """Find OAuth credentials file"""
        for creds_file in self.credentials_files:
            if os.path.exists(creds_file):
                logger.info(f"📁 Found credentials file: {creds_file}")
                return creds_file
        return None

    def load_existing_token(self, token_path):
        """Load existing OAuth token"""
        try:
            if token_path.endswith('.b64'):
                # Handle base64-encoded pickle files (Render deployment)
                with open(token_path, 'r') as f:
                    base64_data = f.read().strip()
                    decoded_data = base64.b64decode(base64_data)
                    creds = pickle.loads(decoded_data)
                logger.info(f"✅ Loaded base64-encoded token from {token_path}")
            else:
                # Handle regular pickle files (local development)
                with open(token_path, 'rb') as f:
                    creds = pickle.load(f)
                logger.info(f"✅ Loaded regular pickle token from {token_path}")
            
            return creds
        except Exception as e:
            logger.error(f"❌ Failed to load token from {token_path}: {e}")
            return None

    def check_current_scopes(self, creds):
        """Check what scopes the current token has"""
        if not creds:
            return []
        
        current_scopes = getattr(creds, 'scopes', [])
        logger.info(f"📋 Current scopes: {current_scopes}")
        
        # Check if calendar scopes are already included
        calendar_scopes = [
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events.readonly'
        ]
        
        missing_calendar_scopes = [scope for scope in calendar_scopes if scope not in current_scopes]
        
        if missing_calendar_scopes:
            logger.info(f"⚠️ Missing calendar scopes: {missing_calendar_scopes}")
            return missing_calendar_scopes
        else:
            logger.info("✅ Calendar scopes already present!")
            return []

    def refresh_token_with_new_scopes(self, creds, credentials_file):
        """Refresh token to include new calendar scopes"""
        try:
            logger.info("🔄 Refreshing token with calendar scopes...")
            
            # Create new flow with expanded scopes
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            
            # Force re-authentication to get new scopes
            flow.redirect_uri = 'http://localhost:8082'
            new_creds = flow.run_local_server(port=8082, access_type='offline', prompt='consent')
            
            logger.info("✅ Successfully refreshed token with calendar scopes")
            return new_creds
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh token with new scopes: {e}")
            return None

    def save_token(self, creds, original_path):
        """Save the updated token"""
        try:
            if original_path.endswith('.b64'):
                # Save as base64 for Render deployment
                pickle_data = pickle.dumps(creds)
                base64_data = base64.b64encode(pickle_data).decode('utf-8')
                
                with open(original_path, 'w') as f:
                    f.write(base64_data)
                logger.info(f"💾 Saved base64-encoded token to {original_path}")
            else:
                # Save as regular pickle for local development
                with open(original_path, 'wb') as f:
                    pickle.dump(creds, f)
                logger.info(f"💾 Saved regular pickle token to {original_path}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save token: {e}")
            return False

    def test_calendar_access(self, creds):
        """Test if the token can access calendar"""
        try:
            logger.info("🧪 Testing calendar access...")
            
            # Test Gmail access
            gmail_service = build('gmail', 'v1', credentials=creds)
            profile = gmail_service.users().getProfile(userId='me').execute()
            logger.info(f"✅ Gmail access working for: {profile['emailAddress']}")
            
            # Test Calendar access
            calendar_service = build('calendar', 'v3', credentials=creds)
            calendar_list = calendar_service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            
            logger.info(f"✅ Calendar access working! Found {len(calendars)} calendars:")
            for calendar in calendars:
                logger.info(f"   📅 {calendar.get('summary', 'Unknown')} ({calendar.get('id', 'No ID')})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Calendar access test failed: {e}")
            return False

    def setup_calendar_scopes(self):
        """Main method to add calendar scopes to existing token"""
        logger.info("🚀 Setting up calendar scopes for brian@downhome.com")
        logger.info("=" * 60)
        
        # Step 1: Find existing token
        token_path = self.find_existing_token()
        if not token_path:
            logger.error("❌ No existing token found for brian@downhome.com")
            logger.info("💡 Please run setup_gmail_tokens.py first to create initial token")
            return False
        
        # Step 2: Find credentials file
        credentials_file = self.find_credentials_file()
        if not credentials_file:
            logger.error("❌ No OAuth credentials file found")
            logger.info("💡 Please ensure you have OAuth credentials in the credentials folder")
            return False
        
        # Step 3: Load existing token
        creds = self.load_existing_token(token_path)
        if not creds:
            logger.error("❌ Failed to load existing token")
            return False
        
        # Step 4: Check current scopes
        missing_scopes = self.check_current_scopes(creds)
        if not missing_scopes:
            logger.info("🎉 Calendar scopes already present! Testing access...")
            return self.test_calendar_access(creds)
        
        # Step 5: Refresh token with new scopes
        logger.info("🔄 Calendar scopes missing. Starting OAuth flow to add them...")
        logger.info("📱 A browser window will open for authentication")
        logger.info("🔐 Please authenticate as brian@downhome.com")
        
        new_creds = self.refresh_token_with_new_scopes(creds, credentials_file)
        if not new_creds:
            logger.error("❌ Failed to refresh token with calendar scopes")
            return False
        
        # Step 6: Save updated token
        if not self.save_token(new_creds, token_path):
            logger.error("❌ Failed to save updated token")
            return False
        
        # Step 7: Test calendar access
        if self.test_calendar_access(new_creds):
            logger.info("🎉 SUCCESS! Calendar scopes added and working!")
            return True
        else:
            logger.error("❌ Calendar access test failed after adding scopes")
            return False

def main():
    """Main function"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    setup = CalendarScopeSetup()
    
    print("\n📅 Calendar Scope Setup for brian@downhome.com")
    print("=" * 50)
    print("This will add calendar access to your existing OAuth token.")
    print("A browser window will open for authentication if needed.\n")
    
    confirm = input("Continue? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Setup cancelled")
        return
    
    success = setup.setup_calendar_scopes()
    
    if success:
        print("\n🎉 SUCCESS!")
        print("✅ Calendar scopes added to OAuth token")
        print("✅ Calendar access is now working")
        print("🔄 Restart your application to use calendar features")
    else:
        print("\n❌ FAILED!")
        print("💡 Check the logs above for details")
        print("🔧 You may need to manually authenticate or check credentials")

if __name__ == "__main__":
    main() 
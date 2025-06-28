#!/usr/bin/env python3
"""
Quick Calendar Scope Addition
Automatically adds calendar scopes to existing OAuth tokens
"""

import os
import pickle
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Combined scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events.readonly'
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_calendar_scopes():
    """Add calendar scopes to existing OAuth token"""
    
    # Paths to check
    token_path = 'gmail_tokens/brian_downhome.pickle'
    credentials_file = 'credentials/gmail_credentials.json'
    
    if not os.path.exists(token_path):
        logger.error(f"❌ Token not found: {token_path}")
        return False
    
    if not os.path.exists(credentials_file):
        logger.error(f"❌ Credentials not found: {credentials_file}")
        return False
    
    try:
        # Load existing token
        logger.info(f"📁 Loading existing token from {token_path}")
        with open(token_path, 'rb') as f:
            creds = pickle.load(f)
        
        # Check current scopes
        current_scopes = getattr(creds, 'scopes', [])
        logger.info(f"📋 Current scopes: {current_scopes}")
        
        # Check if calendar scopes are missing
        calendar_scopes = [
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events.readonly'
        ]
        
        missing_scopes = [scope for scope in calendar_scopes if scope not in current_scopes]
        
        if not missing_scopes:
            logger.info("✅ Calendar scopes already present!")
            return True
        
        logger.info(f"⚠️ Missing calendar scopes: {missing_scopes}")
        logger.info("🔄 Starting OAuth flow to add calendar scopes...")
        
        # Create new flow with expanded scopes
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
        flow.redirect_uri = 'http://localhost:8082'
        
        # Force re-authentication
        new_creds = flow.run_local_server(port=8082, access_type='offline', prompt='consent')
        
        # Save updated token
        with open(token_path, 'wb') as f:
            pickle.dump(new_creds, f)
        
        logger.info("💾 Updated token saved with calendar scopes")
        
        # Test calendar access
        logger.info("🧪 Testing calendar access...")
        calendar_service = build('calendar', 'v3', credentials=new_creds)
        calendar_list = calendar_service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        logger.info(f"✅ Calendar access working! Found {len(calendars)} calendars:")
        for calendar in calendars:
            logger.info(f"   📅 {calendar.get('summary', 'Unknown')} ({calendar.get('id', 'No ID')})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to add calendar scopes: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Adding calendar scopes to OAuth token...")
    success = add_calendar_scopes()
    
    if success:
        print("🎉 SUCCESS! Calendar scopes added.")
        print("🔄 Restart your application to use calendar features.")
    else:
        print("❌ FAILED! Check the logs above for details.") 
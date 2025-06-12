#!/usr/bin/env python3
"""
Manual Email Search - Search for specific terms in your Gmail
"""

import argparse
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from utils import load_config
import pickle

def search_emails(search_term, days=30, account_filter=None):
    """Search for specific terms across accounts"""
    
    config = load_config("config/config_perfect.json")
    
    print(f"🔍 Searching for: '{search_term}'")
    print(f"📅 Time range: {days} days")
    print("=" * 50)
    
    total_found = 0
    
    for account in config["gmail_accounts"]:
        email = account["email"]
        
        # Skip if account filter specified
        if account_filter and account_filter not in email:
            continue
            
        token_path = account["pickle_file"]
        
        try:
            # Load credentials directly
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            
            # Build service
            service = build('gmail', 'v1', credentials=creds)
            
            # Build query
            since = (datetime.utcnow() - timedelta(days=days)).strftime('%Y/%m/%d')
            query = f"after:{since} {search_term}"
            
            print(f"\n📧 {email}")
            print(f"🔎 Query: {query}")
            
            # Search
            response = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10
            ).execute()
            
            messages = response.get('messages', [])
            count = len(messages)
            total_found += count
            
            print(f"📊 Found: {count} messages")
            
            # Show first few results
            for i, msg in enumerate(messages[:3]):
                try:
                    full_msg = service.users().messages().get(
                        userId='me', 
                        id=msg['id'],
                        format='metadata'
                    ).execute()
                    
                    headers = full_msg.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
                    from_addr = next((h['value'] for h in headers if h['name'] == 'From'), 'No sender')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No date')
                    
                    print(f"\n  {i+1}. 📩 {subject}")
                    print(f"     👤 {from_addr}")
                    print(f"     📅 {date}")
                    
                except Exception as e:
                    print(f"  {i+1}. ❌ Error getting message: {e}")
                    
        except Exception as e:
            print(f"❌ {email}: Search failed - {e}")
    
    print(f"\n🎯 Total found: {total_found} messages")
    return total_found

def main():
    parser = argparse.ArgumentParser(description="Search your Gmail accounts")
    parser.add_argument("search_term", help="What to search for")
    parser.add_argument("--days", type=int, default=30, help="Days back to search")
    parser.add_argument("--account", type=str, help="Filter to specific account (partial email)")
    
    args = parser.parse_args()
    
    search_emails(args.search_term, args.days, args.account)

if __name__ == "__main__":
    print("📧 MANUAL EMAIL SEARCH")
    print("\nExamples:")
    print("  python search_my_emails.py 'google'")
    print("  python search_my_emails.py 'receipt OR invoice'") 
    print("  python search_my_emails.py 'claude' --days 90")
    print("  python search_my_emails.py 'hotel' --account brian@downhome")
    print("  python search_my_emails.py 'has:attachment'")
    print("  python search_my_emails.py 'subject:confirmation'")
    print("\n" + "="*50)
    
    main() 
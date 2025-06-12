#!/usr/bin/env python3
"""
Debug Search - Test different query formats
"""

from gmail_utils import GmailManager
from gmail_auth.auth_flow import load_gmail_credentials
from utils import load_config
from datetime import datetime, timedelta

def test_search_formats():
    """Test different search query formats"""
    
    config = load_config("config/config_perfect.json")
    
    # Test with first account only
    account = config["gmail_accounts"][0]
    email = account["email"]
    token_path = account["pickle_file"]
    
    print(f"🔍 Testing search formats for: {email}")
    print("=" * 50)
    
    try:
        creds = load_gmail_credentials(email, token_path, config["google_credentials_path"])
        gm = GmailManager(email, creds)
        
        # Calculate date
        since_date = (datetime.utcnow() - timedelta(days=90)).isoformat("T") + "Z"
        
        # Test different query formats
        test_queries = [
            # Format 1: What we know works
            "receipt OR invoice",
            
            # Format 2: With date filter (what's failing)
            f"after:{since_date} receipt OR invoice",
            
            # Format 3: Alternative date format
            f"after:2025/03/13 receipt OR invoice",
            
            # Format 4: Just one term
            "invoice",
            
            # Format 5: Date + single term
            f"after:{since_date} invoice",
            f"after:2025/03/13 invoice",
            
            # Format 6: No date, specific terms
            "mobile order",
            "paypal",
            "google",
            
            # Format 7: Date + specific terms
            f"after:2025/03/13 mobile order",
            f"after:2025/03/13 paypal",
            f"after:2025/03/13 google",
        ]
        
        for query in test_queries:
            try:
                print(f"\n🔎 Testing: '{query}'")
                
                response = gm.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=5
                ).execute()
                
                messages = response.get('messages', [])
                count = len(messages)
                estimated = response.get('resultSizeEstimate', 0)
                
                print(f"  📊 Found: {count} messages (estimated: {estimated})")
                
                if count > 0:
                    # Get first message details
                    first_msg = messages[0]
                    full_msg = gm.service.users().messages().get(
                        userId='me', 
                        id=first_msg['id'],
                        format='metadata'
                    ).execute()
                    
                    headers = full_msg.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No date')
                    
                    print(f"  📩 Example: {subject[:50]}...")
                    print(f"  📅 Date: {date}")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        # Test the exact query that worked before
        print(f"\n🎯 Testing exact working query:")
        working_query = "after:2025/03/13 receipt OR invoice"
        
        try:
            response = gm.service.users().messages().list(
                userId='me',
                q=working_query,
                maxResults=10
            ).execute()
            
            messages = response.get('messages', [])
            print(f"📊 Working query found: {len(messages)} messages")
            
            for i, msg in enumerate(messages[:3]):
                full_msg = gm.service.users().messages().get(
                    userId='me', 
                    id=msg['id'],
                    format='metadata'
                ).execute()
                
                headers = full_msg.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
                from_addr = next((h['value'] for h in headers if h['name'] == 'From'), 'No sender')
                
                print(f"  {i+1}. {subject}")
                print(f"     From: {from_addr}")
                
        except Exception as e:
            print(f"❌ Working query failed: {e}")
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")

if __name__ == "__main__":
    test_search_formats() 
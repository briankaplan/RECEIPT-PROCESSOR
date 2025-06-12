#!/usr/bin/env python3
"""
Enhanced Gmail Search Module
Provides robust Gmail search functionality for finding receipts
"""

import logging
from datetime import datetime, timedelta
import asyncio

async def enhanced_gmail_receipt_search(gmail_manager, days_back=60):
    """
    Enhanced Gmail search that actually finds receipts
    """
    
    logging.info(f"🔍 Enhanced Gmail search - looking back {days_back} days")
    
    all_messages = []
    
    # Calculate date range - Gmail uses YYYY/MM/DD format
    start_date = datetime.now() - timedelta(days=days_back)
    date_str = start_date.strftime('%Y/%m/%d')
    
    # Strategy 1: Cast a wide net first
    broad_queries = [
        f"after:{date_str}",  # All emails in timeframe
        f"after:{date_str} has:attachment",  # Emails with attachments
        f"after:{date_str} (amazon OR google OR apple OR microsoft)",  # Known merchants
        f"after:{date_str} (\$ OR dollar OR payment OR charged)",  # Money-related
    ]
    
    logging.info("📧 Step 1: Broad search to test Gmail access...")
    
    total_found = 0
    for query in broad_queries:
        try:
            response = gmail_manager.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=50
            ).execute()
            
            messages = response.get('messages', [])
            count = len(messages)
            total_found += count
            
            logging.info(f"   Query: '{query}' → {count} results")
            
            # Get a few sample subjects to verify
            if messages and count > 0:
                for i, msg in enumerate(messages[:3]):
                    try:
                        full_msg = gmail_manager.get_message(msg['id'])
                        if full_msg:
                            subject = full_msg.get('subject', 'No subject')[:50]
                            logging.info(f"   Sample {i+1}: {subject}...")
                    except:
                        pass
            
            # Add messages to collection
            for message in messages:
                try:
                    full_message = gmail_manager.get_message(message['id'])
                    if full_message:
                        full_message['search_strategy'] = 'broad'
                        full_message['search_query'] = query
                        all_messages.append(full_message)
                except Exception as e:
                    logging.warning(f"Error getting message {message['id']}: {e}")
            
        except Exception as e:
            logging.error(f"Search failed for '{query}': {e}")
            continue
    
    logging.info(f"📊 Broad search results: {total_found} total emails found")
    
    if total_found == 0:
        logging.warning("❌ No emails found in broad search - possible Gmail API issue")
        return []
    
    # Strategy 2: Receipt-specific searches (only if broad search worked)
    logging.info("📧 Step 2: Receipt-specific searches...")
    
    receipt_queries = [
        f"after:{date_str} receipt",
        f"after:{date_str} invoice", 
        f"after:{date_str} order",
        f"after:{date_str} purchase",
        f"after:{date_str} payment",
        f"after:{date_str} confirmation",
        f"after:{date_str} billing",
        f"after:{date_str} transaction",
        f"after:{date_str} \"thank you for your order\"",
        f"after:{date_str} \"order confirmation\"",
        f"after:{date_str} subject:receipt",
        f"after:{date_str} subject:invoice",
        f"after:{date_str} subject:order"
    ]
    
    receipt_count = 0
    for query in receipt_queries:
        try:
            response = gmail_manager.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=30
            ).execute()
            
            messages = response.get('messages', [])
            count = len(messages)
            receipt_count += count
            
            if count > 0:
                logging.info(f"   Receipt query: '{query}' → {count} results")
                
                for message in messages:
                    try:
                        full_message = gmail_manager.get_message(message['id'])
                        if full_message:
                            full_message['search_strategy'] = 'receipt'
                            full_message['search_query'] = query
                            all_messages.append(full_message)
                    except Exception as e:
                        logging.warning(f"Error getting message {message['id']}: {e}")
            
        except Exception as e:
            logging.error(f"Receipt search failed for '{query}': {e}")
            continue
    
    logging.info(f"📊 Receipt search results: {receipt_count} receipt-like emails found")
    
    # Strategy 3: Merchant-specific searches
    logging.info("📧 Step 3: Merchant-specific searches...")
    
    merchants = [
        "amazon", "google", "apple", "microsoft", "anthropic", "claude",
        "midjourney", "expensify", "starbucks", "uber", "lyft", "paypal",
        "stripe", "best buy", "target", "walmart", "costco"
    ]
    
    merchant_count = 0
    for merchant in merchants:
        try:
            query = f"after:{date_str} from:{merchant}"
            
            response = gmail_manager.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10
            ).execute()
            
            messages = response.get('messages', [])
            count = len(messages)
            merchant_count += count
            
            if count > 0:
                logging.info(f"   Merchant: {merchant} → {count} results")
                
                for message in messages:
                    try:
                        full_message = gmail_manager.get_message(message['id'])
                        if full_message:
                            full_message['search_strategy'] = 'merchant'
                            full_message['merchant_search'] = merchant
                            all_messages.append(full_message)
                    except Exception as e:
                        logging.warning(f"Error getting message {message['id']}: {e}")
            
        except Exception as e:
            logging.error(f"Merchant search failed for '{merchant}': {e}")
            continue
    
    logging.info(f"📊 Merchant search results: {merchant_count} merchant emails found")
    
    # Remove duplicates
    unique_messages = {}
    for msg in all_messages:
        msg_id = msg.get('id')
        if msg_id not in unique_messages:
            unique_messages[msg_id] = msg
    
    final_messages = list(unique_messages.values())
    
    logging.info(f"🎯 Final results:")
    logging.info(f"   Total unique emails: {len(final_messages)}")
    logging.info(f"   Potential receipts: {len([m for m in final_messages if m.get('search_strategy') == 'receipt'])}")
    
    return final_messages

def debug_gmail_search(gmail_manager, email_address):
    """
    Debug function to understand why Gmail search returns 0 results
    """
    
    logging.info(f"🔍 Debugging Gmail search for {email_address}")
    
    try:
        # Test 1: Can we access ANY emails?
        response = gmail_manager.service.users().messages().list(
            userId='me',
            maxResults=5
        ).execute()
        
        total_messages = response.get('messages', [])
        logging.info(f"   📧 Total accessible messages: {len(total_messages)}")
        
        if not total_messages:
            logging.error("   ❌ Cannot access any emails - check Gmail API permissions")
            return False
        
        # Test 2: How many emails in the last year?
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y/%m/%d')
        response = gmail_manager.service.users().messages().list(
            userId='me',
            q=f"after:{one_year_ago}",
            maxResults=10
        ).execute()
        
        recent_messages = response.get('messages', [])
        logging.info(f"   📧 Messages in last year: {len(recent_messages)}")
        
        # Test 3: Sample some recent emails
        if recent_messages:
            logging.info("   📧 Sample recent emails:")
            for i, msg in enumerate(recent_messages[:3]):
                try:
                    full_msg = gmail_manager.get_message(msg['id'])
                    if full_msg:
                        subject = full_msg.get('subject', 'No subject')
                        sender = full_msg.get('sender', 'No sender')
                        logging.info(f"   {i+1}. {subject[:50]} (from: {sender[:30]})")
                except:
                    pass
        
        # Test 4: Search for common terms
        test_terms = ['amazon', 'google', 'payment', 'order', '$']
        for term in test_terms:
            try:
                response = gmail_manager.service.users().messages().list(
                    userId='me',
                    q=term,
                    maxResults=5
                ).execute()
                
                term_messages = response.get('messages', [])
                logging.info(f"   🔍 '{term}': {len(term_messages)} results")
                
            except Exception as e:
                logging.error(f"   ❌ Search for '{term}' failed: {e}")
        
        return True
        
    except Exception as e:
        logging.error(f"   ❌ Debug failed: {e}")
        return False

if __name__ == "__main__":
    # Test the search functionality
    from gmail_utils import GmailManager
    from gmail_auth.auth_flow import load_gmail_credentials
    from utils import load_config
    
    config = load_config("config/config_perfect.json")
    email = config["gmail_accounts"][0]["email"]
    token_path = config["gmail_accounts"][0]["pickle_file"]
    
    creds = load_gmail_credentials(email, token_path, config["google_credentials_path"])
    if not creds:
        print(f"❌ No credentials for {email}")
        exit(1)
    
    gm = GmailManager(email, creds)
    
    # First debug the Gmail access
    if not debug_gmail_search(gm, email):
        print("❌ Gmail access issues detected")
        exit(1)
    
    # Then try the enhanced search
    import asyncio
    messages = asyncio.run(enhanced_gmail_receipt_search(gm, days_back=60))
    print(f"\n🎯 Found {len(messages)} potential receipt emails") 
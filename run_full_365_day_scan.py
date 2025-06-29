#!/usr/bin/env python3
"""
Full 365-Day Receipt Scan
Runs personalized email search for the last 365 days and processes all receipts
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_full_365_day_scan():
    """Run a complete 365-day receipt scan for all Gmail accounts"""
    
    logger.info("🚀 Starting Full 365-Day Receipt Scan")
    logger.info("=" * 50)
    
    try:
        from personalized_email_search import PersonalizedEmailSearchSystem
        from multi_gmail_client import MultiGmailClient
        from mongo_client import MongoDBClient
        from comprehensive_receipt_processor import ComprehensiveReceiptProcessor
        
        logger.info("🔧 Initializing system components...")
        
        gmail_client = MultiGmailClient()
        gmail_client.init_services()
        available_accounts = gmail_client.get_available_accounts()
        
        if not available_accounts:
            logger.error("❌ No Gmail accounts available")
            return
        
        logger.info(f"✅ Gmail accounts available: {len(available_accounts)}")
        
        mongo_client = MongoDBClient()
        if not mongo_client.is_connected():
            logger.error("❌ MongoDB not connected")
            return
        
        logger.info("✅ MongoDB connected")
        
        processor = ComprehensiveReceiptProcessor(mongo_client)
        logger.info("✅ Comprehensive receipt processor initialized")
        
        total_emails = 0
        total_receipts = 0
        total_matched = 0
        total_uploaded = 0
        total_attachments = 0
        total_screenshots = 0
        total_url_downloads = 0
        total_errors = 0
        all_errors = []
        
        for account in available_accounts:
            email = account['email']
            service = gmail_client.accounts[email].get('service')
            if not service:
                logger.warning(f"⚠️ No Gmail API service for {email}, skipping.")
                continue
            logger.info(f"🔍 Running personalized search for {email} (365 days)...")
            config = {'gmail_account': email}
            search_system = PersonalizedEmailSearchSystem(
                gmail_service=service,
                mongo_client=mongo_client,
                config=config
            )
            search_results = await search_system.execute_personalized_search(days_back=365)
            emails = search_results.get('emails', [])
            logger.info(f"📧 [{email}] Found {len(emails)} potential receipt emails")
            total_emails += len(emails)
            if not emails:
                continue
            email_candidates = []
            for email_obj in emails:
                candidate = {
                    'id': email_obj.get('message_id', ''),
                    'subject': email_obj.get('subject', ''),
                    'from': email_obj.get('from_email', ''),
                    'date': email_obj.get('date', ''),
                    'body': email_obj.get('body', ''),
                    'has_attachments': email_obj.get('attachment_count', 0) > 0,
                    'receipt_likelihood': email_obj.get('confidence_score', 0.0),
                    'receipt_confidence': email_obj.get('confidence_score', 0.0)
                }
                email_candidates.append(candidate)
            processing_results = processor.process_email_receipts(
                email_candidates, 
                email
            )
            total_receipts += processing_results.get('receipts_processed', 0)
            total_matched += processing_results.get('receipts_matched', 0)
            total_uploaded += processing_results.get('receipts_uploaded', 0)
            total_attachments += processing_results.get('attachments_processed', 0)
            total_screenshots += processing_results.get('body_screenshots', 0)
            total_url_downloads += processing_results.get('url_downloads', 0)
            total_errors += len(processing_results.get('errors', []))
            all_errors.extend(processing_results.get('errors', []))
        logger.info("📊 Scan Results Summary (All Accounts):")
        logger.info("=" * 30)
        logger.info(f"📧 Emails processed: {total_emails}")
        logger.info(f"📄 Receipts found: {total_receipts}")
        logger.info(f"🔗 Receipts matched: {total_matched}")
        logger.info(f"📤 Receipts uploaded: {total_uploaded}")
        logger.info(f"📎 Attachments processed: {total_attachments}")
        logger.info(f"📸 Body screenshots: {total_screenshots}")
        logger.info(f"🔗 URL downloads: {total_url_downloads}")
        logger.info(f"❌ Errors: {total_errors}")
        if all_errors:
            logger.warning("⚠️ Errors encountered:")
            for error in all_errors:
                logger.warning(f"   - {error}")
        logger.info("✅ Full 365-day scan complete!")
    except Exception as e:
        logger.error(f"❌ Error during full scan: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(run_full_365_day_scan()) 
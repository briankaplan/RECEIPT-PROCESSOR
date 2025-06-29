#!/usr/bin/env python3
"""
Debug bank sync functionality
Test Teller integration and see what's happening
"""

import os
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_bank_sync():
    """Debug bank sync functionality"""
    
    logger.info("🔍 Debugging bank sync functionality...")
    
    try:
        # Test 1: Check Teller client
        from teller_client import TellerClient
        
        logger.info("📋 Testing Teller client initialization...")
        teller_client = TellerClient()
        
        # Check credentials
        logger.info(f"   Application ID: {teller_client.application_id}")
        logger.info(f"   Environment: {teller_client.environment}")
        logger.info(f"   API URL: {teller_client.api_url}")
        logger.info(f"   Has credentials: {teller_client._has_credentials()}")
        
        # Test connection
        logger.info("🔗 Testing Teller connection...")
        if teller_client.is_connected():
            logger.info("✅ Teller client is connected!")
        else:
            logger.error("❌ Teller client is not connected")
            return False
        
        # Test 2: Get connected accounts
        logger.info("🏦 Getting connected accounts...")
        accounts = teller_client.get_connected_accounts()
        
        if not accounts:
            logger.warning("⚠️ No connected accounts found")
            return False
        
        logger.info(f"✅ Found {len(accounts)} connected accounts:")
        for account in accounts:
            logger.info(f"   - {account.name} ({account.institution_name}) - Balance: ${account.balance}")
        
        # Test 3: Get transactions for first account
        if accounts:
            account = accounts[0]
            logger.info(f"📊 Getting transactions for {account.name}...")
            
            # Get last 30 days
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            transactions = teller_client.get_transactions(
                account.id,
                start_date=start_date,
                end_date=end_date,
                limit=50
            )
            
            logger.info(f"✅ Found {len(transactions)} transactions")
            
            if transactions:
                logger.info("📋 Sample transactions:")
                for i, tx in enumerate(transactions[:5]):
                    logger.info(f"   {i+1}. {tx.date} - {tx.merchant_name} - ${tx.amount}")
        
        # Test 4: Check database
        logger.info("🗄️ Testing database connection...")
        from mongo_client import MongoDBClient
        
        mongo_client = MongoDBClient()
        if mongo_client.is_connected():
            logger.info("✅ Database is connected!")
            
            # Check existing transactions
            existing_count = mongo_client.db.bank_transactions.count_documents({})
            logger.info(f"📊 Existing transactions in database: {existing_count}")
            
            # Check recent sync jobs
            recent_sync = mongo_client.db.bank_sync_jobs.find_one(
                sort=[('synced_at', -1)]
            )
            
            if recent_sync:
                logger.info(f"📅 Last sync: {recent_sync.get('synced_at')}")
                logger.info(f"   Transactions synced: {recent_sync.get('total_transactions', 0)}")
                logger.info(f"   New transactions: {recent_sync.get('new_transactions', 0)}")
            else:
                logger.info("📅 No previous sync jobs found")
        else:
            logger.error("❌ Database is not connected")
            return False
        
        logger.info("🎯 Bank sync debug completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Bank sync debug failed: {str(e)}")
        return False

if __name__ == "__main__":
    debug_bank_sync() 
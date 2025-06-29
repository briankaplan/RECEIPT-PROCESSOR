#!/usr/bin/env python3
"""
Test Teller connection and account status
"""

import os
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_teller_connection():
    """Test Teller connection and account status"""
    
    logger.info("🔍 Testing Teller connection and account status...")
    
    try:
        from teller_client import TellerClient
        
        # Initialize client
        teller_client = TellerClient()
        
        # Test basic connection
        logger.info("🔗 Testing basic connection...")
        if teller_client.is_connected():
            logger.info("✅ Basic connection successful")
        else:
            logger.error("❌ Basic connection failed")
            return False
        
        # Test accounts endpoint directly
        logger.info("🏦 Testing accounts endpoint...")
        
        url = f"{teller_client.api_url}/accounts"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Teller-Version': teller_client.api_version,
            'User-Agent': 'GmailReceiptProcessor/1.0'
        }
        
        # Add SSL certificates if available
        cert_tuple = None
        if teller_client.cert_path and teller_client.key_path:
            if os.path.exists(teller_client.cert_path) and os.path.exists(teller_client.key_path):
                cert_tuple = (teller_client.cert_path, teller_client.key_path)
                logger.info("🔐 Using SSL certificates")
            else:
                logger.warning("⚠️ Certificate files not found")
        else:
            logger.warning("⚠️ No certificates configured")
        
        try:
            response = requests.get(url, headers=headers, cert=cert_tuple, timeout=10)
            
            logger.info(f"📊 Accounts endpoint response: {response.status_code}")
            
            if response.status_code == 200:
                accounts = response.json()
                logger.info(f"✅ Found {len(accounts)} connected accounts")
                for account in accounts:
                    logger.info(f"   - {account.get('name', 'Unknown')} ({account.get('institution', {}).get('name', 'Unknown Bank')})")
            elif response.status_code == 400:
                logger.error("❌ 400 Bad Request - This usually means:")
                logger.error("   - No bank accounts are connected")
                logger.error("   - Need to complete the Connect flow first")
                logger.error("   - Check the response body for details")
                logger.error(f"   Response: {response.text[:200]}...")
            elif response.status_code == 401:
                logger.error("❌ 401 Unauthorized - Authentication issue")
            elif response.status_code == 403:
                logger.error("❌ 403 Forbidden - Permission issue")
            else:
                logger.error(f"❌ Unexpected status: {response.status_code}")
                logger.error(f"   Response: {response.text[:200]}...")
                
        except Exception as e:
            logger.error(f"❌ Request failed: {str(e)}")
        
        # Test Connect URL generation
        logger.info("🔗 Testing Connect URL generation...")
        connect_url = teller_client.get_connect_url("test_user")
        logger.info(f"✅ Connect URL: {connect_url}")
        
        logger.info("🎯 Teller connection test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_teller_connection() 
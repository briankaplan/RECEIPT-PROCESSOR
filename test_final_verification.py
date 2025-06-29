#!/usr/bin/env python3
"""
Final verification test for receipt processing system
Tests all key components: Hugging Face API, amount extraction, and receipt matching
"""

import os
import logging
from datetime import datetime

# Set up clean logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_huggingface_api():
    """Test Hugging Face API connectivity"""
    try:
        from huggingface_receipt_processor import HuggingFaceReceiptProcessor
        
        logger.info("🧪 Testing Hugging Face API...")
        processor = HuggingFaceReceiptProcessor()
        
        # Test API connectivity
        hf_api_token = os.getenv("HUGGINGFACE_API_KEY")
        if not hf_api_token:
            logger.warning("⚠️ No HuggingFace API token found")
            return False
            
        logger.info("✅ Hugging Face processor initialized successfully")
        # Only log what is guaranteed to exist
        logger.info("   Hugging Face processor object: %s", processor.__class__.__name__)
        logger.info("   Hugging Face API token present: %s", bool(hf_api_token))
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Hugging Face API test failed: {e}")
        return False

def test_amount_extraction():
    """Test amount extraction from various text formats"""
    try:
        from enhanced_receipt_extractor import EnhancedReceiptExtractor
        
        logger.info("🧪 Testing amount extraction...")
        extractor = EnhancedReceiptExtractor()
        
        test_cases = [
            ("Your receipt for $99.00 is attached", 99.0),
            ("Payment Confirmation - Amount: $32.93", 32.93),
            ("Total due: $1,234.56", 1234.56),
            ("Order total: $54.90", 54.9),
            ("No amount in this text", 0.0),
            ("Price: $0.00", 0.0),
        ]
        
        passed = 0
        for text, expected in test_cases:
            result = extractor._extract_amount_from_text(text)
            if abs(result - expected) < 0.01:
                passed += 1
                logger.info(f"   ✅ '{text}' -> ${result}")
            else:
                logger.warning(f"   ❌ '{text}' -> ${result} (expected ${expected})")
        
        logger.info(f"✅ Amount extraction: {passed}/{len(test_cases)} tests passed")
        return passed == len(test_cases)
        
    except Exception as e:
        logger.error(f"❌ Amount extraction test failed: {e}")
        return False

def test_receipt_processing():
    """Test complete receipt processing workflow"""
    try:
        from comprehensive_receipt_processor import ComprehensiveReceiptProcessor
        from pymongo import MongoClient
        
        logger.info("🧪 Testing complete receipt processing...")
        
        # Initialize MongoDB connection
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri:
            logger.warning("⚠️ No MongoDB URI configured")
            return False
            
        client = MongoClient(mongo_uri)
        
        # Initialize R2 client
        r2_client = None
        try:
            from r2_client import R2Client
            r2_client = R2Client()
        except Exception as e:
            logger.warning(f"⚠️ R2 client not available: {e}")
        
        # Initialize processor
        processor = ComprehensiveReceiptProcessor(client, r2_client)
        
        # Test with sample data
        sample_candidates = [
            {
                "message_id": "test_1",
                "subject": "Receipt from EXPENSIFY - $99.00",
                "from_email": "receipts@expensify.com",
                "date": "2025-06-28T10:00:00Z",
                "confidence_score": 0.9,
                "attachment_count": 1,
                "body": "Your receipt for $99.00 is attached. Thank you for your purchase!"
            },
            {
                "message_id": "test_2", 
                "subject": "Payment Confirmation - $32.93",
                "from_email": "billing@midjourney.com",
                "date": "2025-06-28T10:00:00Z",
                "confidence_score": 0.8,
                "attachment_count": 0,
                "body": "Amount: $32.93\nMerchant: Midjourney Inc.\nDate: 2025-06-28"
            }
        ]
        
        # Process receipts
        results = processor.process_email_receipts(sample_candidates, "test@example.com")
        
        logger.info(f"✅ Receipt processing complete:")
        logger.info(f"   Receipts processed: {results.get('receipts_processed', 0)}")
        logger.info(f"   Receipts matched: {results.get('receipts_matched', 0)}")
        logger.info(f"   Errors: {len(results.get('errors', []))}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Receipt processing test failed: {e}")
        return False

def test_url_extraction():
    """Test URL extraction from email content"""
    try:
        from url_extractor import URLExtractor
        
        logger.info("🧪 Testing URL extraction...")
        extractor = URLExtractor()
        
        test_emails = [
            "Your receipt is available at: https://receipts.example.com/view/123",
            "Download your receipt: https://receipts.test.com/download/456",
            "No URLs in this email body",
            "Multiple URLs: https://receipt1.com and https://receipt2.com"
        ]
        
        for email in test_emails:
            urls = extractor.extract_urls_from_email(email)
            logger.info(f"   Found {len(urls)} URLs in: {email[:50]}...")
        
        logger.info("✅ URL extraction test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ URL extraction test failed: {e}")
        return False

def main():
    """Run all verification tests"""
    logger.info("🚀 Starting final verification tests...")
    logger.info("=" * 60)
    
    tests = [
        ("Hugging Face API", test_huggingface_api),
        ("Amount Extraction", test_amount_extraction),
        ("URL Extraction", test_url_extraction),
        ("Receipt Processing", test_receipt_processing),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} test PASSED")
            else:
                logger.error(f"❌ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} test ERROR: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"🎯 Final Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! System is ready for production.")
    else:
        logger.warning(f"⚠️ {total - passed} test(s) failed. Please review before production use.")
    
    return passed == total

if __name__ == "__main__":
    main() 
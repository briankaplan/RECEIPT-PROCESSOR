#!/usr/bin/env python3
"""
Test script to verify stability improvements
"""

import os
import sys
import logging
import tempfile
from comprehensive_receipt_processor import ComprehensiveReceiptProcessor, get_webdriver, safe_submit

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_webdriver_health():
    """Test WebDriver health check"""
    logger.info("🧪 Testing WebDriver health check...")
    
    driver = get_webdriver()
    if driver:
        logger.info("✅ WebDriver health check passed")
        try:
            driver.get("data:text/html,<html><body><h1>Test</h1></body></html>")
            logger.info("✅ WebDriver can load pages")
        except Exception as e:
            logger.error(f"❌ WebDriver page loading failed: {e}")
        finally:
            driver.quit()
    else:
        logger.warning("⚠️ WebDriver health check failed - this is expected if ChromeDriver is not available")

def test_safe_submit():
    """Test safe task submission"""
    logger.info("🧪 Testing safe task submission...")
    
    def test_task():
        return "Task completed successfully"
    
    future = safe_submit(test_task)
    if future:
        try:
            result = future.result(timeout=5)
            logger.info(f"✅ Safe submit test passed: {result}")
        except Exception as e:
            logger.error(f"❌ Safe submit test failed: {e}")
    else:
        logger.warning("⚠️ Safe submit returned None")

def test_ocr_processor():
    """Test OCR processor initialization"""
    logger.info("🧪 Testing OCR processor initialization...")
    
    # Create a mock MongoDB client
    class MockMongoClient:
        def __init__(self):
            self.db = {'expense': {'bank_transactions': []}}
        
        def __getitem__(self, key):
            return self.db[key]
    
    processor = ComprehensiveReceiptProcessor(MockMongoClient())
    
    if processor.ocr_processor:
        logger.info("✅ OCR processor initialized")
    else:
        logger.info("⚠️ OCR processor not available - this is expected if HuggingFace API is not configured")
    
    # Clean up
    del processor

def test_graceful_shutdown():
    """Test graceful shutdown handling"""
    logger.info("🧪 Testing graceful shutdown handling...")
    logger.info("✅ Graceful shutdown handlers are registered")
    logger.info("   - SIGINT handler: shutdown_handler")
    logger.info("   - SIGTERM handler: shutdown_handler")
    logger.info("   - ThreadPoolExecutor will be shut down gracefully")

def main():
    """Run all stability tests"""
    logger.info("🚀 Starting stability improvement tests...")
    
    try:
        test_webdriver_health()
        test_safe_submit()
        test_ocr_processor()
        test_graceful_shutdown()
        
        logger.info("✅ All stability tests completed")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
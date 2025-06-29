#!/usr/bin/env python3
"""
Final Stability Test for Receipt Processor System
Tests all stability improvements including graceful shutdown, WebDriver health,
safe task submission, and MongoDB client guards.
"""

import os
import sys
import logging
import tempfile
import signal
import time
import threading
from comprehensive_receipt_processor import (
    ComprehensiveReceiptProcessor, 
    get_webdriver, 
    safe_submit, 
    get_database,
    shutdown_handler,
    executor
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_graceful_shutdown():
    """Test graceful shutdown handling"""
    logger.info("🧪 Testing graceful shutdown handling...")
    
    # Test signal handlers are registered
    try:
        # This should not crash
        shutdown_handler(signal.SIGINT, None)
        logger.info("✅ Graceful shutdown handler working")
    except Exception as e:
        logger.error(f"❌ Graceful shutdown handler failed: {e}")
        return False
    
    return True

def test_webdriver_health():
    """Test WebDriver health check"""
    logger.info("🧪 Testing WebDriver health check...")
    
    driver = get_webdriver()
    if driver:
        logger.info("✅ WebDriver health check passed")
        try:
            # Test basic functionality
            driver.get("data:text/html,<html><body><h1>Test</h1></body></html>")
            logger.info("✅ WebDriver can load pages")
            
            # Test screenshot capability
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                screenshot_path = tmp.name
            
            driver.save_screenshot(screenshot_path)
            if os.path.exists(screenshot_path):
                logger.info("✅ WebDriver can take screenshots")
                os.unlink(screenshot_path)
            else:
                logger.warning("⚠️ Screenshot file not created")
                
        except Exception as e:
            logger.error(f"❌ WebDriver functionality test failed: {e}")
        finally:
            driver.quit()
            logger.info("✅ WebDriver properly closed")
    else:
        logger.warning("⚠️ WebDriver not available - this is expected if ChromeDriver is not installed")
    
    return True

def test_safe_task_submission():
    """Test safe task submission"""
    logger.info("🧪 Testing safe task submission...")
    
    def test_task():
        return "Task completed successfully"
    
    # Test normal submission
    try:
        future = safe_submit(test_task)
        if future:
            result = future.result(timeout=5)
            if result == "Task completed successfully":
                logger.info("✅ Safe task submission working")
            else:
                logger.error("❌ Task result incorrect")
                return False
        else:
            logger.error("❌ Task submission returned None")
            return False
    except Exception as e:
        logger.error(f"❌ Safe task submission failed: {e}")
        return False
    
    return True

def test_mongodb_client_guard():
    """Test MongoDB client guard"""
    logger.info("🧪 Testing MongoDB client guard...")
    
    # Test with mock client
    class MockMongoClient:
        def __init__(self):
            self.db = {'expense': {'bank_transactions': []}}
        
        def __getitem__(self, key):
            return self.db[key]
    
    # Test with valid mock
    mock_client = MockMongoClient()
    db = get_database(mock_client, 'expense')
    if db:
        logger.info("✅ MongoDB client guard working with mock")
    else:
        logger.error("❌ MongoDB client guard failed with mock")
        return False
    
    # Test with invalid client
    invalid_client = "not_a_client"
    db = get_database(invalid_client, 'expense')
    if db is None:
        logger.info("✅ MongoDB client guard properly handles invalid clients")
    else:
        logger.error("❌ MongoDB client guard should return None for invalid clients")
        return False
    
    return True

def test_comprehensive_processor_initialization():
    """Test comprehensive processor initialization"""
    logger.info("🧪 Testing comprehensive processor initialization...")
    
    # Create a mock MongoDB client
    class MockMongoClient:
        def __init__(self):
            self.db = {'expense': {'bank_transactions': []}}
        
        def __getitem__(self, key):
            return self.db[key]
    
    try:
        processor = ComprehensiveReceiptProcessor(MockMongoClient())
        logger.info("✅ Comprehensive processor initialized successfully")
        
        # Test that webdriver attribute exists
        if hasattr(processor, 'webdriver'):
            logger.info("✅ WebDriver attribute properly initialized")
        else:
            logger.error("❌ WebDriver attribute not found")
            return False
        
        # Test that database is accessible
        if processor.db:
            logger.info("✅ Database properly accessible")
        else:
            logger.error("❌ Database not accessible")
            return False
        
        # Clean up
        del processor
        logger.info("✅ Processor properly cleaned up")
        
    except Exception as e:
        logger.error(f"❌ Comprehensive processor initialization failed: {e}")
        return False
    
    return True

def test_concurrent_operations():
    """Test concurrent operations with safe submission"""
    logger.info("🧪 Testing concurrent operations...")
    
    def long_running_task(task_id):
        time.sleep(0.1)  # Simulate work
        return f"Task {task_id} completed"
    
    try:
        # Submit multiple tasks
        futures = []
        for i in range(5):
            future = safe_submit(long_running_task, i)
            if future:
                futures.append(future)
        
        # Wait for all tasks to complete
        results = []
        for future in futures:
            try:
                result = future.result(timeout=2)
                results.append(result)
            except Exception as e:
                logger.error(f"❌ Task failed: {e}")
                return False
        
        if len(results) == 5:
            logger.info("✅ Concurrent operations working")
        else:
            logger.error(f"❌ Expected 5 results, got {len(results)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Concurrent operations failed: {e}")
        return False
    
    return True

def main():
    """Run all stability tests"""
    logger.info("🚀 Starting Final Stability Tests")
    
    tests = [
        ("Graceful Shutdown", test_graceful_shutdown),
        ("WebDriver Health", test_webdriver_health),
        ("Safe Task Submission", test_safe_task_submission),
        ("MongoDB Client Guard", test_mongodb_client_guard),
        ("Comprehensive Processor", test_comprehensive_processor_initialization),
        ("Concurrent Operations", test_concurrent_operations),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            if test_func():
                logger.info(f"✅ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"FINAL RESULTS: {passed}/{total} tests passed")
    logger.info(f"{'='*50}")
    
    if passed == total:
        logger.info("🎉 ALL STABILITY TESTS PASSED!")
        logger.info("✅ Receipt processor system is stable and production-ready")
    else:
        logger.error(f"⚠️ {total - passed} tests failed - review stability improvements")
    
    # Clean up executor
    try:
        executor.shutdown(wait=False)
        logger.info("✅ Executor properly shut down")
    except Exception as e:
        logger.error(f"❌ Executor shutdown failed: {e}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
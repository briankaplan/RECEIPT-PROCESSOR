#!/usr/bin/env python3
"""
Test script to verify improved receipt detection logic
"""

import logging
from enhanced_receipt_extractor import EnhancedReceiptExtractor
from comprehensive_receipt_processor import ComprehensiveReceiptProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_receipt_detection():
    """Test the improved receipt detection logic"""
    
    # Create mock MongoDB client
    class MockMongoClient:
        def __init__(self):
            self.db = {'expense': {'bank_transactions': []}}
        def __getitem__(self, key):
            return self.db[key]
    
    processor = ComprehensiveReceiptProcessor(MockMongoClient())
    extractor = EnhancedReceiptExtractor()
    
    # Test cases
    test_cases = [
        {
            'name': 'Claude AI Receipt',
            'subject': 'Your Claude.AI subscription payment - $20.00',
            'body': 'Thank you for your Claude.AI subscription. Amount charged: $20.00. Transaction ID: 12345',
            'from_email': 'receipts@anthropic.com',
            'expected_merchant': 'ANTHROPIC',
            'expected_amount': 20.0,
            'should_be_receipt': True
        },
        {
            'name': 'GitHub Build Failure (NOT a receipt)',
            'subject': 'BUILD FAILED FOR RECEIPT-PROCESSOR',
            'body': 'We encountered an error during the build process for your repository.',
            'from_email': 'noreply@github.com',
            'expected_merchant': '',
            'expected_amount': 0.0,
            'should_be_receipt': False
        },
        {
            'name': 'Every.com Marketing (NOT a receipt)',
            'subject': 'Your personalized offers from Every',
            'body': 'Check out these amazing deals just for you!',
            'from_email': 'marketing@every.com',
            'expected_merchant': '',
            'expected_amount': 0.0,
            'should_be_receipt': False
        },
        {
            'name': 'OpenAI Receipt',
            'subject': 'OpenAI API Usage - $15.50',
            'body': 'Your OpenAI API usage for this month. Total charged: $15.50',
            'from_email': 'billing@openai.com',
            'expected_merchant': 'OPENAI',
            'expected_amount': 15.50,
            'should_be_receipt': True
        },
        {
            'name': 'Microsoft Receipt',
            'subject': 'Microsoft 365 subscription - $99.99',
            'body': 'Your Microsoft 365 subscription has been renewed. Amount: $99.99',
            'from_email': 'billing@microsoft.com',
            'expected_merchant': 'MICROSOFT',
            'expected_amount': 99.99,
            'should_be_receipt': True
        }
    ]
    
    logger.info("🧪 Testing improved receipt detection logic...")
    
    for test_case in test_cases:
        logger.info(f"\n📧 Testing: {test_case['name']}")
        
        # Test receipt content detection
        is_receipt = processor._contains_receipt_content(test_case['body'])
        logger.info(f"  Receipt content detected: {is_receipt} (expected: {test_case['should_be_receipt']})")
        
        # Test merchant and amount extraction
        email_data = {
            'subject': test_case['subject'],
            'body': test_case['body'],
            'from_email': test_case['from_email'],
            'date': '2025-06-28'
        }
        
        extracted = extractor.extract_from_email(email_data)
        logger.info(f"  Extracted merchant: {extracted.merchant} (expected: {test_case['expected_merchant']})")
        logger.info(f"  Extracted amount: ${extracted.amount} (expected: ${test_case['expected_amount']})")
        logger.info(f"  Confidence: {extracted.confidence:.2f}")
        logger.info(f"  Method: {extracted.extraction_method}")
        
        # Verify results
        merchant_correct = extracted.merchant == test_case['expected_merchant']
        amount_correct = abs(extracted.amount - test_case['expected_amount']) < 0.01
        receipt_correct = is_receipt == test_case['should_be_receipt']
        
        if merchant_correct and amount_correct and receipt_correct:
            logger.info("  ✅ All tests passed!")
        else:
            logger.warning("  ⚠️ Some tests failed:")
            if not merchant_correct:
                logger.warning(f"    - Merchant mismatch: got '{extracted.merchant}', expected '{test_case['expected_merchant']}'")
            if not amount_correct:
                logger.warning(f"    - Amount mismatch: got ${extracted.amount}, expected ${test_case['expected_amount']}")
            if not receipt_correct:
                logger.warning(f"    - Receipt detection mismatch: got {is_receipt}, expected {test_case['should_be_receipt']}")

def test_brand_mappings():
    """Test brand mappings specifically"""
    logger.info("\n🧪 Testing brand mappings...")
    
    extractor = EnhancedReceiptExtractor()
    
    brand_tests = [
        ('claude', 'ANTHROPIC'),
        ('claude ai', 'ANTHROPIC'),
        ('anthropic claude', 'ANTHROPIC'),
        ('openai', 'OPENAI'),
        ('chatgpt', 'OPENAI'),
        ('github', 'GITHUB'),
        ('microsoft', 'MICROSOFT'),
        ('every', 'EVERY.COM')
    ]
    
    for brand_input, expected_output in brand_tests:
        result = extractor._extract_merchant_from_text(f"Payment to {brand_input}")
        logger.info(f"  {brand_input} -> {result} (expected: {expected_output})")
        if result == expected_output:
            logger.info("    ✅ Correct")
        else:
            logger.warning("    ⚠️ Incorrect")

if __name__ == "__main__":
    test_receipt_detection()
    test_brand_mappings()
    logger.info("\n🎉 Testing complete!") 
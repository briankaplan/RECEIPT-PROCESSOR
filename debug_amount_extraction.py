#!/usr/bin/env python3
"""
Debug script to test amount extraction logic
"""

import re
import logging
from enhanced_receipt_extractor import EnhancedReceiptExtractor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_amount_patterns():
    """Test the amount extraction patterns"""
    extractor = EnhancedReceiptExtractor()
    
    # Test cases with different amount formats
    test_texts = [
        "Your payment of $20.00 has been processed",
        "Amount: $244.87",
        "Total charged: $10.50",
        "Payment confirmation for $99.99",
        "Receipt for $15.75",
        "Invoice amount: $1,234.56",
        "You were charged $5.00",
        "Subscription fee: $29.99",
        "Order total: $199.99",
        "Bill amount: $0.00",  # This should return 0
        "Free trial - $0.00",  # This should return 0
        "No amount specified",  # This should return 0
        "Amount is $",  # Incomplete amount
        "Price: $abc",  # Invalid amount
    ]
    
    print("🧪 Testing Amount Extraction Patterns")
    print("=" * 50)
    
    for i, text in enumerate(test_texts, 1):
        amount = extractor._extract_amount_from_text(text)
        print(f"Test {i:2d}: {text}")
        print(f"       Extracted: ${amount}")
        print()
    
    # Test the actual patterns
    print("🔍 Testing Individual Patterns")
    print("=" * 50)
    
    for i, pattern in enumerate(extractor.amount_patterns):
        print(f"Pattern {i+1}: {pattern}")
        
        # Test with sample text
        test_text = "Your payment of $25.50 has been processed"
        match = re.search(pattern, test_text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            amount = float(amount_str)
            print(f"  Match: {match.group(0)}")
            print(f"  Group 1: {match.group(1)}")
            print(f"  Amount: ${amount}")
        else:
            print(f"  No match")
        print()

def test_real_email_data():
    """Test with real email data from logs"""
    extractor = EnhancedReceiptExtractor()
    
    # Sample email data based on what we see in logs
    test_emails = [
        {
            'subject': 'Claude subscription',
            'body': 'Your Claude subscription has been renewed. Amount: $20.00',
            'from_email': 'billing@claude.ai',
            'date': '2025-06-28'
        },
        {
            'subject': 'EVERY Studio receipt',
            'body': 'Thank you for your purchase from EVERY Studio. Total: $100.00',
            'from_email': 'receipts@every.studio',
            'date': '2025-06-28'
        },
        {
            'subject': 'Build failed notification',
            'body': 'We encountered an error during the build process. No charge.',
            'from_email': 'notifications@github.com',
            'date': '2025-06-28'
        }
    ]
    
    print("📧 Testing Real Email Data")
    print("=" * 50)
    
    for i, email in enumerate(test_emails, 1):
        print(f"Email {i}:")
        print(f"  Subject: {email['subject']}")
        print(f"  Body: {email['body']}")
        
        result = extractor.extract_from_email(email)
        print(f"  Extracted: {result.merchant} - ${result.amount} (confidence: {result.confidence:.2f})")
        print(f"  Method: {result.extraction_method}")
        print()

def debug_specific_case():
    """Debug a specific case from the logs"""
    extractor = EnhancedReceiptExtractor()
    
    # This is the kind of text we're seeing in logs
    problematic_text = "WE ENCOUNTERED AN ERROR DURING THE BUILD PROCESS FOR"
    
    print("🐛 Debugging Specific Case")
    print("=" * 50)
    print(f"Text: {problematic_text}")
    
    # Test amount extraction
    amount = extractor._extract_amount_from_text(problematic_text)
    print(f"Amount extracted: ${amount}")
    
    # Test merchant extraction
    merchant = extractor._extract_merchant_from_text(problematic_text)
    print(f"Merchant extracted: {merchant}")
    
    # Test all patterns
    print("\nTesting all amount patterns:")
    for i, pattern in enumerate(extractor.amount_patterns):
        match = re.search(pattern, problematic_text, re.IGNORECASE)
        if match:
            print(f"  Pattern {i+1} matched: {match.group(0)}")
        else:
            print(f"  Pattern {i+1}: no match")

if __name__ == "__main__":
    test_amount_patterns()
    test_real_email_data()
    debug_specific_case() 
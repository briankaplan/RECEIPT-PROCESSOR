#!/usr/bin/env python3
"""
Debug script to test extraction and matching process
"""

import asyncio
import logging
from datetime import datetime
from pymongo import MongoClient
from personalized_email_search import PersonalizedEmailSearchSystem
from comprehensive_receipt_processor import ComprehensiveReceiptProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_extraction_and_matching():
    """Test the extraction and matching process"""
    
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['expense']
    
    # Get some transactions for testing
    transactions = list(db.bank_transactions.find({}).limit(10))
    logger.info(f"📊 Found {len(transactions)} transactions for testing")
    
    # Print transaction details
    for i, txn in enumerate(transactions):
        merchant = txn.get('merchant') or txn.get('description', 'Unknown')
        amount = abs(float(txn.get('amount', 0)))
        date = txn.get('date', 'Unknown')
        logger.info(f"Transaction {i+1}: {merchant} - ${amount} - {date}")
    
    # Test fallback extraction methods
    from comprehensive_receipt_processor import ComprehensiveReceiptProcessor
    
    processor = ComprehensiveReceiptProcessor(client, None)
    
    # Test subject extraction
    test_subjects = [
        "Receipt from Claude.AI - $20.00",
        "Your Midjourney subscription - $10.00",
        "Google Workspace payment - $244.87",
        "Best Buy purchase confirmation - $599.99",
        "Hive Co invoice - $1,745.83"
    ]
    
    logger.info("\n🔍 Testing subject extraction:")
    for subject in test_subjects:
        merchant = processor._extract_merchant_from_subject(subject)
        amount = processor._extract_amount_from_subject(subject)
        logger.info(f"Subject: '{subject}'")
        logger.info(f"  -> Merchant: '{merchant}'")
        logger.info(f"  -> Amount: ${amount}")
        
        # Test matching
        if merchant and amount:
            match = processor._match_receipt_to_transaction({
                'merchant': merchant,
                'amount': amount,
                'date': datetime.now().isoformat()
            }, transactions)
            
            if match:
                logger.info(f"  -> ✅ MATCH: {match.transaction_data.get('merchant', 'Unknown')} - ${match.transaction_data.get('amount', 0)} (confidence: {match.confidence})")
            else:
                logger.info(f"  -> ❌ NO MATCH")
        logger.info("")
    
    # Test merchant similarity
    logger.info("🔍 Testing merchant similarity:")
    test_merchants = [
        ("claude.ai", "CLAUDE.AI"),
        ("midjourney", "MIDJOURNEY INC."),
        ("google", "GOOGLE *GSUITE_musicci"),
        ("best buy", "BESTBUY.COM"),
        ("hive co", "HIVE CO")
    ]
    
    for test_merchant, actual_merchant in test_merchants:
        similarity = processor._calculate_merchant_similarity(test_merchant, actual_merchant)
        logger.info(f"'{test_merchant}' vs '{actual_merchant}' -> {similarity:.2f}")
    
    # Test with actual email candidates
    logger.info("\n🔍 Testing with actual email candidates:")
    
    # Create mock email candidates based on your transaction data
    mock_candidates = []
    for txn in transactions[:5]:  # Test with first 5 transactions
        merchant = txn.get('merchant') or txn.get('description', 'Unknown')
        amount = abs(float(txn.get('amount', 0)))
        
        # Create realistic email subject
        subject = f"Receipt from {merchant} - ${amount:.2f}"
        
        mock_candidates.append({
            "message_id": f"test_{txn.get('_id')}",
            "subject": subject,
            "from_email": f"receipts@{merchant.lower().replace(' ', '').replace('*', '')}.com",
            "date": txn.get('date', datetime.now().isoformat()),
            "confidence_score": 0.8,
            "attachment_count": 0,
            "body": f"Thank you for your purchase from {merchant}. Total amount: ${amount:.2f}"
        })
    
    # Process with comprehensive processor
    results = processor.process_email_receipts(mock_candidates, "test@example.com")
    
    logger.info(f"\n📊 Processing Results:")
    logger.info(f"Receipts processed: {results.get('receipts_processed', 0)}")
    logger.info(f"Receipts matched: {results.get('receipts_matched', 0)}")
    logger.info(f"Receipts uploaded: {results.get('receipts_uploaded', 0)}")
    logger.info(f"Attachments processed: {results.get('attachments_processed', 0)}")
    logger.info(f"Body screenshots: {results.get('body_screenshots', 0)}")
    logger.info(f"URL downloads: {results.get('url_downloads', 0)}")
    
    if results.get('errors'):
        logger.info(f"Errors: {results.get('errors')}")

if __name__ == "__main__":
    asyncio.run(test_extraction_and_matching()) 
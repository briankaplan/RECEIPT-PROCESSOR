#!/usr/bin/env python3
"""Test the comprehensive receipt processing workflow"""

import os
import logging
from datetime import datetime
from pymongo import MongoClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def test_comprehensive_workflow():
    """Test the comprehensive receipt processing workflow"""
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri:
            print("❌ No MongoDB URI configured")
            return
        
        client = MongoClient(mongo_uri)
        db = client.expense
        
        print("🧪 TESTING COMPREHENSIVE RECEIPT PROCESSING WORKFLOW")
        print("=" * 60)
        
        # Test 1: Check if comprehensive processor can be imported
        try:
            from comprehensive_receipt_processor import ComprehensiveReceiptProcessor
            print("✅ ComprehensiveReceiptProcessor imported successfully")
        except Exception as e:
            print(f"❌ Failed to import ComprehensiveReceiptProcessor: {e}")
            return
        
        # Test 2: Initialize the processor
        try:
            # Initialize R2 client
            r2_client = None
            try:
                from r2_client import R2Client
                r2_client = R2Client()
                print("✅ R2 client initialized")
            except Exception as e:
                print(f"⚠️ R2 client not available: {e}")
            
            processor = ComprehensiveReceiptProcessor(client, r2_client)
            print("✅ ComprehensiveReceiptProcessor initialized")
        except Exception as e:
            print(f"❌ Failed to initialize processor: {e}")
            return
        
        # Test 3: Test with sample data
        print("\n📧 Testing with sample email candidates...")
        
        sample_candidates = [
            {
                "message_id": "test_attachment_1",
                "subject": "Receipt from EXPENSIFY - $99.00",
                "from_email": "receipts@expensify.com",
                "date": "2025-06-28T10:00:00Z",
                "confidence_score": 0.9,
                "attachment_count": 1,
                "body": "Your receipt for $99.00 is attached. Thank you for your purchase!"
            },
            {
                "message_id": "test_body_1",
                "subject": "Payment Confirmation - $32.93",
                "from_email": "billing@midjourney.com",
                "date": "2025-06-28T10:00:00Z",
                "confidence_score": 0.8,
                "attachment_count": 0,
                "body": """
                <div class="receipt">
                    <h2>Payment Confirmation</h2>
                    <p>Amount: $32.93</p>
                    <p>Merchant: Midjourney Inc.</p>
                    <p>Date: 2025-06-28</p>
                    <p>Thank you for your subscription!</p>
                </div>
                """
            },
            {
                "message_id": "test_url_1",
                "subject": "Your Receipt is Ready",
                "from_email": "receipts@anthropic.com",
                "date": "2025-06-28T10:00:00Z",
                "confidence_score": 0.7,
                "attachment_count": 0,
                "body": "Your receipt for $54.90 is available at: https://receipts.anthropic.com/view/12345"
            }
        ]
        
        # Process with comprehensive workflow
        results = processor.process_email_receipts(sample_candidates, "test@example.com")
        
        print(f"\n📊 Processing Results:")
        print(f"  Receipts processed: {results.get('receipts_processed', 0)}")
        print(f"  Receipts matched: {results.get('receipts_matched', 0)}")
        print(f"  Receipts uploaded: {results.get('receipts_uploaded', 0)}")
        print(f"  Attachments processed: {results.get('attachments_processed', 0)}")
        print(f"  Body screenshots: {results.get('body_screenshots', 0)}")
        print(f"  URL downloads: {results.get('url_downloads', 0)}")
        print(f"  Errors: {len(results.get('errors', []))}")
        
        if results.get('errors'):
            print(f"\n❌ Errors encountered:")
            for error in results.get('errors', []):
                print(f"  - {error}")
        
        # Test 4: Check database for new receipts
        print(f"\n🔍 Checking database for new receipts...")
        
        # Get receipts created in the last hour
        recent_receipts = list(db.receipts.find({
            'scanned_at': {
                '$gte': datetime.utcnow().replace(minute=0, second=0, microsecond=0).isoformat()
            }
        }))
        
        print(f"  Recent receipts found: {len(recent_receipts)}")
        
        for receipt in recent_receipts[:3]:
            print(f"    - {receipt.get('merchant', 'Unknown')} - ${receipt.get('amount', 0)}")
            print(f"      Source: {receipt.get('source_type', 'unknown')}")
            print(f"      Transaction ID: {receipt.get('transaction_id', 'None')}")
            print(f"      R2 URL: {'Yes' if receipt.get('r2_url') else 'No'}")
        
        # Test 5: Check transactions with receipt URLs
        transactions_with_receipts = list(db.bank_transactions.find({
            'receipt_url': {'$exists': True, '$ne': ''}
        }))
        
        print(f"\n💰 Transactions with receipt URLs: {len(transactions_with_receipts)}")
        
        # Test 6: Verify the workflow components
        print(f"\n🔧 Workflow Component Verification:")
        
        # Check URL extractor
        try:
            from url_extractor import URLExtractor
            url_extractor = URLExtractor()
            test_urls = url_extractor.extract_urls_from_email("Your receipt is at https://receipts.example.com/view/123")
            print(f"  ✅ URL extractor: {len(test_urls)} URLs found")
        except Exception as e:
            print(f"  ❌ URL extractor: {e}")
        
        # Check OCR processor
        try:
            from huggingface_receipt_processor import HuggingFaceReceiptProcessor
            ocr_processor = HuggingFaceReceiptProcessor()
            print(f"  ✅ OCR processor: Available")
        except Exception as e:
            print(f"  ❌ OCR processor: {e}")
        
        # Check R2 client
        if r2_client:
            print(f"  ✅ R2 client: Connected")
        else:
            print(f"  ⚠️ R2 client: Not available")
        
        print(f"\n🎉 Comprehensive workflow test complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_comprehensive_workflow()

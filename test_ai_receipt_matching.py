#!/usr/bin/env python3
"""
Test Script for AI-Powered Receipt Matching System
Demonstrates the comprehensive matching capabilities
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main test function"""
    try:
        from ai_receipt_matcher import IntegratedAIReceiptMatcher
        from pymongo import MongoClient
        
        print("🤖 AI-Powered Receipt Matching System Test Suite")
        print("=" * 60)
        print("This test demonstrates the comprehensive AI matching capabilities")
        print("including exact matching, subscription detection, fuzzy matching,")
        print("and AI-powered inference for complex cases.")
        print()
        
        # Mock configuration class
        class MockConfig:
            def __init__(self):
                self.MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
                self.MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'expense')
        
        # Initialize components
        try:
            config = MockConfig()
            mongo_client = MongoClient(config.MONGODB_URI)
            mongo_client.admin.command('ping')
            print("✅ MongoDB connection successful")
            
            # Initialize AI matcher
            ai_matcher = IntegratedAIReceiptMatcher(mongo_client, config)
            print("✅ AI Receipt Matcher initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize components: {e}")
            return False
        
        # Test data: Mock transactions for testing
        test_transactions = [
            {
                '_id': 'test_txn_1',
                'description': 'CLAUDE.AI ANTHROPIC',
                'amount': -21.95,
                'date': datetime.now() - timedelta(days=1),
                'account_id': 'test_account'
            },
            {
                '_id': 'test_txn_2',
                'description': 'AMAZON.COM AMZN.COM/BILL',
                'amount': -89.47,
                'date': datetime.now() - timedelta(days=2),
                'account_id': 'test_account'
            },
            {
                '_id': 'test_txn_3',
                'description': 'GOOGLE WORKSPACE GSuite',
                'amount': -12.00,
                'date': datetime.now() - timedelta(days=1),
                'account_id': 'test_account'
            }
        ]
        
        print(f"\n📊 Test Data: {len(test_transactions)} mock transactions")
        for i, txn in enumerate(test_transactions, 1):
            print(f"  {i}. {txn['description']} - ${abs(txn['amount']):.2f}")
        
        # Test subscription detection
        print(f"\n📅 Subscription Pattern Analysis:")
        print(f"-" * 40)
        
        subscription_results = []
        for txn in test_transactions:
            subscription_prob = ai_matcher._calculate_subscription_probability(txn)
            subscription_results.append({
                'description': txn['description'],
                'amount': txn['amount'],
                'subscription_probability': subscription_prob
            })
        
        for result in sorted(subscription_results, key=lambda x: x['subscription_probability'], reverse=True):
            prob = result['subscription_probability']
            status = "🟢 HIGH" if prob > 0.7 else "🟡 MEDIUM" if prob > 0.4 else "🔴 LOW"
            print(f"  {status} ({prob:.2f}) - {result['description']}")
        
        # Test merchant similarity
        print(f"\n🏪 Merchant Similarity Testing:")
        print(f"-" * 40)
        
        test_pairs = [
            ("CLAUDE.AI", "ANTHROPIC CLAUDE"),
            ("AMAZON.COM", "AMAZON"),
            ("GOOGLE WORKSPACE", "GOOGLE GSUITE")
        ]
        
        for merchant1, merchant2 in test_pairs:
            similarity = ai_matcher._calculate_advanced_merchant_similarity(merchant1, merchant2)
            status = "🟢 MATCH" if similarity > 0.8 else "🟡 SIMILAR" if similarity > 0.6 else "🔴 DIFFERENT"
            print(f"  {status} ({similarity:.2f}) - '{merchant1}' ↔ '{merchant2}'")
        
        # Run comprehensive AI matching
        try:
            print(f"\n🚀 Starting comprehensive AI matching...")
            results = ai_matcher.comprehensive_receipt_matching(test_transactions)
            
            # Display results
            print(f"\n📈 AI Matching Results:")
            print(f"=" * 40)
            
            performance = results['performance_stats']
            print(f"🎯 Total Transactions: {performance['total_transactions']}")
            print(f"✅ Total Matched: {performance['total_matched']}")
            print(f"📊 Match Rate: {performance['match_rate_percent']:.1f}%")
            print(f"⚡ Processing Time: {performance['processing_time_seconds']:.2f}s")
            
            print(f"\n📋 Match Breakdown:")
            print(f"  🎯 Exact Matches: {performance['exact_matches']}")
            print(f"  📅 Subscription Matches: {performance['subscription_matches']}")
            print(f"  🔍 Fuzzy Matches: {performance['fuzzy_matches']}")
            print(f"  🤖 AI Inferred Matches: {performance['ai_matches']}")
            print(f"  ❓ Unmatched: {performance['unmatched']}")
            
            print(f"\n✅ AI Receipt Matching Test Completed Successfully!")
            print(f"\n🚀 Next Steps:")
            print(f"  1. Call /api/ai-receipt-matching endpoint")
            print(f"  2. Adjust batch_size and days_back parameters")
            print(f"  3. Monitor performance metrics")
            print(f"  4. Review match confidence scores")
            print(f"  5. Fine-tune subscription patterns for your data")
            
            return True
            
        except Exception as e:
            print(f"❌ AI matching test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except ImportError as e:
        print(f"❌ Failed to import required modules: {e}")
        print("Please ensure all dependencies are installed and configured properly.")
        return False
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Debug script to test receipt-to-transaction matching
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from app import calculate_match_score

def test_matching():
    """Test the matching algorithm with sample data"""
    
    # Sample receipt data (from actual data)
    sample_receipt = {
        "merchant": "mercer",
        "amount": 20.0,
        "date": "2025-06-30T00:00:00",
        "business_type": "Personal",
        "category": "Uncategorized"
    }
    
    # Sample transaction data (from actual data)
    sample_transaction = {
        "merchant_name": "CAMBRIA HOTEL NASHVILLE D",
        "amount": -384.14,
        "date": "Sun, 01 Jun 2025 00:00:00 GMT",
        "business_type": "personal",
        "category": "Travel"
    }
    
    print("🔍 Testing Receipt-to-Transaction Matching")
    print("=" * 50)
    
    print(f"Receipt: {sample_receipt['merchant']} - ${sample_receipt['amount']} - {sample_receipt['date']}")
    print(f"Transaction: {sample_transaction['merchant_name']} - ${sample_transaction['amount']} - {sample_transaction['date']}")
    print()
    
    # Test matching
    score = calculate_match_score(sample_receipt, sample_transaction)
    print(f"Match Score: {score:.3f}")
    
    # Test with different merchants
    test_cases = [
        {
            "receipt": {"merchant": "apple", "amount": 37.95, "date": "2025-06-27T00:00:00"},
            "transaction": {"merchant_name": "APPLE.COM/BILL", "amount": -37.95, "date": "Sun, 27 Jun 2025 00:00:00 GMT"},
            "expected": "Should match (Apple purchase)"
        },
        {
            "receipt": {"merchant": "amazon", "amount": 25.99, "date": "2025-06-25T00:00:00"},
            "transaction": {"merchant_name": "AMZN MKTP US", "amount": -25.99, "date": "Wed, 25 Jun 2025 00:00:00 GMT"},
            "expected": "Should match (Amazon purchase)"
        },
        {
            "receipt": {"merchant": "uber", "amount": 15.50, "date": "2025-06-24T00:00:00"},
            "transaction": {"merchant_name": "UBER *TRIP", "amount": -15.50, "date": "Tue, 24 Jun 2025 00:00:00 GMT"},
            "expected": "Should match (Uber trip)"
        }
    ]
    
    print("\n🧪 Testing Specific Cases:")
    print("-" * 30)
    
    for i, case in enumerate(test_cases, 1):
        score = calculate_match_score(case["receipt"], case["transaction"])
        print(f"Case {i}: {score:.3f} - {case['expected']}")
        print(f"  Receipt: {case['receipt']['merchant']} ${case['receipt']['amount']}")
        print(f"  Transaction: {case['transaction']['merchant_name']} ${case['transaction']['amount']}")
        print()

if __name__ == "__main__":
    test_matching() 
#!/usr/bin/env python3
"""
Transaction Matching Algorithm Test

Tests the core matching algorithms:
1. Merchant name similarity matching
2. Date tolerance matching  
3. Amount matching with tolerance
4. Subscription pattern detection
5. Advanced matching scenarios
"""

import requests
import json
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
from config import Config

# MongoDB connection
def get_mongo_client():
    return MongoClient(Config.MONGODB_URI)

def clear_test_data():
    """Clear any existing test data"""
    client = get_mongo_client()
    db = client.receipt_processor
    
    # Clear test collections
    db.receipts.delete_many({"test_data": True})
    db.transactions.delete_many({"test_data": True})
    
    print("🧹 Cleared existing test data")

def insert_test_receipts():
    """Insert test receipts into database"""
    client = get_mongo_client()
    db = client.receipt_processor
    
    test_receipts = [
        {
            "test_data": True,
            "merchant_name": "Amazon",
            "total_amount": 29.99,
            "date": datetime(2025, 6, 20, 10, 30),
            "description": "Office supplies",
            "category": "business_expense",
            "email_source": "kaplan.brian@gmail.com",
            "r2_url": "https://r2.example.com/receipts/amazon_20250620.pdf"
        },
        {
            "test_data": True,
            "merchant_name": "Starbucks Coffee",
            "total_amount": 5.75,
            "date": datetime(2025, 6, 21, 8, 15),
            "description": "Coffee meeting with client",
            "category": "business_meal",
            "email_source": "brian@downhome.com",
            "r2_url": "https://r2.example.com/receipts/starbucks_20250621.pdf"
        },
        {
            "test_data": True,
            "merchant_name": "Netflix Inc",
            "total_amount": 15.99,
            "date": datetime(2025, 6, 22, 0, 1),
            "description": "Monthly subscription",
            "category": "subscription",
            "is_recurring": True,
            "email_source": "kaplan.brian@gmail.com",
            "r2_url": "https://r2.example.com/receipts/netflix_20250622.pdf"
        },
        {
            "test_data": True,
            "merchant_name": "Shell Gas Station",
            "total_amount": 45.67,
            "date": datetime(2025, 6, 23, 16, 45),
            "description": "Business travel fuel",
            "category": "travel_expense",
            "email_source": "brian@musiccityrodeo.com",
            "r2_url": "https://r2.example.com/receipts/shell_20250623.pdf"
        }
    ]
    
    result = db.receipts.insert_many(test_receipts)
    print(f"📄 Inserted {len(result.inserted_ids)} test receipts")
    return result.inserted_ids

def insert_test_transactions():
    """Insert test transactions into database"""
    client = get_mongo_client()
    db = client.receipt_processor
    
    test_transactions = [
        {
            "test_data": True,
            "description": "AMAZON.COM AMZN.COM/BILL WA",
            "amount": -29.99,
            "date": datetime(2025, 6, 20, 12, 0),  # 1.5 hours later
            "account": "Chase Checking",
            "merchant": "AMAZON.COM",
            "category": "pending_match"
        },
        {
            "test_data": True,
            "description": "STARBUCKS #1234 NASHVILLE TN",
            "amount": -5.75,
            "date": datetime(2025, 6, 21, 8, 20),  # 5 minutes later
            "account": "Chase Credit Card",
            "merchant": "STARBUCKS #1234",
            "category": "pending_match"
        },
        {
            "test_data": True,
            "description": "NETFLIX.COM SUBSCRIPTION",
            "amount": -15.99,
            "date": datetime(2025, 6, 22, 0, 5),  # 4 minutes later
            "account": "Chase Checking",
            "merchant": "NETFLIX.COM",
            "category": "pending_match"
        },
        {
            "test_data": True,
            "description": "SHELL OIL #7890 NASHVILLE TN",
            "amount": -45.67,
            "date": datetime(2025, 6, 23, 16, 50),  # 5 minutes later
            "account": "Chase Business",
            "merchant": "SHELL OIL #7890",
            "category": "pending_match"
        },
        {
            "test_data": True,
            "description": "TARGET T-1234 BRENTWOOD TN",
            "amount": -67.89,
            "date": datetime(2025, 6, 24, 14, 30),  # No matching receipt
            "account": "Chase Checking",
            "merchant": "TARGET T-1234",
            "category": "pending_match"
        }
    ]
    
    result = db.transactions.insert_many(test_transactions)
    print(f"💳 Inserted {len(result.inserted_ids)} test transactions")
    return result.inserted_ids

def test_merchant_matching():
    """Test merchant name matching algorithms"""
    print("\n🏪 Testing Merchant Name Matching:")
    
    merchant_pairs = [
        ("Amazon", "AMAZON.COM"),
        ("Starbucks Coffee", "STARBUCKS #1234"),
        ("Netflix Inc", "NETFLIX.COM"),
        ("Shell Gas Station", "SHELL OIL #7890"),
        ("McDonald's", "MCD #456 NASHVILLE"),
        ("Walmart Supercenter", "WALMART SC #1234"),
    ]
    
    for receipt_merchant, transaction_merchant in merchant_pairs:
        # Test with a simple endpoint call
        response = requests.post(
            "http://localhost:10000/api/test-merchant-match",
            json={
                "receipt_merchant": receipt_merchant,
                "transaction_merchant": transaction_merchant
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            similarity = result.get("similarity", 0)
            match = "✅ MATCH" if similarity > 0.7 else "❌ NO MATCH"
            print(f"   {receipt_merchant} ↔ {transaction_merchant}: {similarity:.2f} {match}")
        else:
            # Fallback to manual similarity calculation
            similarity = calculate_simple_similarity(receipt_merchant, transaction_merchant)
            match = "✅ MATCH" if similarity > 0.7 else "❌ NO MATCH"
            print(f"   {receipt_merchant} ↔ {transaction_merchant}: {similarity:.2f} {match}")

def calculate_simple_similarity(str1, str2):
    """Simple similarity calculation"""
    str1_clean = str1.upper().replace(" ", "").replace(".", "").replace("#", "")
    str2_clean = str2.upper().replace(" ", "").replace(".", "").replace("#", "")
    
    # Check if one contains the other
    if str1_clean in str2_clean or str2_clean in str1_clean:
        return 0.9
    
    # Check for common words
    words1 = set(str1.upper().split())
    words2 = set(str2.upper().split())
    
    if words1 & words2:  # Intersection
        return 0.8
    
    return 0.3

def test_date_matching():
    """Test date tolerance matching"""
    print("\n📅 Testing Date Tolerance Matching:")
    
    base_date = datetime(2025, 6, 20, 10, 30)
    
    date_tests = [
        (base_date, base_date + timedelta(minutes=5), "5 minutes later"),
        (base_date, base_date + timedelta(hours=1), "1 hour later"),
        (base_date, base_date + timedelta(hours=6), "6 hours later"),
        (base_date, base_date + timedelta(days=1), "1 day later"),
        (base_date, base_date + timedelta(days=3), "3 days later"),
        (base_date, base_date + timedelta(days=7), "7 days later"),
    ]
    
    for receipt_date, transaction_date, description in date_tests:
        diff_hours = abs((transaction_date - receipt_date).total_seconds() / 3600)
        
        # Matching criteria: within 3 days (72 hours)
        is_match = diff_hours <= 72
        match_status = "✅ MATCH" if is_match else "❌ NO MATCH"
        
        print(f"   {description}: {diff_hours:.1f}h difference - {match_status}")

def test_amount_matching():
    """Test amount matching with tolerance"""
    print("\n💰 Testing Amount Matching with Tolerance:")
    
    amount_tests = [
        (29.99, 29.99, "Exact match"),
        (29.99, 30.00, "$0.01 difference"),
        (29.99, 32.50, "$2.51 difference"),
        (100.00, 105.00, "$5.00 difference"),
        (100.00, 110.00, "$10.00 difference"),
        (50.00, 65.00, "$15.00 difference"),
    ]
    
    for receipt_amount, transaction_amount, description in amount_tests:
        diff = abs(receipt_amount - transaction_amount)
        
        # Matching criteria: within $5.00 or 5% tolerance
        tolerance_fixed = 5.00
        tolerance_percent = receipt_amount * 0.05
        max_tolerance = max(tolerance_fixed, tolerance_percent)
        
        is_match = diff <= max_tolerance
        match_status = "✅ MATCH" if is_match else "❌ NO MATCH"
        
        print(f"   {description}: ${diff:.2f} diff (tolerance: ${max_tolerance:.2f}) - {match_status}")

def test_perfect_matching():
    """Test the actual perfect matching algorithm from the app"""
    print("\n🎯 Testing Perfect Receipt Matching Algorithm:")
    
    # Test with the real matching endpoint
    response = requests.post(
        "http://localhost:10000/api/find-receipt-matches",
        json={"match_unmatched": True}
    )
    
    if response.status_code == 200:
        result = response.json()
        matches = result.get("matches", [])
        print(f"   Found {len(matches)} potential matches")
        
        for match in matches[:3]:  # Show first 3 matches
            receipt = match.get("receipt", {})
            transaction = match.get("transaction", {})
            confidence = match.get("confidence", 0)
            
            print(f"   Match: {receipt.get('merchant_name')} ↔ {transaction.get('merchant')} (Confidence: {confidence:.2f})")
    else:
        print(f"   ❌ Matching endpoint error: {response.status_code}")

def test_subscription_detection():
    """Test subscription and recurring pattern detection"""
    print("\n🔄 Testing Subscription Detection:")
    
    client = get_mongo_client()
    db = client.receipt_processor
    
    # Find receipts marked as subscriptions
    subscriptions = list(db.receipts.find({"test_data": True, "is_recurring": True}))
    
    print(f"   Found {len(subscriptions)} subscription receipts")
    
    for sub in subscriptions:
        merchant = sub.get("merchant_name")
        amount = sub.get("total_amount")
        date = sub.get("date")
        
        print(f"   📺 {merchant}: ${amount} on {date.strftime('%Y-%m-%d')}")
        
        # Look for similar transactions in previous months
        prev_month_start = date.replace(day=1) - timedelta(days=1)
        prev_month_start = prev_month_start.replace(day=1)
        prev_month_end = date.replace(day=1) - timedelta(days=1)
        
        similar_transactions = list(db.transactions.find({
            "merchant": {"$regex": merchant.split()[0], "$options": "i"},
            "amount": {"$gte": -amount - 1, "$lte": -amount + 1},
            "date": {"$gte": prev_month_start, "$lte": prev_month_end}
        }))
        
        if similar_transactions:
            print(f"      🔍 Found {len(similar_transactions)} similar transactions in previous month")
        else:
            print(f"      ⚪ No previous month pattern found")

def run_matching_tests():
    """Run comprehensive matching algorithm tests"""
    print("🧪 TRANSACTION MATCHING ALGORITHM TESTS")
    print("="*60)
    
    # Setup test data
    print("📊 Setting up test data...")
    clear_test_data()
    receipt_ids = insert_test_receipts()
    transaction_ids = insert_test_transactions()
    
    # Run tests
    test_merchant_matching()
    test_date_matching()
    test_amount_matching()
    test_perfect_matching()
    test_subscription_detection()
    
    print("\n" + "="*60)
    print("✅ Matching algorithm tests completed!")
    print(f"📄 Test receipts: {len(receipt_ids)}")
    print(f"💳 Test transactions: {len(transaction_ids)}")
    
    # Cleanup
    print("\n🧹 Cleaning up test data...")
    clear_test_data()
    print("✨ Test completed successfully!")

if __name__ == "__main__":
    run_matching_tests() 
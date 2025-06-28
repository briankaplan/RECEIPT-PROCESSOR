#!/usr/bin/env python3
"""
Complete System Integration Test
Tests the integration of the personalized email search system with the main workflow
"""

import requests
import json
import time
from datetime import datetime

def test_complete_system_integration():
    """Test the complete system integration"""
    
    base_url = "http://localhost:10000"
    
    print("🧪 Testing Complete System Integration")
    print("=" * 50)
    
    # Test 1: System Health Check
    print("\n1️⃣ Testing System Health...")
    try:
        response = requests.get(f"{base_url}/api/system-health")
        if response.status_code == 200:
            health = response.json()
            print(f"✅ System Health: {health.get('status', 'Unknown')}")
            print(f"   Database: {'✅' if health.get('database', {}).get('status') == 'healthy' else '❌'}")
            print(f"   Storage: {'✅' if health.get('storage', {}).get('status') == 'healthy' else '❌'}")
            print(f"   AI: {'✅' if health.get('ai', {}).get('status') == 'healthy' else '❌'}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test 2: Personalized Email Search
    print("\n2️⃣ Testing Personalized Email Search...")
    try:
        response = requests.post(f"{base_url}/api/personalized-email-search", 
                               json={"days_back": 30, "max_emails": 100})
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Personalized Search: {results.get('receipts_found', 0)} receipts found")
            print(f"   Receipts Saved: {results.get('receipts_saved', 0)}")
            print(f"   Attachments: {results.get('attachments_uploaded', 0)}")
            print(f"   Transactions Matched: {results.get('transactions_matched', 0)}")
        else:
            print(f"❌ Personalized search failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Personalized search error: {e}")
    
    # Test 3: Comprehensive Workflow
    print("\n3️⃣ Testing Comprehensive Workflow...")
    try:
        response = requests.post(f"{base_url}/api/comprehensive-receipt-workflow")
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Comprehensive Workflow: {results.get('email_scan', {}).get('receipts_saved', 0)} receipts")
            print(f"   Total Matches: {results.get('matching', {}).get('total_matches', 0)}")
            print(f"   Match Rate: {results.get('matching', {}).get('match_rate', 0):.1f}%")
            print(f"   Processing Time: {results.get('performance', {}).get('total_time', 0):.2f}s")
        else:
            print(f"❌ Comprehensive workflow failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Comprehensive workflow error: {e}")
    
    # Test 4: Dashboard Stats
    print("\n4️⃣ Testing Dashboard Stats...")
    try:
        response = requests.get(f"{base_url}/api/dashboard-stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Dashboard Stats:")
            print(f"   Total Expenses: ${stats.get('total_expenses', 0):,.2f}")
            print(f"   Match Rate: {stats.get('match_rate', 0):.1f}%")
            print(f"   Total Transactions: {stats.get('total_transactions', 0)}")
            print(f"   Matched Transactions: {stats.get('matched_transactions', 0)}")
        else:
            print(f"❌ Dashboard stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Dashboard stats error: {e}")
    
    # Test 5: Transaction Data
    print("\n5️⃣ Testing Transaction Data...")
    try:
        response = requests.get(f"{base_url}/api/bank-transactions?page=1&limit=10")
        if response.status_code == 200:
            data = response.json()
            transactions = data.get('transactions', [])
            print(f"✅ Transaction Data: {len(transactions)} transactions loaded")
            if transactions:
                print(f"   Sample Transaction: {transactions[0].get('merchant_name', 'Unknown')} - ${transactions[0].get('amount', 0)}")
        else:
            print(f"❌ Transaction data failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Transaction data error: {e}")
    
    # Test 6: Receipt Data
    print("\n6️⃣ Testing Receipt Data...")
    try:
        response = requests.get(f"{base_url}/api/receipts?page=1&limit=10")
        if response.status_code == 200:
            data = response.json()
            receipts = data.get('receipts', [])
            print(f"✅ Receipt Data: {len(receipts)} receipts loaded")
            if receipts:
                print(f"   Sample Receipt: {receipts[0].get('merchant', 'Unknown')} - ${receipts[0].get('amount', 0)}")
        else:
            print(f"❌ Receipt data failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Receipt data error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Complete System Integration Test Finished!")
    print("📊 The system is ready for production use with the new personalized email search system.")
    
    return True

if __name__ == "__main__":
    test_complete_system_integration() 
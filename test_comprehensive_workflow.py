#!/usr/bin/env python3
"""
Test script for the comprehensive receipt workflow
"""

import requests
import json
import time

def test_comprehensive_workflow():
    """Test the comprehensive receipt workflow endpoint"""
    
    print("🚀 Testing Comprehensive Receipt Workflow...")
    print("=" * 50)
    
    # Test the endpoint
    url = "http://localhost:10000/api/comprehensive-receipt-workflow"
    
    try:
        print("📡 Making request to comprehensive workflow endpoint...")
        start_time = time.time()
        
        response = requests.post(url, 
                               headers={'Content-Type': 'application/json'},
                               timeout=300)  # 5 minute timeout
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  Request completed in {duration:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print("✅ Workflow completed successfully!")
                print("\n📊 Results Summary:")
                print(f"   📧 Email Scan:")
                print(f"      - Receipts Found: {data['email_scan']['receipts_found']}")
                print(f"      - Receipts Saved: {data['email_scan']['receipts_saved']}")
                print(f"      - Attachments Uploaded: {data['email_scan']['attachments_uploaded']}")
                
                print(f"\n   🎯 Matching:")
                print(f"      - Total Matches: {data['matching']['total_matches']}")
                print(f"      - Exact Matches: {data['matching']['exact_matches']}")
                print(f"      - Fuzzy Matches: {data['matching']['fuzzy_matches']}")
                print(f"      - AI Matches: {data['matching']['ai_matches']}")
                print(f"      - Match Rate: {data['matching']['match_rate']:.1f}%")
                
                print(f"\n   💾 Database Updates:")
                print(f"      - Transactions Updated: {data['database_updates']['transactions_updated']}")
                print(f"      - Stats Refreshed: {data['database_updates']['stats_refreshed']}")
                
                print(f"\n   ⚡ Performance:")
                print(f"      - Total Time: {data['performance']['total_time']:.2f}s")
                print(f"      - Email Scan Time: {data['performance']['email_scan_time']:.2f}s")
                print(f"      - Matching Time: {data['performance']['matching_time']:.2f}s")
                
                if data['email_scan']['errors']:
                    print(f"\n   ⚠️  Errors ({len(data['email_scan']['errors'])}):")
                    for error in data['email_scan']['errors'][:3]:  # Show first 3 errors
                        print(f"      - {error}")
                
                return True
            else:
                print(f"❌ Workflow failed: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (5 minutes)")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - make sure the server is running on localhost:10000")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_dashboard_stats():
    """Test that dashboard stats are updated after workflow"""
    
    print("\n📊 Testing Dashboard Stats Update...")
    print("=" * 50)
    
    url = "http://localhost:10000/api/dashboard-stats"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                stats = data['stats']
                print("✅ Dashboard stats retrieved successfully!")
                print(f"   📈 Total Expenses: ${stats['total_expenses']:,.2f}")
                print(f"   📊 Total Transactions: {stats['total_transactions']}")
                print(f"   🎯 Match Rate: {stats['match_rate']}%")
                print(f"   🤖 AI Processed: {stats['ai_processed']}")
                print(f"   ✅ Matched Transactions: {stats['matched_transactions']}")
                print(f"   ⚠️  Missing Receipts: {stats['missing_receipts']}")
                return True
            else:
                print(f"❌ Dashboard stats failed: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Dashboard stats error: {e}")
        return False

def main():
    """Run all tests"""
    
    print("🧪 Comprehensive Receipt Workflow Test Suite")
    print("=" * 60)
    
    # Test 1: Comprehensive Workflow
    workflow_success = test_comprehensive_workflow()
    
    # Test 2: Dashboard Stats
    stats_success = test_dashboard_stats()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"   🚀 Comprehensive Workflow: {'✅ PASS' if workflow_success else '❌ FAIL'}")
    print(f"   📊 Dashboard Stats: {'✅ PASS' if stats_success else '❌ FAIL'}")
    
    if workflow_success and stats_success:
        print("\n🎉 All tests passed! The comprehensive workflow is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the server logs for more details.")
    
    print("\n💡 Next Steps:")
    print("   1. Check the web interface at http://localhost:10000")
    print("   2. Click the '🚀 Complete Workflow' button to run it manually")
    print("   3. Verify that transactions and receipts are properly matched")
    print("   4. Check that dashboard stats are updated")

if __name__ == "__main__":
    main()

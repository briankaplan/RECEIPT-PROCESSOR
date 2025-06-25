#!/usr/bin/env python3
"""
Test script to verify the fixed endpoints work correctly
"""

import requests
import time

def test_endpoints():
    """Test the fixed endpoints"""
    print("🧪 Testing Fixed Endpoints")
    print("=" * 50)
    
    # Start the Flask app in the background (you'll need to do this manually)
    base_url = "http://localhost:10000"
    
    # Test connection-stats endpoint
    print("\n📊 Testing /api/connection-stats")
    try:
        response = requests.get(f"{base_url}/api/connection-stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Connection stats endpoint working!")
            print(f"   Connected accounts: {data.get('connected_accounts', 0)}")
            print(f"   Total transactions: {data.get('total_transactions', 0)}")
            print(f"   Status: {data.get('status', 'Unknown')}")
            print(f"   MongoDB connected: {data.get('mongo_connected', False)}")
        else:
            print(f"❌ Connection stats failed with status {response.status_code}")
            print(f"   Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print("⚠️ Could not connect to Flask app. Make sure it's running on port 10000")
    except Exception as e:
        print(f"❌ Connection stats error: {e}")
    
    # Test teller-environment endpoint
    print("\n🏦 Testing /api/teller-environment")
    try:
        response = requests.get(f"{base_url}/api/teller-environment", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Teller environment endpoint working!")
            print(f"   Environment: {data.get('environment', 'Unknown')}")
            print(f"   Connected: {data.get('connected', False)}")
            print(f"   Success: {data.get('success', False)}")
        else:
            print(f"❌ Teller environment failed with status {response.status_code}")
            print(f"   Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print("⚠️ Could not connect to Flask app. Make sure it's running on port 10000")
    except Exception as e:
        print(f"❌ Teller environment error: {e}")
    
    print("\n📋 Summary:")
    print("To test these endpoints:")
    print("1. Start your Flask app: python app.py")
    print("2. In another terminal, run: python test_endpoints.py")
    print("3. Or test manually:")
    print(f"   - GET {base_url}/api/connection-stats")
    print(f"   - GET {base_url}/api/teller-environment")

if __name__ == "__main__":
    test_endpoints() 
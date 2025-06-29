#!/usr/bin/env python3
"""
Test script for authentication flow
"""

import requests
import json
import time

BASE_URL = "http://localhost:10000"

def test_registration():
    """Test user registration"""
    print("🔐 Testing Registration Flow...")
    
    # Test data
    test_user = {
        "username": f"demo_user_{int(time.time())}",
        "email": f"demo_{int(time.time())}@example.com",
        "password": "demo123pass"
    }
    
    print(f"📝 Registering user: {test_user['username']}")
    
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        headers={"Content-Type": "application/json"},
        json=test_user
    )
    
    print(f"📊 Response Status: {response.status_code}")
    print(f"📄 Response: {response.json()}")
    
    if response.status_code == 201:
        print("✅ Registration successful!")
        return test_user
    else:
        print("❌ Registration failed!")
        return None

def test_login(username, password):
    """Test user login"""
    print(f"\n🔑 Testing Login Flow for user: {username}")
    
    login_data = {
        "username": username,
        "password": password
    }
    
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        headers={"Content-Type": "application/json"},
        json=login_data
    )
    
    print(f"📊 Response Status: {response.status_code}")
    result = response.json()
    
    if response.status_code == 200:
        print("✅ Login successful!")
        print(f"🎫 Access Token: {result['tokens']['access_token'][:50]}...")
        print(f"🔄 Refresh Token: {result['tokens']['refresh_token'][:50]}...")
        return result['tokens']
    else:
        print("❌ Login failed!")
        print(f"📄 Error: {result}")
        return None

def main():
    """Run the complete authentication flow test"""
    print("🚀 Starting Authentication Flow Test")
    print("=" * 50)
    
    # Test registration
    user = test_registration()
    if not user:
        print("❌ Cannot proceed without successful registration")
        return
    
    # Test login
    tokens = test_login(user['username'], user['password'])
    if not tokens:
        print("❌ Cannot proceed without successful login")
        return
    
    print("\n" + "=" * 50)
    print("🎉 Authentication Flow Test Complete!")
    print(f"👤 Test User: {user['username']}")
    print(f"📧 Email: {user['email']}")

if __name__ == "__main__":
    main() 
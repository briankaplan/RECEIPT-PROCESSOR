#!/usr/bin/env python3
"""
🔐 Render Certificate Testing & Diagnostics
Tests certificate configuration on Render deployment
"""

import requests
import json
import time
from datetime import datetime

# Configuration
RENDER_URL = "https://receipt-processor.onrender.com"
TEST_TIMEOUT = 30  # seconds

def test_health_endpoint():
    """Test basic app health"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{RENDER_URL}/health", timeout=TEST_TIMEOUT)
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print("⏰ Health check timed out - app may be slow to start")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_certificate_debug():
    """Test certificate debugging endpoint"""
    print("\n🔐 Testing certificate debug endpoint...")
    try:
        response = requests.post(f"{RENDER_URL}/api/debug-certificates", timeout=TEST_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Certificate debug endpoint responded")
            
            if data.get('success'):
                debug_info = data.get('debug_info', {})
                
                # Certificate paths
                cert_paths = debug_info.get('certificate_paths', {})
                print(f"\n📂 Certificate Paths:")
                print(f"   Cert Path: {cert_paths.get('cert_path')}")
                print(f"   Key Path: {cert_paths.get('key_path')}")
                print(f"   Cert Exists: {cert_paths.get('cert_exists')}")
                print(f"   Key Exists: {cert_paths.get('key_exists')}")
                
                # File inspection
                file_inspection = debug_info.get('file_inspection', {})
                
                if 'certificate' in file_inspection:
                    cert_info = file_inspection['certificate']
                    if 'error' in cert_info:
                        print(f"❌ Certificate file error: {cert_info['error']}")
                    else:
                        print(f"\n📜 Certificate File Analysis:")
                        print(f"   Size: {cert_info.get('size_bytes')} bytes")
                        print(f"   Starts with PEM: {cert_info.get('starts_with_pem')}")
                        print(f"   Contains cert marker: {cert_info.get('contains_certificate_marker')}")
                        print(f"   Line count: {cert_info.get('line_count')}")
                        print(f"   Preview: {cert_info.get('first_50_chars')}")
                
                if 'private_key' in file_inspection:
                    key_info = file_inspection['private_key']
                    if 'error' in key_info:
                        print(f"❌ Private key file error: {key_info['error']}")
                    else:
                        print(f"\n🔑 Private Key File Analysis:")
                        print(f"   Size: {key_info.get('size_bytes')} bytes")
                        print(f"   Starts with PEM: {key_info.get('starts_with_pem')}")
                        print(f"   Contains key marker: {key_info.get('contains_key_marker')}")
                        print(f"   Line count: {key_info.get('line_count')}")
                        print(f"   Preview: {key_info.get('first_50_chars')}")
                
                return True
            else:
                print(f"❌ Certificate debug failed: {data}")
                return False
        else:
            print(f"❌ Certificate debug endpoint error: {response.status_code}")
            try:
                print(f"Response: {response.text[:500]}")
            except:
                pass
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ Certificate debug timed out")
        return False
    except Exception as e:
        print(f"❌ Certificate debug error: {e}")
        return False

def test_status_endpoint():
    """Test detailed status endpoint"""
    print("\n📊 Testing status endpoint...")
    try:
        response = requests.get(f"{RENDER_URL}/status", timeout=TEST_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Status endpoint responded")
            
            # Check services
            services = data.get('services', {})
            for service, status in services.items():
                print(f"   {service}: {status}")
            
            # Check Teller integration
            teller_info = data.get('teller', {})
            print(f"\n🏦 Teller Integration:")
            print(f"   Environment: {teller_info.get('environment')}")
            print(f"   App ID: {teller_info.get('application_id')}")
            print(f"   Webhook URL: {teller_info.get('webhook_url')}")
            
            return True
        else:
            print(f"❌ Status endpoint error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Status endpoint error: {e}")
        return False

def test_bank_sync():
    """Test bank synchronization"""
    print("\n🏦 Testing bank transaction sync...")
    try:
        response = requests.post(f"{RENDER_URL}/api/sync-bank-transactions", timeout=TEST_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Bank sync responded: {data.get('message', 'Success')}")
            
            if 'certificate_status' in data:
                cert_status = data['certificate_status']
                print(f"🔐 Certificate Status: {cert_status}")
            
            return True
        else:
            print(f"❌ Bank sync error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Response text: {response.text[:300]}")
            return False
            
    except Exception as e:
        print(f"❌ Bank sync error: {e}")
        return False

def main():
    """Run comprehensive certificate testing"""
    print("🚀 Starting Render Certificate Testing")
    print(f"🌐 Target URL: {RENDER_URL}")
    print(f"⏰ Timeout: {TEST_TIMEOUT}s")
    print("=" * 60)
    
    # Run all tests
    tests = [
        ("Health Check", test_health_endpoint),
        ("Certificate Debug", test_certificate_debug),
        ("Status Check", test_status_endpoint),
        ("Bank Sync Test", test_bank_sync)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 40)
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
        
        # Small delay between tests
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Certificate configuration looks good.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("\n🔧 Common solutions:")
        print("   1. Verify certificates are uploaded to Render Secret Files")
        print("   2. Check file names: teller_certificate.b64, teller_private_key.b64")
        print("   3. Ensure base64 content is properly formatted")
        print("   4. Verify webhook URL is correct")

if __name__ == "__main__":
    main() 
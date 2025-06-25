#!/usr/bin/env python3
"""
Test script to verify local certificate configuration
"""

import os
import base64
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import Config, load_certificate_files_fixed, enhanced_bank_sync_with_certificates

def test_certificate_files():
    """Test that certificate files exist and are valid"""
    print("🔐 Testing Certificate Configuration")
    print("=" * 50)
    
    # Check certificate paths - use .b64 files for security
    cert_path = "./credentials/teller_certificate.b64"
    key_path = "./credentials/teller_private_key.b64"
    
    print(f"Certificate path: {cert_path}")
    print(f"Private key path: {key_path}")
    print()
    
    # Check if files exist
    cert_exists = os.path.exists(cert_path)
    key_exists = os.path.exists(key_path)
    
    print(f"Certificate file exists: {'✅' if cert_exists else '❌'}")
    print(f"Private key file exists: {'✅' if key_exists else '❌'}")
    print()
    
    if not cert_exists or not key_exists:
        print("❌ Certificate files not found!")
        return False
    
    # Test loading certificates
    print("🔄 Testing certificate loading...")
    cert_temp_path, key_temp_path = load_certificate_files_fixed(cert_path, key_path)
    
    if cert_temp_path and key_temp_path:
        print("✅ Certificates loaded successfully!")
        print(f"Temp cert path: {cert_temp_path}")
        print(f"Temp key path: {key_temp_path}")
        
        # Clean up temp files
        try:
            os.unlink(cert_temp_path)
            os.unlink(key_temp_path)
            print("🧹 Cleaned up temporary files")
        except:
            pass
        
        return True
    else:
        print("❌ Failed to load certificates!")
        return False

def test_bank_sync():
    """Test the enhanced bank sync function"""
    print("\n🏦 Testing Bank Sync Function")
    print("=" * 50)
    
    result = enhanced_bank_sync_with_certificates()
    
    print(f"Success: {result.get('success', False)}")
    if 'error' in result:
        print(f"Error: {result['error']}")
    if 'message' in result:
        print(f"Message: {result['message']}")
    if 'debug_info' in result:
        print("Debug info:")
        for key, value in result['debug_info'].items():
            print(f"  {key}: {value}")
    
    return result.get('success', False)

def test_environment():
    """Test environment configuration"""
    print("\n🌍 Testing Environment Configuration")
    print("=" * 50)
    
    print(f"Teller Environment: {Config.TELLER_ENVIRONMENT}")
    print(f"Teller App ID: {Config.TELLER_APPLICATION_ID}")
    print(f"Teller API URL: {Config.TELLER_API_URL}")
    print(f"Teller Webhook URL: {Config.TELLER_WEBHOOK_URL}")
    print(f"Teller Cert Path: {Config.TELLER_CERT_PATH}")
    print(f"Teller Key Path: {Config.TELLER_KEY_PATH}")
    print()
    
    # Check if we're in development mode (required for real banking)
    if Config.TELLER_ENVIRONMENT == 'development':
        print("✅ Environment set to 'development' - ready for real banking data")
    else:
        print("⚠️ Environment not set to 'development' - may be in sandbox mode")
    
    return Config.TELLER_ENVIRONMENT == 'development'

def main():
    """Run all tests"""
    print("🚀 Certificate and Environment Test Suite")
    print("=" * 60)
    
    # Test environment
    env_ok = test_environment()
    
    # Test certificate files
    cert_ok = test_certificate_files()
    
    # Test bank sync
    sync_ok = test_bank_sync()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    print(f"Environment: {'✅' if env_ok else '❌'}")
    print(f"Certificates: {'✅' if cert_ok else '❌'}")
    print(f"Bank Sync: {'✅' if sync_ok else '❌'}")
    
    if env_ok and cert_ok:
        print("\n🎉 Setup looks good! You can now:")
        print("1. Start your Flask app: python app.py")
        print("2. Access via ngrok: https://2e1d-69-130-149-204.ngrok-free.app")
        print("3. Connect to Chase via Teller")
    else:
        print("\n⚠️ Some issues detected. Please check the errors above.")

if __name__ == "__main__":
    main() 
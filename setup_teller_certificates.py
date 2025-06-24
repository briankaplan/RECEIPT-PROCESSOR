#!/usr/bin/env python3
"""
Teller Certificate Configuration Script
Helps set up SSL client certificates for Teller Banking API
"""

import os
import requests
import json
from pathlib import Path

def main():
    print("🔐 Teller Certificate Configuration")
    print("=" * 50)
    
    # Check current configuration
    print("\n📋 Current Configuration:")
    print(f"   TELLER_APPLICATION_ID: {os.getenv('TELLER_APPLICATION_ID', 'Not set')}")
    print(f"   TELLER_ENVIRONMENT: {os.getenv('TELLER_ENVIRONMENT', 'Not set')}")
    print(f"   TELLER_CERT_PATH: {os.getenv('TELLER_CERT_PATH', 'Not set')}")
    print(f"   TELLER_KEY_PATH: {os.getenv('TELLER_KEY_PATH', 'Not set')}")
    
    # Check for certificate files
    cert_path = os.getenv('TELLER_CERT_PATH', './credentials/teller_certificate.pem')
    key_path = os.getenv('TELLER_KEY_PATH', './credentials/teller_private_key.pem')
    
    print(f"\n📁 Certificate Files:")
    print(f"   Certificate: {cert_path} {'✅' if os.path.exists(cert_path) else '❌'}")
    print(f"   Private Key: {key_path} {'✅' if os.path.exists(key_path) else '❌'}")
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print("\n🚨 MISSING CERTIFICATES!")
        print("\nTo obtain Teller client certificates:")
        print("1. 📧 Contact Teller Support: support@teller.io")
        print("2. 📝 Request SSL client certificates for your application ID")
        print("3. 📎 Include your application ID: app_pbvpiocruhfnvkhf1k000")
        print("4. 💼 Mention you need certificates for development tier API access")
        print("5. 📥 They will send you two files:")
        print("   - teller_certificate.pem (public certificate)")
        print("   - teller_private_key.pem (private key)")
        
        print("\n💡 Alternative Options:")
        print("1. Use Sandbox Mode (no certificates needed, but fake data)")
        print("2. Use Webhook-only approach (real-time notifications)")
        
        # Create placeholder certificate files for development
        credentials_dir = Path('./credentials')
        credentials_dir.mkdir(exist_ok=True)
        
        placeholder_cert = """-----BEGIN CERTIFICATE-----
# PLACEHOLDER CERTIFICATE
# Replace this with your actual Teller client certificate
# Contact support@teller.io to obtain your certificates
-----END CERTIFICATE-----"""
        
        placeholder_key = """-----BEGIN PRIVATE KEY-----
# PLACEHOLDER PRIVATE KEY  
# Replace this with your actual Teller private key
# Contact support@teller.io to obtain your certificates
-----END PRIVATE KEY-----"""
        
        with open(cert_path, 'w') as f:
            f.write(placeholder_cert)
        print(f"✅ Created placeholder certificate: {cert_path}")
        
        with open(key_path, 'w') as f:
            f.write(placeholder_key)
        print(f"✅ Created placeholder private key: {key_path}")
        
        # Set secure permissions
        os.chmod(cert_path, 0o600)
        os.chmod(key_path, 0o600)
        print("🔒 Set secure file permissions (600)")
        
    else:
        print("✅ Certificate files found!")
        
        # Test certificate validity (basic check)
        try:
            with open(cert_path, 'r') as f:
                cert_content = f.read()
                if 'BEGIN CERTIFICATE' in cert_content and 'END CERTIFICATE' in cert_content:
                    print("✅ Certificate file appears valid")
                else:
                    print("⚠️ Certificate file may be invalid")
                    
            with open(key_path, 'r') as f:
                key_content = f.read()
                if 'BEGIN PRIVATE KEY' in key_content and 'END PRIVATE KEY' in key_content:
                    print("✅ Private key file appears valid")
                else:
                    print("⚠️ Private key file may be invalid")
                    
        except Exception as e:
            print(f"❌ Error reading certificate files: {e}")
    
    # Show next steps
    print("\n🚀 Next Steps:")
    print("1. If using development mode:")
    print("   - Obtain real certificates from Teller support")
    print("   - Replace placeholder files with real certificates")
    print("   - Restart your application")
    print("\n2. If using sandbox mode:")
    print("   - Change TELLER_ENVIRONMENT to 'sandbox' in render.yaml")
    print("   - No certificates needed (but fake transaction data)")
    print("\n3. For production:")
    print("   - Upload certificates to Render.com secret files")
    print("   - Ensure paths match environment variables")

if __name__ == "__main__":
    main() 
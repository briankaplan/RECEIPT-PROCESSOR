#!/usr/bin/env python3
"""
Test and fix Teller certificate base64 decoding
"""

import base64
import os
import tempfile

def test_certificate_decoding():
    """Test certificate decoding and fix padding issues"""
    
    print("🔐 Testing Teller Certificate Decoding")
    print("=" * 50)
    
    # Check certificate files
    cert_path = './credentials/teller_certificate.b64'
    key_path = './credentials/teller_private_key.b64'
    
    if not os.path.exists(cert_path):
        print(f"❌ Certificate file not found: {cert_path}")
        return False
    
    if not os.path.exists(key_path):
        print(f"❌ Private key file not found: {key_path}")
        return False
    
    print(f"✅ Certificate file found: {cert_path}")
    print(f"✅ Private key file found: {key_path}")
    
    try:
        # Read certificate
        with open(cert_path, 'r') as f:
            cert_b64 = f.read().strip()
        
        print(f"Certificate base64 length: {len(cert_b64)}")
        print(f"Certificate base64 ends with: {cert_b64[-10:]}")
        
        # Check if padding is needed
        missing_padding = len(cert_b64) % 4
        if missing_padding:
            print(f"⚠️ Adding {missing_padding} padding characters to certificate")
            cert_b64 += '=' * (4 - missing_padding)
        
        # Decode certificate
        cert_pem = base64.b64decode(cert_b64).decode('utf-8')
        print(f"✅ Certificate decoded successfully ({len(cert_pem)} characters)")
        
        # Read private key
        with open(key_path, 'r') as f:
            key_b64 = f.read().strip()
        
        print(f"Private key base64 length: {len(key_b64)}")
        print(f"Private key base64 ends with: {key_b64[-10:]}")
        
        # Check if padding is needed
        missing_padding = len(key_b64) % 4
        if missing_padding:
            print(f"⚠️ Adding {missing_padding} padding characters to private key")
            key_b64 += '=' * (4 - missing_padding)
        
        # Decode private key
        key_pem = base64.b64decode(key_b64).decode('utf-8')
        print(f"✅ Private key decoded successfully ({len(key_pem)} characters)")
        
        # Create temporary files
        cert_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
        key_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
        
        cert_file.write(cert_pem)
        key_file.write(key_pem)
        
        cert_file.close()
        key_file.close()
        
        # Set permissions
        os.chmod(cert_file.name, 0o600)
        os.chmod(key_file.name, 0o600)
        
        print(f"✅ Temporary certificate file: {cert_file.name}")
        print(f"✅ Temporary private key file: {key_file.name}")
        
        # Test the certificate files
        cert_files = (cert_file.name, key_file.name)
        print(f"✅ Certificate files ready: {cert_files}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error decoding certificates: {e}")
        return False

def fix_certificate_files():
    """Fix certificate files by ensuring proper base64 padding"""
    
    print("\n🔧 Fixing Certificate Files")
    print("=" * 40)
    
    cert_path = './credentials/teller_certificate.b64'
    key_path = './credentials/teller_private_key.b64'
    
    try:
        # Fix certificate
        with open(cert_path, 'r') as f:
            cert_b64 = f.read().strip()
        
        missing_padding = len(cert_b64) % 4
        if missing_padding:
            print(f"Adding {missing_padding} padding characters to certificate")
            cert_b64 += '=' * (4 - missing_padding)
            
            with open(cert_path, 'w') as f:
                f.write(cert_b64)
            print("✅ Certificate file fixed")
        
        # Fix private key
        with open(key_path, 'r') as f:
            key_b64 = f.read().strip()
        
        missing_padding = len(key_b64) % 4
        if missing_padding:
            print(f"Adding {missing_padding} padding characters to private key")
            key_b64 += '=' * (4 - missing_padding)
            
            with open(key_path, 'w') as f:
                f.write(key_b64)
            print("✅ Private key file fixed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing certificate files: {e}")
        return False

if __name__ == "__main__":
    print("Testing certificate decoding...")
    success = test_certificate_decoding()
    
    if not success:
        print("\nAttempting to fix certificate files...")
        fix_certificate_files()
        print("\nTesting again after fix...")
        test_certificate_decoding() 
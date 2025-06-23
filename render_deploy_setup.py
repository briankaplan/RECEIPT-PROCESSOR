#!/usr/bin/env python3
"""
Render.com Deployment Setup Script
Fixes OAuth redirects and prepares all necessary configurations
"""

import os
import json
import shutil
from pathlib import Path

# Render.com deployment configuration
RENDER_URL = "https://receipt-processor.onrender.com"
RENDER_SECRET_FILES = {
    # Gmail OAuth tokens
    'kaplan_brian_gmail.pickle': './gmail_tokens/kaplan_brian_gmail.pickle',
    'brian_downhome.pickle': './gmail_tokens/brian_downhome.pickle', 
    'brian_musiccityrodeo.pickle': './gmail_tokens/brian_musiccityrodeo.pickle',
    
    # Google API credentials
    'gmail_credentials.json': './credentials/gmail_credentials.json',
    'service_account.json': './credentials/service_account.json',
    
    # Teller SSL certificates
    'teller_certificate.pem': './credentials/teller_certificate.pem',
    'teller_private_key.pem': './credentials/teller_private_key.pem'
}

def check_oauth_redirects():
    """Verify OAuth redirect URIs are configured for render.com"""
    print("🔐 Checking OAuth Redirect URIs...")
    
    required_redirects = [
        f"{RENDER_URL}/gmail/oauth/callback",
        f"{RENDER_URL}/auth/google/callback", 
        f"{RENDER_URL}/teller/callback",
        "https://receipt-processor.onrender.com/oauth2callback"
    ]
    
    print("📋 Required OAuth Redirect URIs for Google Cloud Console:")
    for redirect in required_redirects:
        print(f"   ✅ {redirect}")
    
    print("\n⚠️  IMPORTANT: Add these URLs to your Google Cloud Console:")
    print("   1. Go to https://console.cloud.google.com/apis/credentials")
    print("   2. Edit your OAuth 2.0 Client ID")
    print("   3. Add all the above URLs to 'Authorized redirect URIs'")
    print("   4. Save changes\n")

def update_gmail_credentials():
    """Update Gmail credentials with proper redirect URIs"""
    creds_file = './credentials/gmail_credentials.json'
    
    if not os.path.exists(creds_file):
        print(f"❌ Gmail credentials not found: {creds_file}")
        return False
    
    try:
        with open(creds_file, 'r') as f:
            creds = json.load(f)
        
        # Add render.com redirect URIs
        if 'installed' in creds:
            redirect_uris = creds['installed'].get('redirect_uris', [])
            new_redirects = [
                f"{RENDER_URL}/oauth2callback",
                f"{RENDER_URL}/gmail/oauth/callback"
            ]
            
            for redirect in new_redirects:
                if redirect not in redirect_uris:
                    redirect_uris.append(redirect)
            
            creds['installed']['redirect_uris'] = redirect_uris
            
            # Save updated credentials
            with open(creds_file, 'w') as f:
                json.dump(creds, f, indent=2)
            
            print("✅ Gmail credentials updated with render.com redirect URIs")
            return True
    
    except Exception as e:
        print(f"❌ Failed to update Gmail credentials: {e}")
        return False

def prepare_render_secrets():
    """Prepare secret files for Render deployment"""
    print("📁 Preparing secret files for Render...")
    
    # Create render_secrets directory
    secrets_dir = Path('./render_secrets')
    secrets_dir.mkdir(exist_ok=True)
    
    missing_files = []
    
    for render_name, local_path in RENDER_SECRET_FILES.items():
        if os.path.exists(local_path):
            shutil.copy2(local_path, secrets_dir / render_name)
            print(f"   ✅ {render_name}")
        else:
            missing_files.append(local_path)
            print(f"   ❌ Missing: {local_path}")
    
    if missing_files:
        print(f"\n⚠️  Missing {len(missing_files)} required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print(f"\n✅ All {len(RENDER_SECRET_FILES)} secret files prepared")
    return True

def create_render_instructions():
    """Generate deployment instructions for Render"""
    instructions = f"""
# 🚀 Render.com Deployment Instructions

## 1. Upload Secret Files

In your Render dashboard, go to your service and upload these files to "Secret Files":

"""
    
    for render_name, local_path in RENDER_SECRET_FILES.items():
        instructions += f"- `{render_name}` (from ./render_secrets/{render_name})\n"
    
    instructions += f"""

## 2. Environment Variables

All environment variables are already configured in render.yaml.

## 3. OAuth Configuration

### Google Cloud Console:
1. Go to https://console.cloud.google.com/apis/credentials
2. Edit your OAuth 2.0 Client ID  
3. Add these Authorized redirect URIs:
   - {RENDER_URL}/oauth2callback
   - {RENDER_URL}/gmail/oauth/callback
   - {RENDER_URL}/auth/google/callback

### Teller Configuration:
1. Go to your Teller dashboard
2. Update redirect URI to: {RENDER_URL}/teller/callback
3. Update webhook URL to: {RENDER_URL}/teller/webhook

## 4. Deploy

1. Commit and push changes to GitHub
2. Render will auto-deploy from main branch
3. Check logs for any issues

## 5. Post-Deployment

1. Visit {RENDER_URL}/status to check service health
2. Test Gmail authentication at {RENDER_URL}/gmail/auth
3. Test Teller connection at {RENDER_URL}/connect

## 🔧 Troubleshooting

### Gmail Issues:
- Verify redirect URIs in Google Cloud Console
- Check that secret files are uploaded correctly
- Ensure GOOGLE_APPLICATION_CREDENTIALS points to /etc/secrets/service_account.json

### Teller Issues:
- Verify SSL certificates are uploaded as secret files
- Check TELLER_CERT_PATH and TELLER_KEY_PATH point to /etc/secrets/
- Ensure redirect URI matches exactly in Teller dashboard

### General Issues:
- Check Render logs for detailed error messages
- Verify all environment variables are set correctly
- Test with /status endpoint first
"""

    with open('./RENDER_DEPLOY_INSTRUCTIONS.md', 'w') as f:
        f.write(instructions)
    
    print("📝 Deployment instructions created: ./RENDER_DEPLOY_INSTRUCTIONS.md")

def main():
    """Main deployment setup"""
    print("🚀 Render.com Deployment Setup")
    print("=" * 50)
    
    # Step 1: Check OAuth redirects
    check_oauth_redirects()
    
    # Step 2: Update Gmail credentials
    update_gmail_credentials()
    
    # Step 3: Prepare secret files
    if not prepare_render_secrets():
        print("\n❌ Cannot proceed with missing files. Please ensure all credentials exist.")
        return False
    
    # Step 4: Create instructions
    create_render_instructions()
    
    print("\n" + "=" * 50)
    print("✅ Render deployment setup complete!")
    print("\nNEXT STEPS:")
    print("1. Read ./RENDER_DEPLOY_INSTRUCTIONS.md")
    print("2. Upload secret files to Render dashboard")
    print("3. Update OAuth redirect URIs in Google Cloud Console")
    print("4. Update Teller redirect URI and webhook URL")
    print("5. Deploy to Render")
    
    return True

if __name__ == '__main__':
    main() 
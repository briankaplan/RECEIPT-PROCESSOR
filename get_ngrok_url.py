#!/usr/bin/env python3
"""
Get ngrok URL helper script
Use this when automatic URL detection fails
"""

import requests
import time
import sys
import subprocess
import json

def check_ngrok_running():
    """Check if ngrok process is running"""
    try:
        result = subprocess.run(['pgrep', 'ngrok'], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def get_ngrok_url(max_retries=10):
    """Get ngrok URL with retries"""
    for i in range(max_retries):
        try:
            response = requests.get('http://localhost:4040/api/tunnels', timeout=2)
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get('tunnels', [])
                
                if tunnels:
                    for tunnel in tunnels:
                        if tunnel.get('proto') == 'https':
                            public_url = tunnel.get('public_url')
                            if public_url:
                                return public_url
                    
                    # If no https, try first tunnel
                    public_url = tunnels[0].get('public_url')
                    if public_url:
                        return public_url
                
                print(f"Attempt {i+1}: No tunnels found yet...")
            else:
                print(f"Attempt {i+1}: ngrok API returned status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"Attempt {i+1}: Connection failed - {e}")
        
        if i < max_retries - 1:
            time.sleep(2)
    
    return None

def start_ngrok():
    """Start ngrok if not running"""
    if not check_ngrok_running():
        print("🚀 Starting ngrok...")
        try:
            subprocess.Popen(['ngrok', 'http', '5000'], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            time.sleep(3)
        except Exception as e:
            print(f"❌ Failed to start ngrok: {e}")
            return False
    return True

def main():
    print("🔍 Getting ngrok URL...")
    
    # Check if ngrok is running, start if needed
    if not start_ngrok():
        return
    
    # Try to get URL
    url = get_ngrok_url()
    
    if url:
        print(f"✅ ngrok URL: {url}")
        print(f"🔗 Webhook URL: {url}/teller/webhook")
        print(f"🔗 OAuth callback: {url}/teller/callback")
        
        # Update .env file if it exists
        try:
            with open('.env', 'r') as f:
                content = f.read()
            
            # Update webhook URL
            content = content.replace(
                'TELLER_WEBHOOK_URL=http://localhost:5000/teller/webhook',
                f'TELLER_WEBHOOK_URL={url}/teller/webhook'
            )
            content = content.replace(
                'TELLER_WEBHOOK_URL=https://localhost:5000/teller/webhook',
                f'TELLER_WEBHOOK_URL={url}/teller/webhook'
            )
            
            with open('.env', 'w') as f:
                f.write(content)
            
            print("✅ Updated .env file with ngrok URL")
            
        except FileNotFoundError:
            print("⚠️  No .env file found - create one first")
        except Exception as e:
            print(f"⚠️  Couldn't update .env file: {e}")
            
        print("\n📋 Next steps:")
        print("1. Copy the webhook URL above")
        print("2. Go to your Teller dashboard")
        print("3. Update the Webhook URL field")
        print("4. Test the webhook")
        
    else:
        print("❌ Could not get ngrok URL")
        print("\n🔧 Manual steps:")
        print("1. Open http://localhost:4040 in your browser")
        print("2. Look for the 'Forwarding' URL (should be https://xxx.ngrok.io)")
        print("3. Copy that URL and add '/teller/webhook' to the end")
        print("4. Use that as your webhook URL in Teller dashboard")

if __name__ == '__main__':
    main() 
import argparse
import json
import os
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

def setup_clients_json():
    """Create clients.json template if it doesn't exist"""
    clients_path = Path("gmail_auth/clients.json")
    if not clients_path.exists():
        clients_path.parent.mkdir(exist_ok=True)
        template = {
            "your.email@gmail.com": {
                "web": {
                    "client_id": "your-client-id.apps.googleusercontent.com",
                    "project_id": "your-project-id",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": "your-client-secret",
                    "redirect_uris": ["http://localhost:8080"]
                }
            }
        }
        with open(clients_path, 'w') as f:
            json.dump(template, f, indent=2)
        print(f"📝 Created template: {clients_path}")
        print("📋 Please update with your OAuth credentials from Google Cloud Console")
        print("🔗 https://console.cloud.google.com/apis/credentials")
        return False
    return True

def list_accounts():
    """List available accounts in clients.json"""
    try:
        with open("gmail_auth/clients.json") as f:
            clients = json.load(f)
        print("📧 Available accounts:")
        for email in clients:
            print(f"   - {email}")
    except FileNotFoundError:
        print("❌ No clients.json found. Run: python auth_tool.py --setup")
    except json.JSONDecodeError:
        print("❌ Invalid clients.json format")

def authenticate(email):
    """Authenticate a specific email account and store refresh token + pickle"""
    try:
        with open("gmail_auth/clients.json") as f:
            clients = json.load(f)
    except FileNotFoundError:
        print("❌ clients.json not found. Run: python auth_tool.py --setup")
        return False

    # Special case for main Gmail account
    if email == "kaplan.brian@gmail.com" and "installed" in clients:
        client_config = clients["installed"]
        email = "kaplan.brian@gmail.com"  # Use the actual email for the pickle file
    elif email not in clients:
        print(f"❌ Email {email} not found in clients.json")
        print("📧 Available accounts:")
        for available_email in clients:
            if available_email != "installed":  # Don't show the installed key
                print(f"   - {available_email}")
        return False
    else:
        client_config = clients[email]

    # Handle both 'web' and 'installed' formats
    if "web" in client_config:
        oauth_config = client_config["web"]
    else:
        oauth_config = client_config

    redirect_uri = oauth_config["redirect_uris"][0]
    port = int(redirect_uri.split(":")[-1].rstrip("/"))

    print(f"🔐 Starting OAuth flow for {email} on port {port}...")
    print("🌐 Your browser should open automatically")

    flow = InstalledAppFlow.from_client_config({"web": oauth_config}, SCOPES)
    creds = flow.run_local_server(port=port, prompt='consent')

    if creds.refresh_token:
        # Save refresh token to tokens.json
        tokens_path = Path("gmail_auth/tokens.json")
        if tokens_path.exists():
            try:
                with open(tokens_path) as f:
                    tokens = json.load(f)
            except json.JSONDecodeError:
                tokens = {}
        else:
            tokens = {}
        tokens[email] = creds.refresh_token
        with open(tokens_path, "w") as f:
            json.dump(tokens, f, indent=2)

        # Save full credentials as a pickle
        pickle_dir = Path("gmail_tokens")
        pickle_dir.mkdir(exist_ok=True)
        pickle_path = pickle_dir / f"{email.replace('@', '_at_').replace('.', '_')}.pickle"
        with open(pickle_path, "wb") as token_file:
            pickle.dump(creds, token_file)

        print(f"✅ Successfully authenticated {email}")
        print(f"🥒 Saved credentials to: {pickle_path}")
        return True
    else:
        print("❌ No refresh token received. Check OAuth settings.")
        return False

def setup_auth_flow():
    """Authenticate all Gmail accounts from .env"""
    emails = [
        os.getenv("GMAIL_ACCOUNT_1_EMAIL"),
        os.getenv("GMAIL_ACCOUNT_2_EMAIL"),
        os.getenv("GMAIL_ACCOUNT_3_EMAIL")
    ]
    for email in emails:
        if email:
            print(f"\n📧 Authenticating {email}...")
            authenticate(email)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gmail Auth Tool")
    parser.add_argument("--setup", action="store_true", help="Authenticate all accounts from .env")
    parser.add_argument("--email", type=str, help="Authenticate specific Gmail account")
    parser.add_argument("--list", action="store_true", help="List accounts from clients.json")
    parser.add_argument("--all", action="store_true", help="Authenticate all from config.settings")

    args = parser.parse_args()

    if args.setup:
        setup_auth_flow()
    elif args.list:
        list_accounts()
    elif args.email:
        authenticate(args.email)
    elif args.all:
        try:
            from config.settings import GMAIL_ACCOUNTS
            success_count = 0
            for email in GMAIL_ACCOUNTS:
                if email:
                    print(f"\n📧 Authenticating {email}...")
                    if authenticate(email):
                        success_count += 1
            print(f"\n✅ Successfully authenticated {success_count}/{len(GMAIL_ACCOUNTS)} accounts")
        except ImportError:
            print("❌ Could not load email accounts from config")
    else:
        parser.print_help()
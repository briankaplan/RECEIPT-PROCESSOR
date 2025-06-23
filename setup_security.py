#!/usr/bin/env python3
"""
Security Setup Script for Receipt Processor
This script helps set up the application securely by creating necessary directories
and checking for proper configuration.
"""

import os
import stat
import sys
from pathlib import Path

def create_directory(path, mode=0o755):
    """Create directory with proper permissions"""
    Path(path).mkdir(mode=mode, parents=True, exist_ok=True)
    print(f"✅ Created directory: {path}")

def check_env_file():
    """Check if .env file exists and warn if not"""
    if not os.path.exists('.env'):
        print("⚠️  WARNING: .env file not found!")
        print("   Copy env.example to .env and configure with your credentials:")
        print("   cp env.example .env")
        return False
    else:
        # Check .env file permissions
        env_stat = os.stat('.env')
        if env_stat.st_mode & stat.S_IROTH or env_stat.st_mode & stat.S_IRGRP:
            print("⚠️  WARNING: .env file has overly permissive permissions!")
            print("   Fix with: chmod 600 .env")
        else:
            print("✅ .env file found with secure permissions")
        return True

def set_secure_permissions():
    """Set secure permissions on sensitive files and directories"""
    
    # Secure .env file
    if os.path.exists('.env'):
        os.chmod('.env', 0o600)
        print("✅ Set secure permissions on .env file")
    
    # Secure credentials directory
    if os.path.exists('credentials'):
        os.chmod('credentials', 0o700)
        for file in Path('credentials').glob('*'):
            if file.is_file():
                os.chmod(file, 0o600)
        print("✅ Set secure permissions on credentials directory")
    
    # Secure gmail_tokens directory
    if os.path.exists('gmail_tokens'):
        os.chmod('gmail_tokens', 0o700)
        for file in Path('gmail_tokens').glob('*.pickle'):
            os.chmod(file, 0o600)
        print("✅ Set secure permissions on gmail_tokens directory")

def check_gitignore():
    """Verify .gitignore has proper entries"""
    if not os.path.exists('.gitignore'):
        print("⚠️  WARNING: .gitignore file not found!")
        return False
    
    with open('.gitignore', 'r') as f:
        gitignore_content = f.read()
    
    required_entries = ['.env', 'credentials/', 'gmail_tokens/', '*.pickle']
    missing_entries = []
    
    for entry in required_entries:
        if entry not in gitignore_content:
            missing_entries.append(entry)
    
    if missing_entries:
        print(f"⚠️  WARNING: .gitignore missing entries: {missing_entries}")
        return False
    else:
        print("✅ .gitignore has proper security entries")
        return True

def validate_environment_variables():
    """Check for required environment variables"""
    from dotenv import load_dotenv
    
    # Load .env file if it exists
    if os.path.exists('.env'):
        load_dotenv()
    
    required_vars = [
        'MONGODB_URI',
        'GMAIL_ACCOUNT_1_EMAIL',
        'SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  WARNING: Missing required environment variables: {missing_vars}")
        print("   Please configure these in your .env file")
        return False
    else:
        print("✅ Required environment variables are configured")
        return True

def check_credential_files():
    """Check if credential files exist in proper locations"""
    credential_files = [
        'credentials/gmail_credentials.json',
        'credentials/google_credentials.json'
    ]
    
    missing_files = []
    for file_path in credential_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"⚠️  WARNING: Missing credential files: {missing_files}")
        print("   Please add your credential files to the credentials/ directory")
        return False
    else:
        print("✅ Credential files found")
        return True

def main():
    """Main setup function"""
    print("🔐 Receipt Processor Security Setup")
    print("=" * 40)
    
    # Create necessary directories
    print("\n📁 Creating directories...")
    create_directory('credentials', 0o700)
    create_directory('gmail_tokens', 0o700)
    create_directory('downloads', 0o755)
    create_directory('data', 0o755)
    create_directory('logs', 0o755)
    
    # Check configuration files
    print("\n🔍 Checking configuration...")
    env_ok = check_env_file()
    gitignore_ok = check_gitignore()
    
    # Set secure permissions
    print("\n🔒 Setting secure permissions...")
    set_secure_permissions()
    
    # Validate configuration
    print("\n✅ Validating configuration...")
    if env_ok:
        env_vars_ok = validate_environment_variables()
        creds_ok = check_credential_files()
    else:
        env_vars_ok = False
        creds_ok = False
    
    # Summary
    print("\n📋 Setup Summary:")
    print(f"Environment file: {'✅' if env_ok else '❌'}")
    print(f"GitIgnore config: {'✅' if gitignore_ok else '❌'}")
    print(f"Environment vars: {'✅' if env_vars_ok else '❌'}")
    print(f"Credential files: {'✅' if creds_ok else '❌'}")
    
    if all([env_ok, gitignore_ok, env_vars_ok, creds_ok]):
        print("\n🎉 Security setup complete! Your application is properly configured.")
    else:
        print("\n⚠️  Security setup incomplete. Please address the warnings above.")
        print("\n📖 See SECURITY.md for detailed configuration instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Settings Configuration - Bridge between old and new systems
"""

import os
import json
import pickle
import logging
from pathlib import Path
from typing import Dict, List, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Gmail accounts for both systems
GMAIL_ACCOUNTS = [
    os.getenv('GMAIL_ACCOUNT_1_EMAIL'),
    os.getenv('GMAIL_ACCOUNT_2_EMAIL'),
    os.getenv('GMAIL_ACCOUNT_3_EMAIL')
]

# Account details with pickle files
GMAIL_ACCOUNT_DETAILS = [
    {
        "email": os.getenv('GMAIL_ACCOUNT_1_EMAIL'),
        "pickle_file": os.getenv('GMAIL_ACCOUNT_1_PICKLE_FILE')
    },
    {
        "email": os.getenv('GMAIL_ACCOUNT_2_EMAIL'),
        "pickle_file": os.getenv('GMAIL_ACCOUNT_2_PICKLE_FILE')
    },
    {
        "email": os.getenv('GMAIL_ACCOUNT_3_EMAIL'),
        "pickle_file": os.getenv('GMAIL_ACCOUNT_3_PICKLE_FILE')
    }
]

def load_gmail_credentials(email: str, pickle_path: str, clients_path: str = None) -> Optional[Credentials]:
    """
    Load Gmail credentials from pickle file
    Compatible with both old and new systems
    """
    
    try:
        if Path(pickle_path).exists():
            with open(pickle_path, 'rb') as token:
                creds = pickle.load(token)
                
            # Check if credentials are valid
            if creds and creds.valid:
                return creds
            elif creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                
                # Save refreshed credentials
                with open(pickle_path, 'wb') as token:
                    pickle.dump(creds, token)
                
                return creds
            else:
                logging.warning(f"⚠️ Invalid credentials for {email}")
                return None
        else:
            logging.error(f"❌ Credentials file not found: {pickle_path}")
            return None
            
    except Exception as e:
        logging.error(f"❌ Failed to load credentials for {email}: {e}")
        return None

def initialize_gmail_services() -> Dict[str, any]:
    """
    Initialize Gmail services for all accounts
    Returns dictionary mapping email -> Gmail service
    """
    
    services = {}
    
    for account in GMAIL_ACCOUNT_DETAILS:
        email = account["email"]
        pickle_file = account["pickle_file"]
        
        try:
            creds = load_gmail_credentials(email, pickle_file)
            
            if creds:
                service = build('gmail', 'v1', credentials=creds)
                services[email] = service
                logging.info(f"✅ Gmail service initialized for {email}")
            else:
                logging.warning(f"⚠️ Failed to initialize Gmail service for {email}")
                
        except Exception as e:
            logging.error(f"❌ Gmail service initialization failed for {email}: {e}")
    
    return services

def get_config_path() -> str:
    """Get the config file path"""
    
    # Try new config first
    new_config = "config/expense_config.json"
    if Path(new_config).exists():
        return new_config
    
    # Fall back to old config
    old_config = "config/config_perfect.json"
    if Path(old_config).exists():
        return old_config
    
    raise FileNotFoundError("No config file found. Please create config/expense_config.json")

def load_config() -> Dict:
    """Load configuration file"""
    
    config_path = get_config_path()
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"❌ Failed to load config from {config_path}: {e}")
        raise

def get_mongodb_config() -> Dict:
    """Get MongoDB configuration"""
    
    config = load_config()
    
    mongodb_config = config.get('mongodb', {})
    
    # Get MongoDB config from environment variables
    return {
        'uri': os.getenv('MONGODB_URI'),
        'database': os.getenv('MONGODB_DATABASE', 'expenses'),
        'collection': os.getenv('MONGODB_COLLECTION', 'receipts')
    }

def get_google_sheets_config() -> Dict:
    """Get Google Sheets configuration"""
    
    config = load_config()
    
    # Get Google Sheets config from environment variables
    return {
        'spreadsheet_id': os.getenv('GOOGLE_SHEETS_ID'),
        'sheet_name': os.getenv('GOOGLE_SHEETS_NAME', 'Receipt Dashboard'),
        'credentials_path': os.getenv('GOOGLE_CREDENTIALS_PATH'),
        'service_account_path': os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
    }

def get_processing_config() -> Dict:
    """Get processing configuration"""
    
    config = load_config()
    
    return {
        'days_back_default': int(os.getenv('PROCESSING_DAYS', '30')),
        'max_concurrent': int(os.getenv('MAX_CONCURRENT_PROCESSING', '3')),
        'debug': os.getenv('DEBUG', 'false').lower() == 'true',
        'log_level': os.getenv('LOG_LEVEL', 'INFO')
    }

def get_r2_config() -> Dict:
    """Get R2 storage configuration"""
    
    return {
        'endpoint': os.getenv('R2_ENDPOINT'),
        'access_key': os.getenv('R2_ACCESS_KEY'),
        'secret_key': os.getenv('R2_SECRET_KEY'),
        'bucket': os.getenv('R2_BUCKET'),
        'public_url': os.getenv('R2_PUBLIC_URL')
    }

def get_business_rules() -> Dict:
    """Get business rules for categorization"""
    
    config = load_config()
    
    return config.get('business_rules', {})

def get_ai_settings() -> Dict:
    """Get AI configuration settings"""
    
    config = load_config()
    
    return {
        'huggingface_api_key': os.getenv('HUGGINGFACE_API_KEY'),
        'google_vision_api_key': os.getenv('GOOGLE_VISION_API_KEY'),
        'use_enhanced_ai': True,
        'semantic_model': 'all-MiniLM-L6-v2'
    }

def get_notification_config() -> Dict:
    """Get notification configuration"""
    
    config = load_config()
    
    return config.get('notifications', {
        'console': {'enabled': True},
        'email': {'enabled': False},
        'slack': {'enabled': False}
    })

def get_budget_limits() -> Dict[str, float]:
    """Get budget limits by category"""
    
    config = load_config()
    
    return config.get('budget_limits', {
        "Food & Beverage": 800.0,
        "Software": 500.0,
        "Travel": 1000.0,
        "Gas": 200.0,
        "Professional Services": 800.0,
        "Entertainment": 150.0,
        "Retail": 400.0,
        "Office Supplies": 200.0
    })

def ensure_directories():
    """Ensure all required directories exist"""
    
    config = load_config()
    directories = config.get('directories', {})
    
    default_dirs = [
        'temp_attachments',
        'temp_receipts', 
        'reports',
        'processed',
        'logs',
        'data',
        'config'
    ]
    
    # Create directories from config
    for dir_name in directories.values():
        Path(dir_name).mkdir(parents=True, exist_ok=True)
    
    # Create default directories
    for dir_name in default_dirs:
        Path(dir_name).mkdir(parents=True, exist_ok=True)

def validate_config() -> bool:
    """Validate configuration completeness"""
    
    try:
        # Check required environment variables
        required_vars = [
            'MONGODB_URI',
            'MONGODB_DATABASE',
            'GOOGLE_SHEETS_ID',
            'R2_ENDPOINT',
            'R2_ACCESS_KEY',
            'R2_SECRET_KEY',
            'R2_BUCKET'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logging.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        # Check Gmail accounts
        if not all(GMAIL_ACCOUNTS):
            logging.error("❌ Not all Gmail accounts configured")
            return False
        
        # Check pickle files exist
        for account in GMAIL_ACCOUNT_DETAILS:
            pickle_file = account['pickle_file']
            if not Path(pickle_file).exists():
                logging.warning(f"⚠️ Gmail credentials not found: {pickle_file}")
        
        # Check Google Cloud credentials
        service_account_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
        if not Path(service_account_path).exists():
            logging.warning(f"⚠️ Service account file not found: {service_account_path}")
        
        logging.info("✅ Configuration validation passed")
        return True
        
    except Exception as e:
        logging.error(f"❌ Configuration validation failed: {e}")
        return False

def get_credentials_status() -> Dict[str, bool]:
    """Check the status of all credentials"""
    
    status = {}
    
    # Check Gmail credentials
    for account in GMAIL_ACCOUNT_DETAILS:
        email = account['email']
        pickle_file = account['pickle_file']
        
        try:
            creds = load_gmail_credentials(email, pickle_file)
            status[f"gmail_{email}"] = creds is not None and creds.valid
        except:
            status[f"gmail_{email}"] = False
    
    # Check Google Cloud credentials
    service_account_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
    status['google_cloud_vision'] = Path(service_account_path).exists()
    
    # Check MongoDB
    status['mongodb_configured'] = bool(os.getenv('MONGODB_URI'))
    
    # Check Google Sheets
    status['google_sheets_configured'] = bool(os.getenv('GOOGLE_SHEETS_ID'))
    
    # Check R2 Storage
    status['r2_storage_configured'] = all([
        os.getenv('R2_ENDPOINT'),
        os.getenv('R2_ACCESS_KEY'),
        os.getenv('R2_SECRET_KEY'),
        os.getenv('R2_BUCKET')
    ])
    
    return status

def print_system_status():
    """Print a comprehensive system status"""
    
    print("\n" + "="*60)
    print("🔧 EXPENSE PROCESSING SYSTEM STATUS")
    print("="*60)
    
    # Environment Variables
    print(f"\n🔑 Environment Variables:")
    required_vars = [
        'MONGODB_URI',
        'MONGODB_DATABASE',
        'GOOGLE_SHEETS_ID',
        'R2_ENDPOINT',
        'R2_ACCESS_KEY',
        'R2_SECRET_KEY',
        'R2_BUCKET'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        status = "✅ Set" if value else "❌ Missing"
        print(f"   {var}: {status}")
    
    # Gmail Accounts
    print(f"\n📧 Gmail Accounts:")
    for account in GMAIL_ACCOUNT_DETAILS:
        email = account['email']
        pickle_file = account['pickle_file']
        
        if Path(pickle_file).exists():
            try:
                creds = load_gmail_credentials(email, pickle_file)
                status = "✅ Ready" if creds and creds.valid else "⚠️ Invalid"
            except:
                status = "❌ Error"
        else:
            status = "❌ Missing"
        
        print(f"   {email}: {status}")
    
    # Credentials Status
    print(f"\n🔑 Credentials:")
    cred_status = get_credentials_status()
    for cred_name, is_valid in cred_status.items():
        status_icon = "✅" if is_valid else "❌"
        print(f"   {cred_name}: {status_icon}")
    
    # System Readiness
    print(f"\n🚀 System Status:")
    gmail_ready = any(cred_status[k] for k in cred_status if k.startswith('gmail_'))
    vision_ready = cred_status.get('google_cloud_vision', False)
    mongodb_ready = cred_status.get('mongodb_configured', False)
    r2_ready = cred_status.get('r2_storage_configured', False)
    
    if all([gmail_ready, vision_ready, mongodb_ready, r2_ready]):
        print("   Status: ✅ READY TO PROCESS")
        print("   You can run: python main.py --transactions bank_transactions.csv --days 30")
    else:
        print("   Status: ⚠️ PARTIAL - Some components not ready")
        if not gmail_ready:
            print("   - Gmail authentication required")
        if not vision_ready:
            print("   - Google Cloud Vision API setup required")
        if not mongodb_ready:
            print("   - MongoDB configuration required")
        if not r2_ready:
            print("   - R2 Storage configuration required")
    
    print("="*60)

if __name__ == "__main__":
    ensure_directories()
    print_system_status()
import os
import secrets
from typing import Dict, Any, Optional

class Config:
    """Application configuration"""
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Gmail API Configuration
    GMAIL_CREDENTIALS = os.environ.get('GMAIL_CREDENTIALS')
    GMAIL_TOKEN = os.environ.get('GMAIL_TOKEN')
    
    # Gmail Accounts Configuration - Load from environment variables
    @staticmethod
    def get_gmail_accounts():
        return {
            os.environ.get('GMAIL_ACCOUNT_1_EMAIL', 'account1@gmail.com'): {
                'email': os.environ.get('GMAIL_ACCOUNT_1_EMAIL', 'account1@gmail.com'),
                'display_name': os.environ.get('GMAIL_ACCOUNT_1_DISPLAY_NAME', 'Account 1'),
                'pickle_file': os.environ.get('GMAIL_ACCOUNT_1_PICKLE_FILE', 'gmail_tokens/account1.pickle'),
                'enabled': os.environ.get('GMAIL_ACCOUNT_1_ENABLED', 'true').lower() == 'true',
                'port': int(os.environ.get('GMAIL_ACCOUNT_1_PORT', '8080'))
            },
            os.environ.get('GMAIL_ACCOUNT_2_EMAIL', 'account2@domain.com'): {
                'email': os.environ.get('GMAIL_ACCOUNT_2_EMAIL', 'account2@domain.com'),
                'display_name': os.environ.get('GMAIL_ACCOUNT_2_DISPLAY_NAME', 'Account 2'),
                'pickle_file': os.environ.get('GMAIL_ACCOUNT_2_PICKLE_FILE', 'gmail_tokens/account2.pickle'),
                'enabled': os.environ.get('GMAIL_ACCOUNT_2_ENABLED', 'true').lower() == 'true',
                'port': int(os.environ.get('GMAIL_ACCOUNT_2_PORT', '8081'))
            },
            os.environ.get('GMAIL_ACCOUNT_3_EMAIL', 'account3@domain.com'): {
                'email': os.environ.get('GMAIL_ACCOUNT_3_EMAIL', 'account3@domain.com'),
                'display_name': os.environ.get('GMAIL_ACCOUNT_3_DISPLAY_NAME', 'Account 3'),
                'pickle_file': os.environ.get('GMAIL_ACCOUNT_3_PICKLE_FILE', 'gmail_tokens/account3.pickle'),
                'enabled': os.environ.get('GMAIL_ACCOUNT_3_ENABLED', 'true').lower() == 'true',
                'port': int(os.environ.get('GMAIL_ACCOUNT_3_PORT', '8082'))
            }
        }
    
    GMAIL_ACCOUNTS = get_gmail_accounts()
    
    # MongoDB Configuration
    MONGODB_URI = os.environ.get('MONGODB_URI')
    MONGODB_DATABASE = os.environ.get('MONGODB_DATABASE', 'expense')
    MONGODB_COLLECTION = os.environ.get('MONGODB_COLLECTION', 'receipts')
    
    # R2 Storage Configuration  
    R2_ENDPOINT = os.environ.get('R2_ENDPOINT')
    R2_ACCESS_KEY = os.environ.get('R2_ACCESS_KEY')
    R2_SECRET_KEY = os.environ.get('R2_SECRET_KEY')
    R2_BUCKET = os.environ.get('R2_BUCKET', 'expensesbk')
    R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL')
    
    # Google Services Configuration
    GOOGLE_CREDENTIALS_PATH = os.environ.get('GOOGLE_CREDENTIALS_PATH')
    GOOGLE_SERVICE_ACCOUNT_PATH = os.environ.get('GOOGLE_SERVICE_ACCOUNT_PATH')
    GOOGLE_SHEETS_ID = os.environ.get('GOOGLE_SHEETS_ID')
    GOOGLE_SHEETS_NAME = os.environ.get('GOOGLE_SHEETS_NAME', 'Receipt Dashboard')
    GOOGLE_VISION_API_KEY = os.environ.get('GOOGLE_VISION_API_KEY')
    
    # Google Photos Configuration
    GOOGLE_PHOTOS_CREDENTIALS_PATH = os.environ.get('GOOGLE_PHOTOS_CREDENTIALS_PATH', 'credentials/google_photos_credentials.json')
    GOOGLE_PHOTOS_TOKEN_PATH = os.environ.get('GOOGLE_PHOTOS_TOKEN_PATH', 'credentials/google_photos_token.json')
    
    # Hugging Face AI Configuration
    HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY')
    
    # Teller Bank API Configuration
    TELLER_APPLICATION_ID = os.environ.get('TELLER_APPLICATION_ID')
    TELLER_API_URL = os.environ.get('TELLER_API_URL', 'https://api.teller.io')
    TELLER_API_VERSION = os.environ.get('TELLER_API_VERSION', '2020-10-12')
    TELLER_ENVIRONMENT = os.environ.get('TELLER_ENVIRONMENT', 'sandbox')
    TELLER_WEBHOOK_URL = os.environ.get('TELLER_WEBHOOK_URL')
    TELLER_SIGNING_SECRET = os.environ.get('TELLER_SIGNING_SECRET')
    TELLER_SIGNING_KEY = os.environ.get('TELLER_SIGNING_KEY')
    TELLER_CERT_PATH = os.environ.get('TELLER_CERT_PATH')
    TELLER_KEY_PATH = os.environ.get('TELLER_KEY_PATH')
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Processing settings
    MAX_EMAILS_PER_BATCH = 50
    PROCESSING_DAYS = int(os.environ.get('PROCESSING_DAYS', 30))
    MAX_CONCURRENT_PROCESSING = int(os.environ.get('MAX_CONCURRENT_PROCESSING', 3))
    LOCAL_EXPORT_ENABLED = os.environ.get('LOCAL_EXPORT_ENABLED', 'true').lower() == 'true'
    
    RECEIPT_KEYWORDS = [
        'receipt', 'invoice', 'bill', 'payment', 'purchase',
        'total', 'subtotal', 'tax', 'amount', 'due'
    ]
    
    # Matching tolerances
    AMOUNT_TOLERANCE = 0.01
    DATE_TOLERANCE_DAYS = 3
    
    # File storage
    DOWNLOAD_FOLDER = 'downloads'
    DATA_FOLDER = 'data'
    
    # AI Settings
    AI_ENABLED = bool(os.environ.get('HUGGINGFACE_API_KEY'))
    AI_CONFIDENCE_THRESHOLD = 0.7
    
    # Rate Limiting and Cost Protection
    # AI API Rate Limits (to prevent unexpected charges)
    HUGGINGFACE_DAILY_LIMIT = int(os.environ.get('HUGGINGFACE_DAILY_LIMIT', 200))  # MUCH LOWER: Max 200 calls/day for monthly plan
    HUGGINGFACE_MONTHLY_LIMIT = int(os.environ.get('HUGGINGFACE_MONTHLY_LIMIT', 5000))  # Max 5000 calls/month safety
    # NO OPENAI - REMOVED COMPLETELY
    AI_REQUEST_TIMEOUT = int(os.environ.get('AI_REQUEST_TIMEOUT', 15))  # Shorter timeout: 15 seconds
    AI_RETRY_ATTEMPTS = int(os.environ.get('AI_RETRY_ATTEMPTS', 1))  # Only 1 retry to save calls
    AI_RETRY_DELAY = float(os.environ.get('AI_RETRY_DELAY', 2.0))  # Longer delay between retries
    
    # Processing Limits (to prevent resource abuse and costs)
    MAX_RECEIPTS_PER_SESSION = int(os.environ.get('MAX_RECEIPTS_PER_SESSION', 50))  # MUCH LOWER: 50 receipts max
    MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', 10))  # Smaller files: 10MB max
    MAX_BATCH_SIZE = int(os.environ.get('MAX_BATCH_SIZE', 5))  # Smaller batches: 5 files max
    
    # Conservative AI Usage
    AI_BATCH_DELAY = float(os.environ.get('AI_BATCH_DELAY', 1.0))  # 1 second delay between AI calls
    FALLBACK_TO_RULES_THRESHOLD = float(os.environ.get('FALLBACK_TO_RULES_THRESHOLD', 0.8))  # Fall back to rules at 80% usage
    
    # API Rate Limiting
    GMAIL_API_RATE_LIMIT = int(os.environ.get('GMAIL_API_RATE_LIMIT', 100))  # Max 100 requests/minute
    TELLER_API_RATE_LIMIT = int(os.environ.get('TELLER_API_RATE_LIMIT', 60))  # Max 60 requests/minute
    R2_UPLOAD_RATE_LIMIT = int(os.environ.get('R2_UPLOAD_RATE_LIMIT', 30))  # Max 30 uploads/minute
    
    # Security Settings
    SESSION_TIMEOUT_HOURS = int(os.environ.get('SESSION_TIMEOUT_HOURS', 8))  # Auto-logout after 8 hours
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))  # Block after 5 failed attempts
    IP_RATE_LIMIT_PER_HOUR = int(os.environ.get('IP_RATE_LIMIT_PER_HOUR', 1000))  # Max 1000 requests per IP per hour
    
    # Cost Monitoring Flags
    COST_MONITORING_ENABLED = os.environ.get('COST_MONITORING_ENABLED', 'true').lower() == 'true'
    USAGE_ALERTS_ENABLED = os.environ.get('USAGE_ALERTS_ENABLED', 'true').lower() == 'true'
    
    @staticmethod
    def init_app(app):
        """Initialize app with configuration"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

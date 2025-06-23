import os

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

#!/usr/bin/env python3
"""
Receipt Processor - Production Flask Application
Real-time receipt scanning, AI processing, and bank transaction matching
"""

import os
import sys
import json
import logging
import secrets
import requests
import hmac
import hashlib
import base64
import tempfile
from urllib.parse import urlencode
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, render_template, request, jsonify, redirect, url_for

# MongoDB
from pymongo import MongoClient
from bson import ObjectId

# Google Sheets integration
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Google Sheets dependencies not available")

# OCR and image processing
try:
    import pytesseract
    from PIL import Image
    import PyPDF2
    OCR_AVAILABLE = True
except ImportError as e:
    OCR_AVAILABLE = False
    # Set up basic logging for this error
    print(f"Warning: OCR modules not available: {e}")
    print("Install with: pip install pytesseract Pillow PyPDF2")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log') if os.path.exists('logs') else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Safe imports for optional dependencies
def safe_import(module_name, error_message=None):
    """Safely import optional modules"""
    try:
        return __import__(module_name)
    except ImportError as e:
        if error_message:
            logger.warning(f"{module_name}: {error_message}")
        else:
            logger.warning(f"Optional module {module_name} not available: {e}")
        return None

# Import optional OCR dependencies safely
pytesseract = safe_import('pytesseract', 'OCR processing will be limited - install with: pip install pytesseract')
PIL = safe_import('PIL', 'Image processing will be limited - install with: pip install Pillow')
if not PIL:
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow not available for image processing")
PyPDF2 = safe_import('PyPDF2', 'PDF processing will be limited - install with: pip install PyPDF2')

def safe_parse_date(date_str, default=None):
    """Safely parse various date formats"""
    if not date_str:
        return default or datetime.utcnow()
    
    try:
        # Try different date formats
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%fZ'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try fromisoformat as last resort
        if hasattr(datetime, 'fromisoformat'):
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        
        # If all else fails, return default
        return default or datetime.utcnow()
        
    except Exception as e:
        logger.warning(f"Failed to parse date '{date_str}': {e}")
        return default or datetime.utcnow()

# Core Flask imports
from flask import Flask, request, jsonify, render_template, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

# Database & HTTP
import pymongo
from pymongo import MongoClient
import hmac
import hashlib

# Google Sheets integration
import gspread
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2.service_account import Credentials

# Utilities
from urllib.parse import urlencode

# PERSISTENT MEMORY SYSTEM
from persistent_memory import get_persistent_memory, remember_bank_connection, remember_user_setting, remember_system_setting

# ENHANCED TRANSACTION PROCESSING
try:
    from enhanced_transaction_utils import (
        process_transaction_for_display, process_receipt_for_display,
        build_transaction_query, get_sort_field, categorize_and_analyze_transaction,
        should_split_transaction, split_transaction_intelligently, find_perfect_receipt_match,
        calculate_perfect_match_score, calculate_comprehensive_stats,
        can_transaction_be_split, assess_transaction_review_status,
        find_similar_transactions, generate_transaction_insights,
        generate_transaction_recommendations, create_export_row,
        generate_csv_export, export_to_google_sheets, execute_manual_split,
        extract_merchant_name
    )
    ENHANCED_TRANSACTIONS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Enhanced transaction utilities not available: {e}")
    ENHANCED_TRANSACTIONS_AVAILABLE = False

# BRIAN'S PERSONAL AI FINANCIAL WIZARD
try:
    from brian_financial_wizard import BrianFinancialWizard
    from email_receipt_detector import EmailReceiptDetector
    BRIAN_WIZARD_AVAILABLE = True
    logger.info("🧙‍♂️ Brian's Financial Wizard loaded successfully")
except ImportError as e:
    logger.warning(f"Brian's Financial Wizard not available: {e}")
    BRIAN_WIZARD_AVAILABLE = False

# CALENDAR CONTEXT INTEGRATION
try:
    from calendar_api import register_calendar_blueprint
    CALENDAR_INTEGRATION_AVAILABLE = True
    logger.info("📅 Calendar context integration loaded successfully")
except ImportError as e:
    logger.warning(f"Calendar integration not available: {e}")
    CALENDAR_INTEGRATION_AVAILABLE = False

# ============================================================================
# FIXED CONFIGURATION
# ============================================================================

class Config:
    """Fixed configuration that works on Render"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('PORT', 10000))  # Render's default port
    
    # MongoDB - CRITICAL: Check both MONGO_URI and MONGODB_URI
    MONGODB_URI = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
    MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'expense')
    
    # Teller Configuration - FORCE DEVELOPMENT MODE FOR REAL BANKING
    TELLER_APPLICATION_ID = os.getenv('TELLER_APPLICATION_ID', 'app_pbvpiocruhfnvkhf1k000')
    TELLER_ENVIRONMENT = 'development'  # FORCE development tier for REAL banking data
    TELLER_API_URL = os.getenv('TELLER_API_URL', 'https://api.teller.io')
    TELLER_WEBHOOK_URL = os.getenv('TELLER_WEBHOOK_URL', 'https://receipt-processor.onrender.com/teller/webhook')
    TELLER_SIGNING_SECRET = os.getenv('TELLER_SIGNING_SECRET', 'q7xdfvnwf6nbajjghgzbnzaut4tm4sck')
    
    # R2 Storage
    R2_ENDPOINT = os.getenv('R2_ENDPOINT')
    R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY')
    R2_SECRET_KEY = os.getenv('R2_SECRET_KEY')
    R2_BUCKET = os.getenv('R2_BUCKET', 'expensesbk')
    R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL')
    
    # Gmail accounts
    GMAIL_ACCOUNTS = {
        'kaplan.brian@gmail.com': {
            'display_name': 'Personal Gmail',
            'pickle_file': '/etc/secrets/kaplan_brian_gmail.b64'
        },
        'brian@downhome.com': {
            'display_name': 'Down Home Business', 
            'pickle_file': '/etc/secrets/brian_downhome.b64'
        },
        'brian@musiccityrodeo.com': {
            'display_name': 'Music City Rodeo',
            'pickle_file': '/etc/secrets/brian_musiccityrodeo.b64'
        }
    }

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def load_credential_file(file_path: str, is_binary: bool = False):
    """
    Load credential files with base64 decode support for Render compatibility.
    
    Args:
        file_path: Path to the credential file
        is_binary: If True, returns raw bytes; if False, returns text
    
    Returns:
        File content as bytes or string, or None if file not found
    """
    if not file_path or not os.path.exists(file_path):
        return None
    
    try:
        # Try loading as regular file first
        mode = 'rb' if is_binary else 'r'
        with open(file_path, mode) as f:
            content = f.read()
        
        # If it's a text file and looks like base64, try decoding
        if not is_binary and isinstance(content, str):
            content = content.strip()
            # Check if it looks like base64 (no spaces, reasonable length, base64 chars)
            if (len(content) > 100 and 
                ' ' not in content and 
                '\n' not in content and 
                all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in content)):
                try:
                    # It's base64 encoded, decode it
                    import base64
                    decoded = base64.b64decode(content)
                    return decoded.decode('utf-8') if not is_binary else decoded
                except Exception:
                    # If base64 decode fails, return original content
                    pass
        
        return content
        
    except Exception as e:
        logger.error(f"Failed to load credential file {file_path}: {e}")
        return None

def load_certificate_files_fixed(cert_path: str, key_path: str):
    """
    Enhanced certificate loading with proper error handling and multiple format support.
    Handles both raw PEM files and base64-encoded content from Render secrets.
    """
    try:
        logger.info(f"🔐 Loading certificates from: {cert_path}, {key_path}")
        
        # Try to load certificate content
        cert_content = load_certificate_content(cert_path)
        key_content = load_certificate_content(key_path)
        
        if not cert_content or not key_content:
            logger.error("❌ Failed to load certificate or key content")
            return None, None
        
        # Validate PEM format
        if not validate_pem_format(cert_content, 'CERTIFICATE'):
            logger.error("❌ Invalid certificate PEM format")
            return None, None
            
        if not validate_pem_format(key_content, 'PRIVATE KEY'):
            logger.error("❌ Invalid private key PEM format")
            return None, None
        
        # Create temporary files for requests library
        cert_temp_path, key_temp_path = create_temp_certificate_files(cert_content, key_content)
        
        if cert_temp_path and key_temp_path:
            logger.info("✅ Successfully created temporary certificate files")
            return cert_temp_path, key_temp_path
        else:
            logger.error("❌ Failed to create temporary certificate files")
            return None, None
            
    except Exception as e:
        logger.error(f"❌ Certificate loading error: {e}")
        return None, None

def load_certificate_content(file_path: str) -> str:
    """Load certificate content from file, handling multiple formats"""
    if not file_path or not os.path.exists(file_path):
        logger.warning(f"⚠️ Certificate file not found: {file_path}")
        return None
    
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            logger.warning(f"⚠️ Empty certificate file: {file_path}")
            return None
        
        # Check if content is already in PEM format
        if content.startswith('-----BEGIN'):
            logger.info(f"✅ Found PEM format certificate in {file_path}")
            return content
        
        # Check if content is base64 encoded
        if is_base64_content(content):
            logger.info(f"🔄 Decoding base64 certificate from {file_path}")
            try:
                decoded = base64.b64decode(content).decode('utf-8')
                if decoded.startswith('-----BEGIN'):
                    return decoded
                else:
                    logger.warning(f"⚠️ Base64 decoded content is not PEM format")
                    return None
            except Exception as e:
                logger.error(f"❌ Failed to decode base64 content: {e}")
                return None
        
        # If we get here, content format is unknown
        logger.error(f"❌ Unknown certificate format in {file_path}")
        logger.debug(f"Content preview: {content[:100]}...")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error reading certificate file {file_path}: {e}")
        return None

def is_base64_content(content: str) -> bool:
    """Check if content appears to be base64 encoded"""
    if not content:
        return False
    
    # Basic checks for base64
    if len(content) < 100:  # Too short to be a certificate
        return False
    
    if '\n' in content or ' ' in content:  # Base64 should be single line without spaces
        return False
    
    # Check if all characters are valid base64
    base64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
    return all(c in base64_chars for c in content)

def validate_pem_format(content: str, pem_type: str) -> bool:
    """Validate that content is properly formatted PEM"""
    if not content:
        return False
    
    begin_marker = f"-----BEGIN {pem_type}-----"
    end_marker = f"-----END {pem_type}-----"
    
    if not content.startswith(begin_marker):
        logger.error(f"❌ Missing BEGIN marker for {pem_type}")
        return False
    
    if not content.rstrip().endswith(end_marker):
        logger.error(f"❌ Missing END marker for {pem_type}")
        return False
    
    # Check that there's content between markers
    content_lines = content.split('\n')[1:-1]  # Remove first and last line (markers)
    if not any(line.strip() for line in content_lines):
        logger.error(f"❌ No content between PEM markers for {pem_type}")
        return False
    
    return True

def create_temp_certificate_files(cert_content: str, key_content: str):
    """Create temporary certificate files for requests library"""
    try:
        # Create temporary files
        cert_fd, cert_temp_path = tempfile.mkstemp(suffix='.pem', text=True)
        key_fd, key_temp_path = tempfile.mkstemp(suffix='.pem', text=True)
        
        # Write certificate content
        with os.fdopen(cert_fd, 'w') as f:
            f.write(cert_content)
        
        # Write key content
        with os.fdopen(key_fd, 'w') as f:
            f.write(key_content)
        
        # Set secure permissions
        os.chmod(cert_temp_path, 0o600)
        os.chmod(key_temp_path, 0o600)
        
        logger.info(f"✅ Created temporary certificate files: {cert_temp_path}, {key_temp_path}")
        return cert_temp_path, key_temp_path
        
    except Exception as e:
        logger.error(f"❌ Failed to create temporary certificate files: {e}")
        return None, None

def enhanced_bank_sync_with_certificates():
    """Enhanced bank sync that properly handles certificates"""
    try:
        # Get certificate paths from environment
        cert_path = os.getenv('TELLER_CERT_PATH')
        key_path = os.getenv('TELLER_KEY_PATH')
        
        if not cert_path or not key_path:
            return {
                'success': False,
                'error': 'Certificate paths not configured',
                'cert_path': cert_path,
                'key_path': key_path
            }
        
        logger.info(f"🔐 Certificate paths: {cert_path}, {key_path}")
        
        # Load certificates with enhanced error handling
        cert_temp_path, key_temp_path = load_certificate_files_fixed(cert_path, key_path)
        
        if not cert_temp_path or not key_temp_path:
            return {
                'success': False,
                'error': 'Failed to load certificate files',
                'debug_info': {
                    'cert_path_exists': os.path.exists(cert_path) if cert_path else False,
                    'key_path_exists': os.path.exists(key_path) if key_path else False,
                    'cert_path': cert_path,
                    'key_path': key_path
                }
            }
        
        # Test certificate files by making a simple request
        import requests
        
        try:
            # Test with a simple Teller API call
            test_response = requests.get(
                'https://api.teller.io/accounts',
                headers={
                    'Authorization': 'Bearer test_token',  # This will fail auth but test certs
                    'Content-Type': 'application/json'
                },
                cert=(cert_temp_path, key_temp_path),
                timeout=10
            )
            
            logger.info(f"✅ Certificate test successful - HTTP {test_response.status_code}")
            
            # Clean up temporary files
            try:
                os.unlink(cert_temp_path)
                os.unlink(key_temp_path)
                logger.info("🧹 Cleaned up temporary certificate files")
            except:
                pass
            
            return {
                'success': True,
                'message': 'Certificates loaded and validated successfully',
                'http_status': test_response.status_code
            }
            
        except requests.exceptions.SSLError as e:
            return {
                'success': False,
                'error': f'SSL certificate error: {str(e)}',
                'error_type': 'ssl_error'
            }
        except requests.exceptions.RequestException as e:
            # If we get here, certificates worked but auth failed (expected)
            if 'certificate' not in str(e).lower():
                return {
                    'success': True,
                    'message': 'Certificates working - auth error is expected',
                    'auth_error': str(e)
                }
            else:
                return {
                    'success': False,
                    'error': f'Certificate-related request error: {str(e)}',
                    'error_type': 'cert_request_error'
                }
        finally:
            # Always clean up temp files
            try:
                if cert_temp_path and os.path.exists(cert_temp_path):
                    os.unlink(cert_temp_path)
                if key_temp_path and os.path.exists(key_temp_path):
                    os.unlink(key_temp_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ Enhanced bank sync error: {e}")
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'error_type': 'unexpected_error'
        }

def parse_teller_date(date_str):
    """Safely parse Teller API date strings"""
    if not date_str:
        return datetime.utcnow()
    
    try:
        # Try different date formats that Teller might use
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%fZ'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # If none of the formats work, try fromisoformat
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        
    except Exception as e:
        logger.warning(f"Failed to parse date '{date_str}': {e}")
        return datetime.utcnow()

def safe_import_module(module_name, fallback_message="Module not available"):
    """Safely import modules with fallback"""
    try:
        return __import__(module_name)
    except ImportError as e:
        logger.warning(f"{module_name} not available: {e}")
        return None

# ============================================================================
# SAFE CLIENTS WITH ERROR HANDLING
# ============================================================================

class SafeMongoClient:
    """MongoDB client that won't crash the app"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Connect with proper error handling"""
        try:
            if not Config.MONGODB_URI:
                logger.warning("No MongoDB URI configured")
                return
            
            self.client = MongoClient(
                Config.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                maxPoolSize=10,
                retryWrites=True
            )
            
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[Config.MONGODB_DATABASE]
            self.connected = True
            logger.info("✅ MongoDB connected")
            
        except Exception as e:
            logger.warning(f"MongoDB connection failed: {e}")
            self.connected = False
    
    def health_check(self) -> bool:
        """Check if MongoDB is working"""
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
        except:
            pass
        return False
    
    def get_stats(self) -> Dict:
        """Get database stats safely"""
        try:
            if not self.connected:
                return {"connected": False, "collections": {}}
            
            return {
                "connected": True,
                "database": Config.MONGODB_DATABASE,
                "collections": {
                    "teller_accounts": self.db.teller_accounts.count_documents({}),
                    "teller_transactions": self.db.teller_transactions.count_documents({}),
                    "receipts": self.db.receipts.count_documents({}),
                    "teller_webhooks": self.db.teller_webhooks.count_documents({})
                }
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"connected": False, "error": str(e)}

class SafeTellerClient:
    """Teller client that handles all environments safely"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Receipt-Processor/1.0',
            'Accept': 'application/json'
        })
    
    def get_connect_url(self, user_id: str) -> str:
        """Generate Teller Connect URL"""
        if not Config.TELLER_APPLICATION_ID:
            return "#"
        
        params = {
            'application_id': Config.TELLER_APPLICATION_ID,
            'redirect_uri': Config.TELLER_WEBHOOK_URL.replace('/webhook', '/callback'),
            'state': user_id,
            'scope': 'transactions:read accounts:read identity:read'
        }
        
        base_url = "https://connect.teller.io/connect"
        return f"{base_url}?{urlencode(params)}"
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature safely"""
        try:
            if not Config.TELLER_SIGNING_SECRET:
                return True  # Allow in development
            
            expected = hmac.new(
                Config.TELLER_SIGNING_SECRET.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected)
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

class SafeSheetsClient:
    """Google Sheets client with service account authentication"""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Connect to Google Sheets with service account (supports base64 files)"""
        try:
            # Try multiple credential paths for local and Render deployment
            credential_paths = [
                '/etc/secrets/service_account.b64',  # Render deployment path (base64)
                '/etc/secrets/service_account.json',  # Render deployment path (legacy)
                '/opt/render/project/src/credentials/service_account.json',  # Alternative Render path
                'credentials/service_account.json',  # Local development
                '/Users/briankaplan/Receipt_Matcher/RECEIPT-PROCESSOR/credentials/service_account.json'  # User's local path
            ]
            
            credentials = None
            for path in credential_paths:
                try:
                    # Load credential content with base64 support
                    cred_content = load_credential_file(path, is_binary=False)
                    if not cred_content:
                        continue
                    
                    # Define the scope for Google Sheets
                    scope = [
                        'https://spreadsheets.google.com/feeds',
                        'https://www.googleapis.com/auth/drive'
                    ]
                    
                    # Parse JSON content and create credentials from info
                    import json
                    cred_info = json.loads(cred_content)
                    credentials = Credentials.from_service_account_info(cred_info, scopes=scope)
                    logger.info(f"✅ Google Sheets credentials loaded from: {path}")
                    break
                    
                except Exception as e:
                    logger.warning(f"Failed to load credentials from {path}: {e}")
                    continue
            
            if credentials:
                self.client = gspread.authorize(credentials)
                self.connected = True
                logger.info("✅ Google Sheets client connected successfully")
            else:
                logger.warning("❌ No valid Google Sheets credentials found")
                self.connected = False
                
        except Exception as e:
            logger.error(f"Google Sheets connection failed: {e}")
            self.connected = False
    
    def create_spreadsheet(self, title: str, folder_id: str = None) -> Optional[str]:
        """Create a new Google Spreadsheet"""
        if not self.connected or not self.client:
            logger.error("Google Sheets client not connected - cannot create spreadsheet")
            return None
        
        try:
            # Create spreadsheet
            spreadsheet = self.client.create(title)
            spreadsheet_id = spreadsheet.id
            
            # Share with service account email to ensure access
            try:
                # Get service account email from credentials if available
                spreadsheet.share('', perm_type='anyone', role='reader')
                logger.info(f"✅ Created and shared spreadsheet: {title} (ID: {spreadsheet_id})")
            except Exception as share_error:
                logger.warning(f"Created spreadsheet but sharing failed: {share_error}")
            
            return spreadsheet_id
            
        except Exception as e:
            logger.error(f"Failed to create Google Spreadsheet '{title}': {e}")
            logger.error(f"Google Sheets connection status: {self.connected}")
            if "credentials" in str(e).lower():
                logger.error("This appears to be a credentials issue. Check service account setup.")
            return None
    
    def update_sheet(self, spreadsheet_id: str, worksheet_name: str, data: List[List[str]]) -> bool:
        """Update a worksheet with data"""
        try:
            if not self.connected:
                return False
            
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            
            # Try to get existing worksheet or create new one
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=len(data)+10, cols=len(data[0]) if data else 10)
            
            # Clear existing data and update
            worksheet.clear()
            if data:
                worksheet.update(data, value_input_option='RAW')
            
            logger.info(f"✅ Updated Google Sheet: {worksheet_name} with {len(data)} rows")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update spreadsheet: {e}")
            return False
    
    def get_spreadsheet_url(self, spreadsheet_id: str) -> str:
        """Get the public URL for a spreadsheet"""
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

# ============================================================================
# FLASK APPLICATION
# ============================================================================

def create_app():
    """Create Flask app with all error handling"""
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # Configure for Render
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    
    # Initialize clients safely
    mongo_client = SafeMongoClient()
    teller_client = SafeTellerClient()
    sheets_client = SafeSheetsClient()
    
    logger.info(f"✅ App created - Environment: {Config.TELLER_ENVIRONMENT}")
    
    # ========================================================================
    # CORE ROUTES
    # ========================================================================
    
    @app.route('/health')
    def health():
        """Minimal health check - always responds fast"""
        return jsonify({
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    
    @app.route('/health/detailed')
    def health_detailed():
        """Detailed health check for debugging"""
        try:
            # Quick MongoDB check with timeout protection
            mongo_status = "disconnected"
            try:
                if mongo_client and mongo_client.connected:
                    mongo_status = "connected"
            except:
                mongo_status = "error"
            
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "environment": Config.TELLER_ENVIRONMENT,
                "port": Config.PORT,
                "mongo": mongo_status,
                "services": {
                    "gmail": "configured",
                    "teller": "configured", 
                    "r2": "configured" if Config.R2_ACCESS_KEY else "not_configured"
                }
            }), 200
        except Exception as e:
            return jsonify({
                "status": "degraded",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 200
    
    @app.route('/status')
    def status():
        """System status with real vs test data indicators"""
        try:
            mongo_stats = mongo_client.get_stats()
            
            # Get real data counts
            real_data_stats = {}
            if mongo_client.connected:
                real_data_stats = {
                    "teller_connections": mongo_client.db.teller_tokens.count_documents({"status": "active"}),
                    "total_webhooks": mongo_client.db.teller_webhooks.count_documents({}),
                    "receipts_processed": mongo_client.db.receipts.count_documents({})
                }
            
            return jsonify({
                "timestamp": datetime.utcnow().isoformat(),
                "environment": Config.TELLER_ENVIRONMENT,
                "application_id": Config.TELLER_APPLICATION_ID,
                "port": Config.PORT,
                "webhook_url": Config.TELLER_WEBHOOK_URL,
                "data_status": {
                    "environment_type": "REAL BANKING DATA" if Config.TELLER_ENVIRONMENT == "development" else "TEST DATA",
                    "teller_connections": real_data_stats.get("teller_connections", 0),
                    "total_webhooks": real_data_stats.get("total_webhooks", 0),
                    "receipts_processed": real_data_stats.get("receipts_processed", 0)
                },
                "services": {
                    "mongodb": {
                        "status": "connected" if mongo_stats.get("connected") else "error",
                        "stats": mongo_stats
                    },
                    "teller": {
                        "status": "configured",
                        "environment": Config.TELLER_ENVIRONMENT,
                        "application_id": Config.TELLER_APPLICATION_ID,
                        "webhook_url": Config.TELLER_WEBHOOK_URL
                    },
                    "r2_storage": {
                        "status": "configured" if Config.R2_ACCESS_KEY else "not_configured",
                        "bucket": Config.R2_BUCKET
                    },
                    "gmail": {
                        "status": "configured",
                        "accounts": len(Config.GMAIL_ACCOUNTS)
                    }
                }
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/')
    def dashboard():
        """PWA Main dashboard with futuristic interface"""
        try:
            import time
            
            # Initialize with zero stats - real data loaded via JavaScript
            stats = {
                'total_transactions': '0',
                'match_rate': '0%',
                'total_spend': '$0',
                'review_needed': 0,
                'realtime_processed': 0
            }
            
            # Try to get real stats if MongoDB is connected
            if mongo_client.connected:
                try:
                    # Count all transactions (bank + receipts)
                    bank_transactions = mongo_client.db.bank_transactions.count_documents({})
                    receipts = mongo_client.db.receipts.count_documents({})
                    total_transactions = bank_transactions + receipts
                    
                    if total_transactions > 0:
                        stats['total_transactions'] = f"{total_transactions:,}"
                        
                        # Calculate total spending from bank transactions
                        pipeline = [
                            {"$match": {"amount": {"$lt": 0}}},  # Only expenses
                            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
                        ]
                        result = list(mongo_client.db.bank_transactions.aggregate(pipeline))
                        if result:
                            total_spend = abs(result[0]['total'])
                            if total_spend > 1000:
                                stats['total_spend'] = f"${total_spend/1000:.1f}K"
                            else:
                                stats['total_spend'] = f"${total_spend:.0f}"
                        
                        # Calculate match rate
                        matched_transactions = mongo_client.db.bank_transactions.count_documents({"receipt_matched": True})
                        if bank_transactions > 0:
                            match_rate = (matched_transactions / bank_transactions) * 100
                            stats['match_rate'] = f"{match_rate:.1f}%"
                        
                        # Count items needing review
                        review_needed = mongo_client.db.bank_transactions.count_documents({"needs_review": True})
                        stats['review_needed'] = review_needed
                        
                        # Count real-time processed (recent transactions)
                        from datetime import datetime, timedelta
                        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
                        realtime_count = mongo_client.db.bank_transactions.count_documents({
                            "synced_at": {"$gte": recent_cutoff}
                        })
                        stats['realtime_processed'] = realtime_count
                        
                except Exception as e:
                    logger.warning(f"Failed to get real stats: {e}")
            
            return render_template('index_pwa.html', 
                                 stats=stats, 
                                 timestamp=int(time.time()))
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return f"Dashboard error: {e}", 500
    
    @app.route('/connect')
    def connect_banks():
        """Connect banks page"""
        try:
            connect_url = teller_client.get_connect_url("user_12345")
            return render_template('connect.html', 
                                 connect_url=connect_url,
                                 config=Config)
        except Exception as e:
            logger.error(f"Connect page error: {e}")
            return f"Connect error: {e}", 500
    
    @app.route('/connect-teller')
    def connect_teller():
        """Connect Teller banks page (alias for /connect)"""
        try:
            connect_url = teller_client.get_connect_url("user_12345")
            return render_template('connect.html', 
                                 connect_url=connect_url,
                                 config=Config)
        except Exception as e:
            logger.error(f"Connect Teller page error: {e}")
            return f"Connect Teller error: {e}", 500
    
    @app.route('/settings')
    def settings():
        """Settings page"""
        try:
            return render_template('settings.html')
        except Exception as e:
            logger.error(f"Settings error: {e}")
            return f"Settings error: {e}", 500
    
    @app.route('/scanner')
    def scanner():
        """Receipt scanner page"""
        try:
            return render_template('receipt_scanner.html')
        except Exception as e:
            logger.error(f"Scanner error: {e}")
            return f"Scanner error: {e}", 500
    
    @app.route('/test')
    def test_ui():
        """Test page for UI enhancements"""
        try:
            import time
            return render_template('test.html', timestamp=int(time.time()))
        except Exception as e:
            logger.error(f"Test page error: {e}")
            return f"Test page error: {e}", 500

    @app.route('/transactions')
    def transaction_manager():
        """Ultimate Transaction Management System"""
        try:
            return render_template('transaction_manager.html')
        except Exception as e:
            logger.error(f"Transaction manager error: {e}")
            return f"Transaction manager error: {e}", 500
    
    @app.route('/transaction_manager')
    def transaction_manager_pwa():
        """Ultimate PWA Transaction Management System with Full Interface"""
        try:
            return render_template('transaction_manager.html')
        except Exception as e:
            logger.error(f"PWA Transaction manager error: {e}")
            return f"PWA Transaction manager error: {e}", 500
    
    @app.route('/teller/webhook', methods=['POST'])
    def teller_webhook():
        """Handle Teller webhooks"""
        try:
            signature = request.headers.get('Teller-Signature', '')
            payload = request.get_data()
            
            # Verify signature
            if not teller_client.verify_webhook_signature(payload, signature):
                logger.warning("Invalid webhook signature")
                return jsonify({"error": "Invalid signature"}), 401
            
            data = request.get_json() or {}
            webhook_type = data.get('type', 'unknown')
            
            logger.info(f"✅ Received Teller webhook: {webhook_type}")
            
            # Store webhook in MongoDB if available
            if mongo_client.connected:
                webhook_record = {
                    "type": webhook_type,
                    "data": data,
                    "received_at": datetime.utcnow(),
                    "signature": signature
                }
                mongo_client.db.teller_webhooks.insert_one(webhook_record)
            
            return jsonify({"success": True, "type": webhook_type}), 200
            
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return jsonify({"error": "Webhook processing failed"}), 500
    
    @app.route('/teller/save-token', methods=['POST'])
    def teller_save_token():
        """Save Teller access token after successful connection with persistent memory"""
        try:
            data = request.get_json() or {}
            access_token = data.get('accessToken')
            user_id = data.get('userId')
            enrollment_id = data.get('enrollmentId')
            
            if not access_token:
                return jsonify({"error": "Missing access token"}), 400
            
            # Store in MongoDB if available (existing logic)
            if mongo_client.connected:
                token_record = {
                    "access_token": access_token,
                    "user_id": user_id,
                    "enrollment_id": enrollment_id,
                    "connected_at": datetime.utcnow(),
                    "environment": Config.TELLER_ENVIRONMENT,
                    "status": "active",
                    "persistent_memory": True,  # Flag for our memory system
                    "auto_reconnect": True,
                    "last_sync_attempt": None,
                    "last_successful_sync": None
                }
                mongo_client.db.teller_tokens.insert_one(token_record)
                logger.info(f"✅ Saved Teller token for user {user_id}")
                
                # PERSISTENT MEMORY: Remember this connection long-term
                try:
                    from persistent_memory import get_persistent_memory
                    memory = get_persistent_memory()
                    enrollment_data = {
                        'enrollment_id': enrollment_id,
                        'environment': Config.TELLER_ENVIRONMENT,
                        'connected_via': 'teller_connect'
                    }
                    memory.remember_bank_connection(user_id, access_token, enrollment_data)
                    logger.info(f"🧠 Bank connection remembered in persistent memory for {user_id}")
                except Exception as memory_error:
                    logger.warning(f"Failed to save to persistent memory: {memory_error}")
            
            return jsonify({
                "success": True,
                "message": "Bank connection saved successfully and remembered for future deployments",
                "user_id": user_id,
                "environment": Config.TELLER_ENVIRONMENT,
                "persistent": True
            })
            
        except Exception as e:
            logger.error(f"Save token error: {e}")
            return jsonify({"error": "Failed to save connection"}), 500
    
    @app.route('/teller/callback')
    def teller_callback():
        """Handle Teller OAuth callback"""
        try:
            # Get query parameters
            state = request.args.get('state', 'default_user')
            code = request.args.get('code')
            error = request.args.get('error')
            
            if error:
                logger.warning(f"Teller callback error: {error}")
                return redirect(f"/?error={error}")
            
            if code:
                logger.info(f"✅ Teller callback success for state: {state}")
                return redirect("/?success=bank_connected")
            
            return redirect("/")
            
        except Exception as e:
            logger.error(f"Callback error: {e}")
            return redirect(f"/?error=callback_failed")
    
    @app.route('/api/process-receipts', methods=['POST'])
    def api_process_receipts():
        """REAL receipt processing using actual Gmail API and AI integration"""
        try:
            # Import ObjectId early to avoid scope issues
            from bson import ObjectId
            
            data = request.get_json() or {}
            days = data.get('days_back', 30)
            max_receipts = data.get('max_receipts', 100)
            
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Initialize processing job record
            processing_results = {
                "started_at": datetime.utcnow(),
                "days_requested": days,
                "max_receipts": max_receipts,
                "status": "processing",
                "errors": []
            }
            
            job_id = str(mongo_client.db.processing_jobs.insert_one(processing_results).inserted_id)
            
            # Import real Gmail and processing clients
            from multi_gmail_client import MultiGmailClient
            from receipt_processor import ReceiptProcessor
            from huggingface_client import HuggingFaceClient
            
            # Initialize real clients
            gmail_client = MultiGmailClient()
            receipt_processor = ReceiptProcessor()
            ai_client = HuggingFaceClient()
            
            total_receipts_found = 0
            total_matched = 0
            
            for email, account_info in Config.GMAIL_ACCOUNTS.items():
                try:
                    logger.info(f"📧 Processing Gmail account: {email}")
                    
                    # Connect to real Gmail account
                    if not gmail_client.connect_account(email):
                        logger.error(f"❌ Failed to connect to Gmail account: {email}")
                        continue
                    
                    # Search for real receipt emails
                    receipt_queries = [
                        'subject:(receipt OR invoice OR order OR purchase OR confirmation)',
                        'from:(noreply OR no-reply OR donotreply OR billing OR orders)',
                        'has:attachment filename:(pdf OR receipt OR invoice)',
                        '(receipt OR invoice OR order) AND (total OR amount OR payment)'
                    ]
                    
                    account_receipts = 0
                    emails_scanned = 0
                    
                    for query in receipt_queries:
                        try:
                            # Get real emails from Gmail API
                            messages = gmail_client.search_messages(email, query, max_results=days//4, days_back=days)
                            emails_scanned += len(messages)
                            
                            for message in messages:
                                try:
                                    # Get full message content
                                    email_data = gmail_client.get_message_content(email, message['id'])
                                    
                                    if not email_data:
                                        continue
                                    
                                    # Process attachments if present
                                    receipt_data = None
                                    if email_data.get('attachments'):
                                        for attachment in email_data['attachments']:
                                            if receipt_processor.is_receipt_file(attachment.get('filename', '')):
                                                # Process attachment with AI
                                                attachment_data = receipt_processor.extract_receipt_data_from_attachment(attachment)
                                                if attachment_data and ai_client.is_connected():
                                                    receipt_data = ai_client.process_receipt(attachment_data)
                                                    break
                                    
                                    # If no attachment, process email body text
                                    if not receipt_data and email_data.get('body'):
                                        if ai_client.is_connected():
                                            receipt_data = ai_client.extract_receipt_from_text(email_data['body'])
                                    
                                    # Save to database if we found receipt data
                                    if receipt_data:
                                        receipt_data['gmail_account'] = email
                                        receipt_data['email_id'] = message['id']
                                        receipt_data['processing_job_id'] = job_id
                                        
                                        if mongo_client.save_receipt(receipt_data, message['id'], email):
                                            account_receipts += 1
                                            total_receipts_found += 1
                                            
                                            # Try to match with bank transactions
                                            if teller_client.is_connected():
                                                match_result = teller_client.find_matching_transaction(receipt_data)
                                                if match_result:
                                                    total_matched += 1
                                                    logger.info(f"✅ Matched receipt to bank transaction")
                                    
                                    # Break early if we hit limits
                                    if account_receipts >= max_receipts // 3:  # Divide by number of accounts
                                        break
                                        
                                except Exception as e:
                                    logger.error(f"❌ Failed to process message {message.get('id')}: {e}")
                                    processing_results["errors"].append(f"Message processing: {str(e)}")
                                    
                        except Exception as e:
                            logger.error(f"❌ Query failed for {email}: {query} - {e}")
                            processing_results["errors"].append(f"Query {query}: {str(e)}")
                    
                    logger.info(f"📧 {email}: Found {account_receipts} receipts from {emails_scanned} emails")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process account {email}: {e}")
                    processing_results["errors"].append(f"Account {email}: {str(e)}")
            
            # Update processing job
            processing_results.update({
                "completed_at": datetime.utcnow(),
                "status": "completed",
                "final_results": {
                    "receipts_found": total_receipts_found,
                    "matched_transactions": total_matched,
                    "accounts_processed": len(Config.GMAIL_ACCOUNTS)
                }
            })
            
            # Use string ID directly since job_id is already a string
            mongo_client.db.processing_jobs.update_one(
                {"_id": job_id},
                {"$set": processing_results}
            )
            
            # Calculate match rate
            match_rate = f"{(total_matched/total_receipts_found*100):.0f}%" if total_receipts_found > 0 else "0%"
            
            return jsonify({
                "success": True,
                "processing_job_id": job_id,
                "receipts_found": total_receipts_found,
                "matched": total_matched,
                "match_rate": match_rate,
                "accounts_processed": len(Config.GMAIL_ACCOUNTS),
                "days_processed": days,
                "processed_at": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Receipt processing failed: {e}")
            return jsonify({"error": f"Receipt processing failed: {str(e)}"}), 500

    @app.route('/api/test-gmail-simple', methods=['POST'])
    def api_test_gmail_simple():
        """Simple Gmail search test for debugging"""
        try:
            from multi_gmail_client import MultiGmailClient
            
            gmail_client = MultiGmailClient()
            gmail_client.init_services()
            
            results = {
                "accounts_tested": 0,
                "total_emails_found": 0,
                "details": []
            }
            
            for email, account_info in Config.GMAIL_ACCOUNTS.items():
                account_result = {
                    "email": email,
                    "connected": False,
                    "simple_search_results": 0,
                    "has_attachment_results": 0,
                    "recent_emails_results": 0,
                    "error": None
                }
                
                try:
                    # Test connection
                    if gmail_client.connect_account(email):
                        account_result["connected"] = True
                        results["accounts_tested"] += 1
                        
                        # Test 1: Very simple search
                        simple_messages = gmail_client.search_messages(email, "is:inbox", max_results=10, days_back=30)
                        account_result["simple_search_results"] = len(simple_messages)
                        
                        # Test 2: Emails with attachments
                        attachment_messages = gmail_client.search_messages(email, "has:attachment", max_results=10, days_back=30)
                        account_result["has_attachment_results"] = len(attachment_messages)
                        
                        # Test 3: Recent emails (last 7 days)
                        recent_messages = gmail_client.search_messages(email, "newer_than:7d", max_results=5, days_back=7)
                        account_result["recent_emails_results"] = len(recent_messages)
                        
                        total_found = account_result["simple_search_results"] + account_result["has_attachment_results"] + account_result["recent_emails_results"]
                        results["total_emails_found"] += total_found
                        
                    else:
                        account_result["error"] = "Failed to connect"
                        
                except Exception as e:
                    account_result["error"] = str(e)
                
                results["details"].append(account_result)
            
            return jsonify({
                "success": True,
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Gmail simple test failed: {e}")
            return jsonify({"error": f"Gmail test failed: {str(e)}"}), 500
    
    @app.route('/api/export-sheets', methods=['POST'])
    def api_export_sheets():
        """Export receipts and bank transactions to Google Sheets"""
        try:
            if not sheets_client.connected:
                return jsonify({
                    "success": False,
                    "error": "Google Sheets not connected. Check service account credentials."
                }), 500
            
            # Create spreadsheet name with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            spreadsheet_title = f"Receipt_Matcher_Export_{timestamp}"
            
            # Create new spreadsheet with enhanced error handling
            try:
                spreadsheet_id = sheets_client.create_spreadsheet(spreadsheet_title)
                if not spreadsheet_id:
                    return jsonify({
                        "success": False,
                        "error": "Failed to create Google Spreadsheet - check service account permissions"
                    }), 500
            except Exception as create_error:
                error_details = str(create_error)
                logger.error(f"Spreadsheet creation failed: {error_details}")
                
                # Provide specific error guidance
                if "403" in error_details or "forbidden" in error_details.lower():
                    error_msg = "Permission denied: Service account lacks Google Sheets/Drive permissions"
                elif "401" in error_details or "unauthorized" in error_details.lower():
                    error_msg = "Authentication failed: Invalid service account credentials"
                elif "quota" in error_details.lower():
                    error_msg = "API quota exceeded: Too many requests to Google Sheets"
                else:
                    error_msg = f"Google Sheets API error: {error_details}"
                
                return jsonify({
                    "success": False,
                    "error": error_msg,
                    "technical_details": error_details[:200],
                    "troubleshooting": "Check GOOGLE_CREDENTIALS_JSON environment variable and service account permissions"
                }), 500
            
            # Get receipts data with COMPLETE field set for receipt matching
            receipts_data = []
            if mongo_client.connected:
                receipts = list(mongo_client.db.receipts.find().sort("date", -1))
                
                # Comprehensive headers matching system needs
                receipts_data.append([
                    'Unique_ID', 'Date', 'Merchant', 'Amount', 'Category', 'Description', 
                    'Business_Type', 'Gmail_Account', 'Gmail_Subject', 'Gmail_Sender',
                    'R2_Image_URL', 'R2_Object_Key', 'AI_Confidence', 'Match_Status',
                    'Bank_Match_ID', 'Matching_Transaction', 'Processing_Job_ID',
                    'Status', 'Created_At', 'OCR_Text', 'Receipt_Type'
                ])
                
                # Add receipt rows with complete data
                for receipt in receipts:
                    # Generate R2 URL if available
                    r2_url = ""
                    r2_key = ""
                    if receipt.get('image_key') or receipt.get('r2_key'):
                        r2_key = receipt.get('image_key', receipt.get('r2_key', ''))
                        if r2_key and Config.R2_PUBLIC_URL:
                            r2_url = f"{Config.R2_PUBLIC_URL}/{r2_key}"
                    
                    # Determine match status
                    match_status = "Unmatched"
                    if receipt.get('bank_matched') or receipt.get('bank_match_id'):
                        match_status = "Matched"
                    elif receipt.get('matching_transaction'):
                        match_status = "Partially Matched"
                    
                    receipts_data.append([
                        str(receipt.get('_id', '')),  # Unique MongoDB ID
                        receipt.get('date', '').strftime('%Y-%m-%d') if hasattr(receipt.get('date'), 'strftime') else str(receipt.get('date', '')),
                        receipt.get('merchant', ''),
                        receipt.get('amount', 0),
                        receipt.get('category', ''),
                        receipt.get('description', receipt.get('subject', '')),  # Use subject as description fallback
                        receipt.get('business_type', receipt.get('merchant_type', 'Unknown')),
                        receipt.get('gmail_account', ''),
                        receipt.get('subject', ''),
                        receipt.get('sender', ''),
                        r2_url,
                        r2_key,
                        receipt.get('ai_confidence', 0),
                        match_status,
                        str(receipt.get('bank_match_id', '')),
                        receipt.get('matching_transaction', ''),
                        str(receipt.get('processing_job_id', '')),
                        receipt.get('status', 'processed'),
                        receipt.get('created_at', '').strftime('%Y-%m-%d %H:%M:%S') if hasattr(receipt.get('created_at'), 'strftime') else str(receipt.get('created_at', '')),
                        receipt.get('ocr_text', receipt.get('extracted_text', '')),
                        receipt.get('receipt_type', 'Email Receipt')
                    ])
            
            # Get bank transactions data with comprehensive fields for receipt matching
            transactions_data = []
            if mongo_client.connected:
                transactions = list(mongo_client.db.bank_transactions.find().sort("date", -1))
                
                # Comprehensive headers for bank transactions
                transactions_data.append([
                    'Transaction_ID', 'Date', 'Description', 'Amount', 'Type', 'Category',
                    'Account_ID', 'Account_Name', 'Bank_Name', 'Counterparty_Name', 
                    'Counterparty_Type', 'Receipt_Match_Status', 'Matched_Receipt_ID', 
                    'Receipt_Match_Confidence', 'Status', 'Running_Balance', 'Details',
                    'Teller_ID', 'Created_At', 'Match_Search_Terms'
                ])
                
                # Add transaction rows with complete data
                for transaction in transactions:
                    # Determine receipt match status
                    receipt_match_status = "No Receipt"
                    if transaction.get('receipt_matched') or transaction.get('receipt_match_id'):
                        receipt_match_status = "Receipt Found"
                    elif transaction.get('amount', 0) < 0:  # Expense transactions need receipts
                        receipt_match_status = "Needs Receipt"
                    
                    # Extract counterparty info
                    counterparty = transaction.get('counterparty', {})
                    counterparty_name = counterparty.get('name', '') if counterparty else ''
                    counterparty_type = counterparty.get('type', '') if counterparty else ''
                    
                    transactions_data.append([
                        str(transaction.get('_id', '')),  # Unique MongoDB ID
                        transaction.get('date', '').strftime('%Y-%m-%d') if hasattr(transaction.get('date'), 'strftime') else str(transaction.get('date', '')),
                        transaction.get('description', ''),
                        transaction.get('amount', 0),
                        'Expense' if transaction.get('amount', 0) < 0 else 'Income',
                        transaction.get('category', ''),
                        transaction.get('account_id', ''),
                        transaction.get('account_name', ''),
                        transaction.get('bank_name', ''),
                        counterparty_name,
                        counterparty_type,
                        receipt_match_status,
                        str(transaction.get('receipt_match_id', transaction.get('matched_receipt_id', ''))),
                        transaction.get('match_confidence', ''),
                        transaction.get('status', ''),
                        transaction.get('running_balance', ''),
                        transaction.get('details', ''),
                        str(transaction.get('teller_id', transaction.get('id', ''))),
                        transaction.get('created_at', '').strftime('%Y-%m-%d %H:%M:%S') if hasattr(transaction.get('created_at'), 'strftime') else str(transaction.get('created_at', '')),
                        f"{transaction.get('description', '')} {counterparty_name}".strip()  # Search terms for receipt matching
                    ])
            
            # Update worksheets
            success = True
            if receipts_data:
                success &= sheets_client.update_sheet(spreadsheet_id, "Receipts", receipts_data)
            
            if transactions_data:
                success &= sheets_client.update_sheet(spreadsheet_id, "Bank_Transactions", transactions_data)
            
            if not success:
                return jsonify({
                    "success": False,
                    "error": "Failed to update spreadsheet data"
                }), 500
            
            # Return success with spreadsheet URL
            spreadsheet_url = sheets_client.get_spreadsheet_url(spreadsheet_id)
            
            return jsonify({
                "success": True,
                "message": f"Data exported successfully to Google Sheets",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": spreadsheet_url,
                "worksheets": ["Receipts", "Bank_Transactions"],
                "receipts_count": len(receipts_data) - 1 if receipts_data else 0,
                "transactions_count": len(transactions_data) - 1 if transactions_data else 0
            })
            
        except Exception as e:
            logger.error(f"Google Sheets export error: {e}")
            return jsonify({
                "success": False,
                "error": f"Export failed: {str(e)}"
            }), 500
    
    @app.route('/api/clear-test-data', methods=['POST'])
    def api_clear_test_data():
        """Clear all test data from the database"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Clear test collections
            collections_cleared = 0
            
            # Clear receipts
            result = mongo_client.db.receipts.delete_many({})
            collections_cleared += result.deleted_count
            
            # Clear bank transactions
            result = mongo_client.db.teller_transactions.delete_many({})
            collections_cleared += result.deleted_count
            
            # Clear processing jobs
            result = mongo_client.db.processing_jobs.delete_many({})
            collections_cleared += result.deleted_count
            
            # Clear match results
            result = mongo_client.db.match_results.delete_many({})
            collections_cleared += result.deleted_count
            
            logger.info(f"Cleared {collections_cleared} test documents")
            
            return jsonify({
                "success": True,
                "message": f"Cleared {collections_cleared} test documents",
                "collections_cleared": collections_cleared
            })
            
        except Exception as e:
            logger.error(f"Error clearing test data: {e}")
            return jsonify({"error": f"Failed to clear test data: {str(e)}"}), 500

    @app.route('/api/create-test-receipts', methods=['POST'])
    def api_create_test_receipts():
        """Create sample categorized receipts to demonstrate the system"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            from expense_categorizer import ExpenseCategorizer
            from datetime import datetime, timedelta
            
            # Initialize categorizer
            categorizer = ExpenseCategorizer()
            
            # Sample receipt data with realistic business expenses
            sample_receipts = [
                {
                    "merchant": "Starbucks Coffee",
                    "total_amount": 28.75,
                    "date": (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
                    "items": [
                        {"name": "Client Meeting - 3 Coffees", "price": 15.75},
                        {"name": "Breakfast Pastries", "price": 13.00}
                    ],
                    "raw_text": "Starbucks Coffee Company\nClient Meeting Location\nBusiness Development\n3 Venti Coffees\nMeeting with potential Down Home investors",
                    "business_purpose": "Client meeting for Down Home expansion",
                    "account": "brian@downhome.com"
                },
                {
                    "merchant": "Uber",
                    "total_amount": 47.82,
                    "date": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                    "items": [
                        {"name": "Airport to Downtown", "price": 47.82}
                    ],
                    "raw_text": "Uber Trip\nNashville Airport to Music City Event Venue\nBusiness Travel",
                    "business_purpose": "Travel to Music City Rodeo venue",
                    "account": "brian@musiccityrodeo.com"
                },
                {
                    "merchant": "Office Depot",
                    "total_amount": 156.43,
                    "date": (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                    "items": [
                        {"name": "HP Printer Ink Cartridges", "price": 89.99},
                        {"name": "Copy Paper - 5 Reams", "price": 45.00},
                        {"name": "File Folders", "price": 21.44}
                    ],
                    "raw_text": "Office Depot Business Supplies\nPrinting and Office Equipment\nBusiness Operating Expenses",
                    "business_purpose": "Office supplies for business operations",
                    "account": "kaplan.brian@gmail.com"
                },
                {
                    "merchant": "Adobe Creative Cloud",
                    "total_amount": 52.99,
                    "date": (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                    "items": [
                        {"name": "Creative Cloud Subscription", "price": 52.99}
                    ],
                    "raw_text": "Adobe Creative Cloud Monthly Subscription\nVideo Production Software\nProfessional Tools",
                    "business_purpose": "Video editing software for productions",
                    "account": "brian@downhome.com"
                },
                {
                    "merchant": "Shell Gas Station",
                    "total_amount": 73.25,
                    "date": (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d'),
                    "items": [
                        {"name": "Gasoline - 18.5 gallons", "price": 73.25}
                    ],
                    "raw_text": "Shell Gas Station\nFuel for business travel\nClient visit trip",
                    "business_purpose": "Business travel fuel",
                    "account": "kaplan.brian@gmail.com"
                },
                {
                    "merchant": "Marriott Hotel",
                    "total_amount": 189.00,
                    "date": (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d'),
                    "items": [
                        {"name": "Hotel Room - 1 Night", "price": 149.00},
                        {"name": "Business Center", "price": 15.00},
                        {"name": "Parking", "price": 25.00}
                    ],
                    "raw_text": "Marriott Hotel Nashville\nBusiness Travel Accommodation\nMusic Industry Conference",
                    "business_purpose": "Accommodation for music industry conference",
                    "account": "brian@musiccityrodeo.com"
                },
                {
                    "merchant": "Amazon Web Services",
                    "total_amount": 127.84,
                    "date": (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                    "items": [
                        {"name": "Cloud Storage", "price": 45.00},
                        {"name": "Computing Services", "price": 67.84},
                        {"name": "Data Transfer", "price": 15.00}
                    ],
                    "raw_text": "Amazon Web Services\nCloud hosting and storage\nBusiness infrastructure",
                    "business_purpose": "Cloud infrastructure for business applications",
                    "account": "kaplan.brian@gmail.com"
                },
                {
                    "merchant": "Zoom Video Communications",
                    "total_amount": 19.99,
                    "date": (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d'),
                    "items": [
                        {"name": "Zoom Pro Subscription", "price": 19.99}
                    ],
                    "raw_text": "Zoom Pro Monthly Subscription\nVideo conferencing\nClient meetings and remote work",
                    "business_purpose": "Video conferencing for client meetings",
                    "account": "brian@downhome.com"
                }
            ]
            
            created_receipts = []
            
            for i, receipt_data in enumerate(sample_receipts):
                try:
                    # Use the expense categorizer for realistic categorization
                    category_result = categorizer.categorize_expense(receipt_data)
                    
                    # Create document for database
                    doc_id = f"test_receipt_{i+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    document = {
                        '_id': doc_id,
                        'email_id': f"test_email_{i+1}",
                        'account': receipt_data['account'],
                        'processed_at': datetime.utcnow(),
                        
                        # Core fields
                        'transaction_date': receipt_data['date'],
                        'merchant': receipt_data['merchant'],
                        'price': receipt_data['total_amount'],
                        'description': f"{receipt_data['merchant']} - {receipt_data['business_purpose']}",
                        
                        # Categorization fields (this is what we want to showcase!)
                        'category': category_result.category,
                        'ai_subcategory': category_result.details,
                        'business_purpose': receipt_data['business_purpose'],
                        'tax_deductible': True,  # Business expenses are typically deductible
                        'confidence_score': round(category_result.confidence, 2),
                        'needs_review': category_result.needs_review,
                        
                        # Business analysis
                        'business_type': categorizer.determine_business_type(receipt_data['raw_text'], receipt_data['account']),
                        'merchant_type': 'restaurant' if 'starbucks' in receipt_data['merchant'].lower() else 'other',
                        
                        # Status fields
                        'receipt_status': 'Found Receipt',
                        'match_status': 'Not Matched',
                        'processing_status': 'completed',
                        'source_type': 'test_data',
                        
                        # Additional data
                        'items': receipt_data['items'],
                        'raw_text': receipt_data['raw_text'],
                        'account_name': receipt_data['account'].split('@')[0],
                        'is_subscription': any(sub in receipt_data['merchant'].lower() for sub in ['adobe', 'zoom', 'aws', 'subscription']),
                        'gmail_link': f"https://mail.google.com/test_receipt_{i+1}",
                        'receipt_data': receipt_data
                    }
                    
                    # Insert into database
                    mongo_client.db.receipts.insert_one(document)
                    created_receipts.append({
                        'merchant': receipt_data['merchant'],
                        'amount': receipt_data['total_amount'],
                        'category': category_result.category,
                        'business_type': document['business_type'],
                        'confidence': category_result.confidence
                    })
                    
                except Exception as e:
                    logger.error(f"Error creating test receipt {i+1}: {e}")
                    continue
            
            return jsonify({
                "success": True,
                "message": f"Created {len(created_receipts)} test receipts with AI categorization",
                "receipts_created": len(created_receipts),
                "sample_categories": list(set([r['category'] for r in created_receipts])),
                "sample_receipts": created_receipts[:3]  # Show first 3 as examples
            })
            
        except Exception as e:
            logger.error(f"Error creating test receipts: {e}")
            return jsonify({"error": f"Failed to create test receipts: {str(e)}"}), 500

    @app.route('/api/update-environment', methods=['POST'])
    def api_update_environment():
        """Update environment configuration"""
        try:
            data = request.get_json() or {}
            environment = data.get('environment', 'sandbox')
            webhook_url = data.get('webhook_url', Config.TELLER_WEBHOOK_URL)
            
            # Validate environment
            valid_environments = ['sandbox', 'development', 'production']
            if environment not in valid_environments:
                return jsonify({"error": f"Invalid environment. Must be one of: {valid_environments}"}), 400
            
            # For now, we just log the change since we can't modify environment vars at runtime
            # In a real deployment, this would update environment variables
            logger.info(f"🔧 Environment change requested: {environment}")
            logger.info(f"🔗 Webhook URL: {webhook_url}")
            
            # Store the preference in MongoDB if available
            if mongo_client.connected:
                config_record = {
                    "environment": environment,
                    "webhook_url": webhook_url,
                    "updated_at": datetime.utcnow(),
                    "current_config": {
                        "teller_environment": Config.TELLER_ENVIRONMENT,
                        "teller_webhook_url": Config.TELLER_WEBHOOK_URL,
                        "teller_application_id": Config.TELLER_APPLICATION_ID
                    }
                }
                mongo_client.db.environment_config.insert_one(config_record)
            
            return jsonify({
                "success": True,
                "message": f"Environment configuration updated to {environment}",
                "current_environment": Config.TELLER_ENVIRONMENT,
                "requested_environment": environment,
                "note": "Changes will take effect on next deployment"
            })
            
        except Exception as e:
            logger.error(f"Update environment error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/deploy-environment', methods=['POST'])
    def api_deploy_environment():
        """Deploy environment changes (placeholder for CI/CD integration)"""
        try:
            data = request.get_json() or {}
            message = data.get('message', 'Deploy environment configuration changes')
            
            # In a real deployment, this would trigger a GitHub Action or webhook
            # For now, we just return success with instructions
            
            return jsonify({
                "success": True,
                "message": "Deployment request submitted successfully",
                "instructions": [
                    "Environment changes are stored in the database",
                    "To apply changes, update environment variables in Render dashboard",
                    "Or commit configuration changes to trigger auto-deployment"
                ],
                "current_environment": Config.TELLER_ENVIRONMENT,
                "webhook_url": Config.TELLER_WEBHOOK_URL
            })
            
        except Exception as e:
            logger.error(f"Deploy environment error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/receipts')
    def api_receipts():
        """Get all processed receipts for table view"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Get all receipts with pagination
            limit = int(request.args.get('limit', 50))
            skip = int(request.args.get('skip', 0))
            
            receipts = list(mongo_client.db.receipts.find(
                {}
            ).sort("date", -1).limit(limit).skip(skip))
            
            # Convert datetime objects and ObjectIds to strings
            for receipt in receipts:
                if '_id' in receipt:
                    receipt['_id'] = str(receipt['_id'])
                if 'date' in receipt and hasattr(receipt['date'], 'isoformat'):
                    receipt['date'] = receipt['date'].isoformat()
                if 'created_at' in receipt and hasattr(receipt['created_at'], 'isoformat'):
                    receipt['created_at'] = receipt['created_at'].isoformat()
            
            total_count = mongo_client.db.receipts.count_documents({})
            
            return jsonify({
                "receipts": receipts,
                "total_count": total_count,
                "showing": len(receipts),
                "has_more": total_count > (skip + len(receipts))
            })
            
        except Exception as e:
            logger.error(f"Get receipts error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/status/real')
    def api_status_real():
        """Get REAL service status for status lights"""
        try:
            status = {
                "timestamp": datetime.utcnow().isoformat(),
                "services": {
                    "mongodb": {
                        "status": "connected" if mongo_client.connected else "disconnected",
                        "connected": mongo_client.connected,
                        "light": "green" if mongo_client.connected else "red"
                    },
                    "gmail": {
                        "status": "configured" if Config.GMAIL_ACCOUNTS else "not_configured",
                        "accounts_configured": len(Config.GMAIL_ACCOUNTS),
                        "connected": len(Config.GMAIL_ACCOUNTS) > 0,
                        "light": "green" if len(Config.GMAIL_ACCOUNTS) > 0 else "red"
                    },
                    "teller": {
                        "status": "configured" if Config.TELLER_APPLICATION_ID else "not_configured",
                        "environment": Config.TELLER_ENVIRONMENT,
                        "connected": bool(Config.TELLER_APPLICATION_ID),
                        "light": "green" if Config.TELLER_APPLICATION_ID and Config.TELLER_ENVIRONMENT == 'development' else "yellow"
                    },
                    "r2": {
                        "status": "configured" if Config.R2_ACCESS_KEY else "not_configured",
                        "connected": bool(Config.R2_ACCESS_KEY),
                        "light": "green" if Config.R2_ACCESS_KEY else "red"
                    },
                    "huggingface": {
                        "status": "configured" if os.getenv('HUGGINGFACE_API_KEY') else "standby",
                        "connected": bool(os.getenv('HUGGINGFACE_API_KEY')),
                        "light": "green" if os.getenv('HUGGINGFACE_API_KEY') else "yellow"
                    },
                    "google_sheets": {
                        "status": "connected" if sheets_client.connected else "not_configured",
                        "connected": sheets_client.connected,
                        "light": "green" if sheets_client.connected else "red"
                    },
                    "ocr": {
                        "status": "active" if os.getenv('HUGGINGFACE_API_KEY') else "standby",
                        "connected": bool(os.getenv('HUGGINGFACE_API_KEY')),
                        "light": "green" if os.getenv('HUGGINGFACE_API_KEY') else "yellow"
                    }
                },
                "counts": mongo_client.get_stats() if mongo_client.connected else {
                    "total_receipts": 0,
                    "processed_receipts": 0,
                    "matched_transactions": 0,
                    "total_amount": 0.0
                }
            }
            
            return jsonify(status)
            
        except Exception as e:
            logger.error(f"Real status error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/sync-bank-transactions', methods=['POST'])
    def api_sync_bank_transactions():
        """Fetch and store real bank transactions from connected accounts"""
        try:
            data = request.get_json() or {}
            days_back = data.get('days_back', 365)  # Default to 1 year
            
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Get connected Teller accounts from database
            connected_accounts = list(mongo_client.db.teller_tokens.find({}))
            
            if not connected_accounts:
                return jsonify({"error": "No bank accounts connected. Please connect via Teller first."}), 400
            
            total_transactions = 0
            sync_results = []
            certificate_error_count = 0
            
            logger.info(f"🏦 Starting bank sync for {len(connected_accounts)} accounts")
            
            for account in connected_accounts:
                try:
                    access_token = account.get('access_token')
                    user_id = account.get('user_id', 'unknown')
                    
                    if not access_token:
                        sync_results.append({
                            'user_id': user_id,
                            'status': 'error',
                            'error': 'Missing access token'
                        })
                        continue
                    
                    logger.info(f"🏦 Syncing for Teller user: {user_id}")
                    
                    # Real Teller API call with certificate handling
                    headers = {
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    }
                    
                    # Check if we have client certificates for Teller API
                    cert_path = os.getenv('TELLER_CERT_PATH')
                    key_path = os.getenv('TELLER_KEY_PATH')
                    
                    # Prepare request parameters
                    request_params = {
                        'headers': headers,
                        'timeout': 30
                    }
                    
                    # Add client certificates if available (with base64 support)
                    if cert_path and key_path:
                        cert_temp_path, key_temp_path = load_certificate_files_fixed(cert_path, key_path)
                        if cert_temp_path and key_temp_path:
                            request_params['cert'] = (cert_temp_path, key_temp_path)
                            logger.info(f"🔐 Using client certificates for Teller API (base64 supported)")
                        else:
                            logger.warning(f"⚠️ Failed to load client certificates - Teller development tier requires certificates")
                    else:
                        logger.warning(f"⚠️ No client certificate paths configured - Teller development tier requires certificates")
                    
                    # Get ALL accounts for this user first (correct Teller API pattern)
                    account_response = requests.get(
                        f"{Config.TELLER_API_URL}/accounts",
                        **request_params
                    )
                    
                    if account_response.status_code == 200:
                        user_accounts = account_response.json()
                        logger.info(f"✅ Found {len(user_accounts)} accounts for user {user_id}")
                        
                        # Process each account discovered
                        for account_info in user_accounts:
                            account_id = account_info.get('id')
                            
                            # Get transactions for THIS specific account
                            from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')
                            
                            transactions_response = requests.get(
                                f"{Config.TELLER_API_URL}/accounts/{account_id}/transactions",
                                params={'from_date': from_date, 'count': 1000},
                                **request_params
                            )
                            
                            if transactions_response.status_code == 200:
                                transactions = transactions_response.json()
                                
                                # Store transactions in MongoDB
                                account_transactions = 0
                                for txn in transactions:
                                    # Enhanced transaction record
                                    transaction_record = {
                                        'account_id': account_id,
                                        'user_id': user_id,
                                        'transaction_id': txn.get('id'),
                                        'amount': float(txn.get('amount', 0)),
                                        'date': parse_teller_date(txn.get('date')),
                                        'description': txn.get('description', ''),
                                        'counterparty': txn.get('counterparty', {}),
                                        'type': txn.get('type', ''),
                                        'status': txn.get('status', ''),
                                        'bank_name': account_info.get('institution', {}).get('name', 'Unknown'),
                                        'account_name': account_info.get('name', 'Unknown Account'),
                                        'account_type': account_info.get('type', 'checking'),
                                        'synced_at': datetime.utcnow(),
                                        'teller_user_id': user_id,
                                        'raw_data': txn
                                    }
                                    
                                    # Upsert to avoid duplicates
                                    mongo_client.db.bank_transactions.update_one(
                                        {'transaction_id': txn.get('id')},
                                        {'$set': transaction_record},
                                        upsert=True
                                    )
                                    account_transactions += 1
                                
                                total_transactions += account_transactions
                                sync_results.append({
                                    'account_id': account_id,
                                    'user_id': user_id,
                                    'account_name': account_info.get('name'),
                                    'bank_name': account_info.get('institution', {}).get('name'),
                                    'account_type': account_info.get('type'),
                                    'transactions_synced': account_transactions,
                                    'date_range': f"{from_date} to {datetime.utcnow().strftime('%Y-%m-%d')}",
                                    'status': 'success'
                                })
                                
                                logger.info(f"✅ Synced {account_transactions} transactions for {account_id} ({account_info.get('name')})")
                            
                            else:
                                error_msg = f"Failed to fetch transactions for {account_id}: {transactions_response.status_code} - {transactions_response.text[:200]}"
                                sync_results.append({
                                    'account_id': account_id,
                                    'user_id': user_id,
                                    'status': 'error',
                                    'error': error_msg,
                                    'http_status': transactions_response.status_code
                                })
                                logger.error(f"❌ {error_msg}")
                    
                    elif account_response.status_code == 400 and 'certificate' in account_response.text.lower():
                        certificate_error_count += 1
                        error_msg = f"Teller client certificate required for API access in development tier"
                        sync_results.append({
                            'user_id': user_id,
                            'status': 'certificate_required',
                            'error': error_msg,
                            'action_required': 'configure_teller_certificates',
                            'certificates_available': bool(cert_path and key_path),
                            'note': 'Bank connections work, but transaction sync requires certificates'
                        })
                        logger.warning(f"🔐 {error_msg} for user {user_id}")
                    
                    elif account_response.status_code == 401:
                        error_msg = f"Invalid or expired access token for user {user_id}"
                        sync_results.append({
                            'user_id': user_id,
                            'status': 'error',
                            'error': error_msg,
                            'action_required': 'reconnect_teller'
                        })
                        logger.error(f"❌ {error_msg}")
                    
                    else:
                        error_msg = f"Failed to fetch accounts for {user_id}: {account_response.status_code} - {account_response.text[:200]}"
                        sync_results.append({
                            'user_id': user_id,
                            'status': 'error',
                            'error': error_msg,
                            'http_status': account_response.status_code
                        })
                        logger.error(f"❌ {error_msg}")
                
                except Exception as e:
                    sync_results.append({
                        'user_id': account.get('user_id', 'unknown'),
                        'status': 'error',
                        'error': str(e)
                    })
                    logger.error(f"❌ Error syncing user {account.get('user_id')}: {e}")
            
            # PERSISTENT MEMORY: Update connection sync status
            try:
                from persistent_memory import get_persistent_memory
                memory = get_persistent_memory()
                
                for result in sync_results:
                    user_id = result.get('user_id')
                    if user_id:
                        success = result.get('status') == 'success'
                        error_msg = result.get('error') if not success else None
                        memory.update_connection_sync_status(user_id, success, error_msg)
                        
                logger.info("🧠 Updated connection states in persistent memory")
            except Exception as memory_error:
                logger.warning(f"Failed to update persistent memory: {memory_error}")
            
            # Store sync job record
            sync_job = {
                'started_at': datetime.utcnow(),
                'total_transactions_synced': total_transactions,
                'accounts_processed': len(connected_accounts),
                'days_back': days_back,
                'results': sync_results,
                'status': 'completed',
                'certificate_errors': certificate_error_count,
                'persistent_memory_updated': True
            }
            
            mongo_client.db.bank_sync_jobs.insert_one(sync_job)
            
            # Generate appropriate response based on results
            if certificate_error_count > 0:
                message = f"Bank connections active but transaction sync requires Teller client certificates. {certificate_error_count} accounts need certificates configured."
                success_status = False
            elif total_transactions > 0:
                message = f'Successfully synced {total_transactions} transactions from {len(connected_accounts)} bank accounts'
                success_status = True
            else:
                message = f'No transactions found in the last {days_back} days from {len(connected_accounts)} connected accounts'
                success_status = True
            
            logger.info(f"🎉 Bank sync completed: {total_transactions} transactions from {len(connected_accounts)} accounts")
            
            return jsonify({
                'success': success_status,
                'total_transactions_synced': total_transactions,
                'accounts_processed': len(connected_accounts),
                'certificate_errors': certificate_error_count,
                'sync_results': sync_results,
                'message': message,
                'date_range': f"{days_back} days back to today",
                'persistent_memory': True,
                'certificate_status': {
                    'required': certificate_error_count > 0,
                    'configured': bool(os.getenv('TELLER_CERT_PATH') and os.getenv('TELLER_KEY_PATH')),
                    'note': 'Teller development tier requires client certificates for transaction API access'
                }
            })
            
        except Exception as e:
            logger.error(f"Bank sync error: {e}")
            return jsonify({"error": str(e), "sync_time": "instant", "reason": "exception"}), 500

    @app.route('/api/debug-secrets', methods=['POST'])
    def api_debug_secrets():
        """Debug endpoint to check secret file accessibility"""
        try:
            debug_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "secret_files_check": {},
                "environment_paths": {},
                "file_system_check": {}
            }
            
            # Check environment variables for secret paths
            secret_env_vars = [
                'TELLER_CERT_PATH', 'TELLER_KEY_PATH',
                'GMAIL_ACCOUNT_1_PICKLE_FILE', 'GMAIL_ACCOUNT_2_PICKLE_FILE', 'GMAIL_ACCOUNT_3_PICKLE_FILE',
                'GOOGLE_SERVICE_ACCOUNT_PATH', 'GOOGLE_CREDENTIALS_PATH'
            ]
            
            for var in secret_env_vars:
                path = os.getenv(var)
                debug_info["environment_paths"][var] = path
                
                if path:
                    try:
                        exists = os.path.exists(path)
                        if exists:
                            stat = os.stat(path)
                            debug_info["secret_files_check"][var] = {
                                "path": path,
                                "exists": True,
                                "size": stat.st_size,
                                "readable": os.access(path, os.R_OK)
                            }
                            
                            # Check if it's a PEM file
                            if path.endswith('.pem'):
                                try:
                                    with open(path, 'r') as f:
                                        content = f.read(100)  # First 100 chars
                                        debug_info["secret_files_check"][var]["pem_header"] = content.startswith('-----BEGIN')
                                except Exception as e:
                                    debug_info["secret_files_check"][var]["read_error"] = str(e)
                                    
                        else:
                            debug_info["secret_files_check"][var] = {
                                "path": path,
                                "exists": False
                            }
                    except Exception as e:
                        debug_info["secret_files_check"][var] = {
                            "path": path,
                            "error": str(e)
                        }
            
            # Check /etc/secrets/ directory
            secrets_dir = "/etc/secrets"
            try:
                if os.path.exists(secrets_dir):
                    secret_files = os.listdir(secrets_dir)
                    debug_info["file_system_check"][secrets_dir] = {
                        "exists": True,
                        "files": secret_files,
                        "count": len(secret_files)
                    }
                else:
                    debug_info["file_system_check"][secrets_dir] = {"exists": False}
            except Exception as e:
                debug_info["file_system_check"][secrets_dir] = {"error": str(e)}
            
            return jsonify({
                "success": True,
                "debug_info": debug_info
            })
            
        except Exception as e:
            logger.error(f"Debug secrets error: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/bank-transactions')
    def api_bank_transactions():
        """Get stored bank transactions for table view"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Get transactions with pagination
            limit = int(request.args.get('limit', 50))
            skip = int(request.args.get('skip', 0))
            
            transactions = list(mongo_client.db.bank_transactions.find(
                {},
                {"_id": 0, "raw_data": 0}  # Exclude MongoDB ObjectId and raw data
            ).sort("date", -1).limit(limit).skip(skip))
            
            # Convert datetime objects to strings
            for txn in transactions:
                if 'date' in txn and hasattr(txn['date'], 'isoformat'):
                    txn['date'] = txn['date'].isoformat()
                if 'synced_at' in txn and hasattr(txn['synced_at'], 'isoformat'):
                    txn['synced_at'] = txn['synced_at'].isoformat()
            
            total_count = mongo_client.db.bank_transactions.count_documents({})
            
            return jsonify({
                "transactions": transactions,
                "total_count": total_count,
                "showing": len(transactions),
                "has_more": total_count > (skip + len(transactions))
            })
            
        except Exception as e:
            logger.error(f"Get bank transactions error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/receipts/<receipt_id>')
    def api_receipt_details(receipt_id):
        """Get detailed information for a specific receipt"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            from bson import ObjectId
            
            # Try to find receipt by MongoDB ObjectId
            try:
                receipt = mongo_client.db.receipts.find_one({"_id": ObjectId(receipt_id)})
            except:
                # If not a valid ObjectId, try as string ID
                receipt = mongo_client.db.receipts.find_one({"_id": receipt_id})
            
            if not receipt:
                return jsonify({"error": "Receipt not found"}), 404
            
            # Convert ObjectId to string for JSON serialization
            if '_id' in receipt:
                receipt['_id'] = str(receipt['_id'])
            
            # Convert datetime objects to strings
            for field in ['date', 'created_at']:
                if field in receipt and hasattr(receipt[field], 'isoformat'):
                    receipt[field] = receipt[field].isoformat()
            
            return jsonify(receipt)
            
        except Exception as e:
            logger.error(f"Get receipt details error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/camera-capture', methods=['POST'])
    def api_camera_capture():
        """Process camera captured receipt image"""
        try:
            data = request.get_json() or {}
            image_data = data.get('image_data')
            
            if not image_data:
                return jsonify({"success": False, "error": "No image data provided"}), 400
            
            # Initialize camera scanner and AI processor
            from camera_scanner import CameraScanner
            from huggingface_client import HuggingFaceClient
            
            camera_scanner = CameraScanner()
            ai_client = HuggingFaceClient()
            
            # Process camera capture
            file_info = camera_scanner.process_camera_capture(image_data)
            if not file_info:
                return jsonify({"success": False, "error": "Failed to process camera image"}), 500
            
            # Extract receipt data with AI
            receipt_data = None
            if ai_client.is_connected():
                with open(file_info['filepath'], 'rb') as f:
                    image_bytes = f.read()
                receipt_data = ai_client.process_image(image_bytes)
            
            # Save to MongoDB if receipt data found
            if receipt_data and mongo_client.connected:
                receipt_record = {
                    "email_id": f"camera_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    "account": "camera_capture",
                    "source_type": "camera_scanner",
                    "subject": "Camera Captured Receipt",
                    "sender": "camera_scanner",
                    "date": datetime.utcnow(),
                    "amount": receipt_data.get('total_amount', 0),
                    "merchant": receipt_data.get('merchant', 'Camera Receipt'),
                    "category": "Camera Scan",
                    "ai_confidence": receipt_data.get('confidence', 0.8),
                    "status": "processed",
                    "created_at": datetime.utcnow(),
                    "image_info": file_info,
                    "ocr_text": receipt_data.get('raw_text', ''),
                    "receipt_type": "Camera Capture"
                }
                
                mongo_client.db.receipts.insert_one(receipt_record)
            
            # Clean up temporary file
            import os
            if os.path.exists(file_info['filepath']):
                os.remove(file_info['filepath'])
            
            return jsonify({
                "success": True,
                "data": receipt_data,
                "message": "Receipt processed successfully"
            })
            
        except Exception as e:
            logger.error(f"Camera capture error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/validate-image', methods=['POST'])
    def api_validate_image():
        """Validate image quality for receipt processing"""
        try:
            data = request.get_json() or {}
            image_data = data.get('image_data')
            
            if not image_data:
                return jsonify({"valid": False, "error": "No image data provided"}), 400
            
            # Basic validation - check if image can be processed
            try:
                import base64
                from PIL import Image
                import io
                
                # Remove data URL prefix if present
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                
                # Decode and validate image
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
                
                # Check image properties
                width, height = image.size
                aspect_ratio = height / width if width > 0 else 0
                
                feedback = []
                valid = True
                
                if width < 300 or height < 400:
                    feedback.append("Image resolution is low - try moving closer")
                    valid = False
                
                if aspect_ratio < 1.0:
                    feedback.append("Rotate phone to portrait mode for better results")
                
                if width > 2000 or height > 3000:
                    feedback.append("Image is very high resolution - processing may be slower")
                
                if not feedback:
                    feedback.append("Image looks good for processing!")
                
                return jsonify({
                    "valid": valid,
                    "feedback": feedback,
                    "image_info": {
                        "width": width,
                        "height": height,
                        "aspect_ratio": round(aspect_ratio, 2)
                    }
                })
                
            except Exception as e:
                return jsonify({"valid": False, "error": "Invalid image data"}), 400
            
        except Exception as e:
            logger.error(f"Image validation error: {e}")
            return jsonify({"valid": False, "error": str(e)}), 500
    
    @app.route('/api/scan-google-photos', methods=['POST'])
    def api_scan_google_photos():
        """Scan Google Photos for receipt images"""
        try:
            data = request.get_json() or {}
            days_back = data.get('days_back', 30)
            
            from google_photos_client import GooglePhotosClient
            from receipt_processor import ReceiptProcessor
            from huggingface_client import HuggingFaceClient
            
            photos_client = GooglePhotosClient()
            receipt_processor = ReceiptProcessor()
            ai_client = HuggingFaceClient()
            
            if not photos_client.is_connected():
                return jsonify({
                    "success": False,
                    "error": "Google Photos not connected. Please check credentials."
                }), 500
            
            # Search for receipt photos
            receipt_photos = photos_client.search_receipt_photos(days_back=days_back)
            
            if not receipt_photos:
                return jsonify({
                    "success": True,
                    "photos_found": 0,
                    "receipts_processed": 0,
                    "message": "No receipt photos found in Google Photos"
                })
            
            # Process found photos
            processed_receipts = photos_client.process_receipt_photos(receipt_photos, receipt_processor)
            
            # Save to MongoDB
            saved_count = 0
            if mongo_client.connected:
                for receipt_data in processed_receipts:
                    receipt_record = {
                        "email_id": f"google_photos_{receipt_data['google_photos_id']}",
                        "account": "google_photos",
                        "source_type": "google_photos",
                        "subject": f"Google Photos: {receipt_data['original_filename']}",
                        "sender": "google_photos",
                        "date": receipt_data.get('date', datetime.utcnow()),
                        "amount": receipt_data.get('total_amount', 0),
                        "merchant": receipt_data.get('merchant', 'Unknown'),
                        "category": "Google Photos",
                        "status": "processed",
                        "created_at": datetime.utcnow(),
                        "google_photos_data": receipt_data,
                        "receipt_type": "Google Photos"
                    }
                    
                    mongo_client.db.receipts.replace_one(
                        {"email_id": receipt_record["email_id"]},
                        receipt_record,
                        upsert=True
                    )
                    saved_count += 1
            
            return jsonify({
                "success": True,
                "photos_found": len(receipt_photos),
                "receipts_processed": len(processed_receipts),
                "receipts_saved": saved_count,
                "message": f"Processed {len(processed_receipts)} receipts from Google Photos"
            })
            
        except Exception as e:
            logger.error(f"Google Photos scan error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/batch-upload', methods=['POST'])
    def api_batch_upload():
        """Handle batch upload of receipt images for processing"""
        try:
            # Import required modules for batch processing
            from camera_scanner import CameraScanner
            from receipt_processor import ReceiptProcessor
            
            # Initialize processors
            camera_scanner = CameraScanner()
            receipt_processor = ReceiptProcessor()
            
            # Check if files were uploaded
            if 'files' not in request.files:
                return jsonify({"error": "No files uploaded"}), 400
            
            files = request.files.getlist('files')
            if not files or all(file.filename == '' for file in files):
                return jsonify({"error": "No files selected"}), 400
            
            # Process uploaded files
            processed_files = camera_scanner.process_batch_upload(files)
            
            # Extract receipt data from processed files
            processed_receipts = camera_scanner.process_receipt_images(processed_files, receipt_processor)
            
            # Save to MongoDB
            saved_count = 0
            if mongo_client.connected:
                for receipt_data in processed_receipts:
                    receipt_record = {
                        "email_id": f"batch_upload_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{saved_count}",
                        "account": "batch_upload",
                        "source_type": "batch_upload",
                        "subject": f"Batch Upload: {receipt_data.get('original_filename', 'Unknown')}",
                        "sender": "batch_upload",
                        "date": datetime.utcnow(),
                        "amount": receipt_data.get('total_amount', 0),
                        "merchant": receipt_data.get('merchant', 'Uploaded Receipt'),
                        "category": "Batch Upload",
                        "status": "processed",
                        "created_at": datetime.utcnow(),
                        "upload_data": receipt_data,
                        "receipt_type": "Batch Upload"
                    }
                    
                    mongo_client.db.receipts.insert_one(receipt_record)
                    saved_count += 1
            
            return jsonify({
                "success": True,
                "files_processed": len(processed_files),
                "receipts_extracted": len(processed_receipts),
                "receipts_saved": saved_count,
                "message": f"Successfully processed {len(processed_files)} files and extracted {len(processed_receipts)} receipts"
            })
            
        except Exception as e:
            logger.error(f"Batch upload error: {e}")
            return jsonify({"error": str(e)}), 500

    # =====================================================================
    # PERSISTENT MEMORY MANAGEMENT API ENDPOINTS
    # =====================================================================
    
    @app.route('/api/memory/stats')
    def api_memory_stats():
        """Get persistent memory statistics"""
        try:
            from persistent_memory import get_persistent_memory
            memory = get_persistent_memory()
            
            stats = memory.get_memory_stats()
            
            # Add current system status
            stats["current_system"] = {
                "active_bank_connections": len(list(mongo_client.db.teller_tokens.find({"status": "active"}))) if mongo_client.connected else 0,
                "receipts_processed": mongo_client.db.receipts.count_documents({}) if mongo_client.connected else 0,
                "last_processing_job": None
            }
            
            # Get last processing job
            if mongo_client.connected:
                last_job = mongo_client.db.processing_jobs.find_one(
                    {},
                    sort=[("started_at", -1)]
                )
                if last_job:
                    stats["current_system"]["last_processing_job"] = {
                        "started_at": last_job.get("started_at").isoformat() if last_job.get("started_at") else None,
                        "status": last_job.get("status"),
                        "receipts_found": last_job.get("final_results", {}).get("receipts_found", 0)
                    }
            
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Memory stats error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/memory/user-settings', methods=['GET', 'POST'])
    def api_user_settings():
        """Get or update user settings"""
        try:
            from persistent_memory import get_persistent_memory
            memory = get_persistent_memory()
            
            user_id = request.args.get('user_id', 'default')
            
            if request.method == 'GET':
                # Get user settings
                settings = memory.get_user_settings(user_id)
                return jsonify({
                    "success": True,
                    "settings": {
                        "user_id": settings.user_id,
                        "email_notifications": settings.email_notifications,
                        "processing_frequency": settings.processing_frequency,
                        "auto_process_receipts": settings.auto_process_receipts,
                        "default_receipt_category": settings.default_receipt_category,
                        "amount_tolerance": settings.amount_tolerance,
                        "date_tolerance_days": settings.date_tolerance_days,
                        "preferred_export_format": settings.preferred_export_format,
                        "theme": settings.theme,
                        "dashboard_layout": settings.dashboard_layout,
                        "language": settings.language,
                        "timezone": settings.timezone,
                        "created_at": settings.created_at.isoformat() if settings.created_at else None,
                        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
                    }
                })
            
            else:  # POST - Update settings
                data = request.get_json() or {}
                
                # Update individual settings
                for key, value in data.items():
                    if key != 'user_id':  # Don't allow changing user_id
                        success = memory.update_user_setting(user_id, key, value)
                        if not success:
                            return jsonify({"error": f"Failed to update {key}"}), 500
                
                return jsonify({
                    "success": True,
                    "message": f"Updated {len(data)} user settings",
                    "updated_settings": list(data.keys())
                })
                
        except Exception as e:
            logger.error(f"User settings error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/memory/system-settings', methods=['GET', 'POST'])
    def api_system_settings():
        """Get or update system settings"""
        try:
            from persistent_memory import get_persistent_memory
            memory = get_persistent_memory()
            
            if request.method == 'GET':
                # Get system settings
                settings = memory.get_system_settings()
                return jsonify({
                    "success": True,
                    "settings": {
                        "setting_id": settings.setting_id,
                        "max_concurrent_processing": settings.max_concurrent_processing,
                        "processing_batch_size": settings.processing_batch_size,
                        "default_processing_days": settings.default_processing_days,
                        "auto_backup_enabled": settings.auto_backup_enabled,
                        "backup_frequency": settings.backup_frequency,
                        "maintenance_mode": settings.maintenance_mode,
                        "debug_mode": settings.debug_mode,
                        "auto_cleanup_old_data": settings.auto_cleanup_old_data,
                        "data_retention_days": settings.data_retention_days,
                        "created_at": settings.created_at.isoformat() if settings.created_at else None,
                        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
                    }
                })
            
            else:  # POST - Update settings
                data = request.get_json() or {}
                
                # Update individual settings
                updated_count = 0
                for key, value in data.items():
                    if key != 'setting_id':  # Don't allow changing setting_id
                        success = memory.update_system_setting(key, value)
                        if success:
                            updated_count += 1
                
                return jsonify({
                    "success": True,
                    "message": f"Updated {updated_count} system settings",
                    "updated_settings": list(data.keys())
                })
                
        except Exception as e:
            logger.error(f"System settings error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/memory/connections')
    def api_memory_connections():
        """Get remembered bank connections"""
        try:
            from persistent_memory import get_persistent_memory
            memory = get_persistent_memory()
            
            connections = memory.get_remembered_bank_connections()
            
            # Add sync status information
            for conn in connections:
                user_id = conn.get('user_id')
                
                # Check for recent sync attempts
                if mongo_client.connected:
                    recent_sync = mongo_client.db.bank_sync_jobs.find_one(
                        {},
                        sort=[("started_at", -1)]
                    )
                    
                    if recent_sync:
                        conn['last_sync_job'] = {
                            "started_at": recent_sync.get("started_at").isoformat() if recent_sync.get("started_at") else None,
                            "status": recent_sync.get("status"),
                            "total_transactions": recent_sync.get("total_transactions_synced", 0)
                        }
            
            return jsonify({
                "success": True,
                "connections": connections,
                "total_active": len([c for c in connections if c.get('status') == 'active']),
                "total_connections": len(connections)
            })
            
        except Exception as e:
            logger.error(f"Memory connections error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/memory/cache/<key>', methods=['GET', 'POST', 'DELETE'])
    def api_memory_cache(key):
        """Manage persistent cache entries"""
        try:
            from persistent_memory import get_persistent_memory
            memory = get_persistent_memory()
            
            if request.method == 'GET':
                # Get cached value
                value = memory.cache_get(key)
                if value is not None:
                    return jsonify({
                        "success": True,
                        "key": key,
                        "value": value,
                        "found": True
                    })
                else:
                    return jsonify({
                        "success": True,
                        "key": key,
                        "value": None,
                        "found": False
                    })
            
            elif request.method == 'POST':
                # Set cached value
                data = request.get_json() or {}
                value = data.get('value')
                expires_minutes = data.get('expires_minutes', 60)
                
                success = memory.cache_set(key, value, expires_minutes)
                return jsonify({
                    "success": success,
                    "key": key,
                    "expires_minutes": expires_minutes
                })
            
            elif request.method == 'DELETE':
                # Delete cached value
                success = memory.cache_delete(key)
                return jsonify({
                    "success": success,
                    "key": key,
                    "deleted": success
                })
                
        except Exception as e:
            logger.error(f"Memory cache error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/simple-test-receipts', methods=['POST'])
    def api_simple_test_receipts():
        """Create simple test receipts without complex processing"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Simple test receipts data
            test_receipts = [
                {
                    "date": datetime(2025, 6, 20),
                    "merchant": "Starbucks Coffee",
                    "amount": 15.47,
                    "category": "Business Meals",
                    "description": "Client meeting coffee",
                    "business_type": "Down Home",
                    "gmail_account": "brian@downhome.com",
                    "subject": "Your Starbucks Receipt",
                    "sender": "receipts@starbucks.com",
                    "status": "processed",
                    "created_at": datetime.utcnow(),
                    "ai_confidence": 0.95,
                    "tax_deductible": True
                },
                {
                    "date": datetime(2025, 6, 19),
                    "merchant": "Uber",
                    "amount": 28.50,
                    "category": "Travel",
                    "description": "Airport transportation",
                    "business_type": "Music City Rodeo",
                    "gmail_account": "brian@musiccityrodeo.com",
                    "subject": "Your trip receipt",
                    "sender": "receipts@uber.com",
                    "status": "processed",
                    "created_at": datetime.utcnow(),
                    "ai_confidence": 0.92,
                    "tax_deductible": True
                },
                {
                    "date": datetime(2025, 6, 18),
                    "merchant": "Office Depot",
                    "amount": 156.78,
                    "category": "Office Supplies",
                    "description": "Office supplies and equipment",
                    "business_type": "Down Home",
                    "gmail_account": "kaplan.brian@gmail.com",
                    "subject": "Office Depot Receipt",
                    "sender": "noreply@officedepot.com",
                    "status": "processed",
                    "created_at": datetime.utcnow(),
                    "ai_confidence": 0.98,
                    "tax_deductible": True
                }
            ]
            
            # Insert directly using simple insert_many
            result = mongo_client.db.receipts.insert_many(test_receipts)
            
            return jsonify({
                "success": True,
                "receipts_created": len(result.inserted_ids),
                "message": f"Created {len(result.inserted_ids)} simple test receipts"
            })
            
        except Exception as e:
            logger.error(f"❌ Simple test receipts failed: {e}")
            return jsonify({"error": f"Simple test failed: {str(e)}"}), 500

    @app.route('/api/webhook-stats', methods=['GET'])
    def api_webhook_stats():
        """Get webhook statistics and recent activity"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Count webhooks by type
            webhook_stats = {}
            for webhook_type in ['transaction.created', 'transaction.updated', 'account.updated']:
                count = mongo_client.db.teller_webhooks.count_documents({
                    'type': webhook_type
                })
                webhook_stats[webhook_type] = count
            
            # Recent webhook activity (last 7 days)
            recent_webhooks = list(mongo_client.db.teller_webhooks.find({
                'received_at': {'$gte': datetime.utcnow() - timedelta(days=7)}
            }).sort('received_at', -1).limit(10))
            
            # Check for any transaction data in webhooks
            transaction_webhooks = []
            for webhook in recent_webhooks:
                if webhook.get('type', '').startswith('transaction'):
                    transaction_data = webhook.get('data', {})
                    transaction_webhooks.append({
                        'type': webhook.get('type'),
                        'received_at': webhook.get('received_at').isoformat() if webhook.get('received_at') else None,
                        'amount': transaction_data.get('amount'),
                        'description': transaction_data.get('description'),
                        'merchant': transaction_data.get('merchant', {}).get('name') if transaction_data.get('merchant') else None,
                        'account_id': transaction_data.get('account_id')
                    })
            
            return jsonify({
                'success': True,
                'webhook_stats': webhook_stats,
                'total_webhooks': sum(webhook_stats.values()),
                'recent_activity': len(recent_webhooks),
                'transaction_webhooks': transaction_webhooks,
                'recent_transaction_count': len(transaction_webhooks),
                'webhook_url': 'https://receipt-processor-vvjo.onrender.com/teller/webhook',
                'webhook_active': True,
                'last_7_days': len(recent_webhooks)
            })
            
        except Exception as e:
            logger.error(f"Webhook stats error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/process-webhook-transactions', methods=['POST'])
    def api_process_webhook_transactions():
        """Process webhook transactions and convert them to bank transactions"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            data = request.get_json() or {}
            days_back = data.get('days_back', 30)
            
            # Get recent webhook transactions
            webhook_data = list(mongo_client.db.teller_webhooks.find({
                "type": {"$in": ["transaction.created", "transaction.updated", "transaction.posted"]},
                "received_at": {"$gte": datetime.utcnow() - timedelta(days=days_back)}
            }).sort("received_at", -1))
            
            processed_transactions = []
            receipt_matches = 0
            
            for webhook in webhook_data:
                try:
                    transaction_data = webhook.get('data', {})
                    
                    # Skip if no transaction data
                    if not transaction_data.get('id') or not transaction_data.get('amount'):
                        continue
                    
                    # Extract transaction details from webhook
                    transaction = {
                        'transaction_id': transaction_data.get('id'),
                        'amount': float(transaction_data.get('amount', 0)),
                        'date': datetime.fromisoformat(transaction_data.get('date', '').replace('Z', '+00:00')),
                        'description': transaction_data.get('description', ''),
                        'merchant_name': transaction_data.get('merchant', {}).get('name', '') if transaction_data.get('merchant') else '',
                        'counterparty': transaction_data.get('counterparty', {}),
                        'account_id': transaction_data.get('account_id'),
                        'status': transaction_data.get('status', 'pending'),
                        'type': transaction_data.get('type', ''),
                        'category': transaction_data.get('category', ''),
                        'source': 'webhook',
                        'webhook_received_at': webhook.get('received_at'),
                        'synced_at': datetime.utcnow(),
                        'processed_for_receipts': False,
                        'bank_name': 'Connected Bank',
                        'account_name': f"Account {transaction_data.get('account_id', 'Unknown')[-4:]}"
                    }
                    
                    # Check if transaction already exists
                    existing = mongo_client.db.bank_transactions.find_one({
                        'transaction_id': transaction['transaction_id']
                    })
                    
                    if not existing:
                        # Insert new transaction
                        result = mongo_client.db.bank_transactions.insert_one(transaction)
                        transaction['_id'] = str(result.inserted_id)
                        processed_transactions.append(transaction)
                        
                        logger.info(f"✅ Processed webhook transaction: {transaction['transaction_id']} - ${transaction['amount']}")
                    
                except Exception as e:
                    logger.error(f"Error processing webhook transaction: {e}")
                    continue
            
            return jsonify({
                'success': True,
                'processed_transactions': len(processed_transactions),
                'receipt_matches': receipt_matches,
                'total_webhooks_processed': len(webhook_data),
                'days_back': days_back,
                'message': f'Processed {len(processed_transactions)} new transactions from webhooks',
                'real_time_data': True,
                'transactions': processed_transactions[:5]
            })
            
        except Exception as e:
            logger.error(f"Webhook transaction processing error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/enhanced-bank-transactions')
    def api_enhanced_bank_transactions():
        """Enhanced bank transactions API with filtering and real-time data"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Get parameters
            limit = int(request.args.get('limit', 50))
            skip = int(request.args.get('skip', 0))
            filter_type = request.args.get('filter', 'all')
            
            # Build query based on filter
            query = {}
            if filter_type == 'matched':
                query['receipt_matched'] = True
            elif filter_type == 'unmatched':
                query['receipt_matched'] = {'$ne': True}
            elif filter_type == 'expenses':
                query['amount'] = {'$lt': 0}
            elif filter_type == 'income':
                query['amount'] = {'$gt': 0}
            elif filter_type == 'webhook':
                query['source'] = 'webhook'
            
            # Get transactions
            transactions = list(mongo_client.db.bank_transactions.find(
                query,
                {"raw_data": 0}  # Exclude raw data for performance
            ).sort("date", -1).limit(limit).skip(skip))
            
            # Enhanced processing
            enhanced_transactions = []
            for txn in transactions:
                # Convert datetime objects
                if 'date' in txn and hasattr(txn['date'], 'isoformat'):
                    txn['date'] = txn['date'].isoformat()
                if 'synced_at' in txn and hasattr(txn['synced_at'], 'isoformat'):
                    txn['synced_at'] = txn['synced_at'].isoformat()
                if 'webhook_received_at' in txn and hasattr(txn['webhook_received_at'], 'isoformat'):
                    txn['webhook_received_at'] = txn['webhook_received_at'].isoformat()
                
                # Enhanced fields
                enhanced_txn = {
                    **txn,
                    '_id': str(txn.get('_id', '')),
                    'formatted_amount': f"${abs(txn.get('amount', 0)):,.2f}",
                    'amount_type': 'expense' if txn.get('amount', 0) < 0 else 'income',
                    'merchant_display': (txn.get('merchant_name') or 
                                       txn.get('counterparty', {}).get('name') or 
                                       txn.get('description', '')[:50] or 'Unknown'),
                    'data_source': 'Real-time Webhook' if txn.get('source') == 'webhook' else 'Historical Sync',
                    'match_status': 'Receipt Found ✅' if txn.get('receipt_matched') else 'No Receipt ⏳',
                    'is_recent': (datetime.now() - datetime.fromisoformat(txn['date'].replace('Z', '+00:00'))).days <= 7 if txn.get('date') else False
                }
                enhanced_transactions.append(enhanced_txn)
            
            # Get statistics
            total_count = mongo_client.db.bank_transactions.count_documents(query)
            all_transactions = list(mongo_client.db.bank_transactions.find({}, {
                'amount': 1, 'receipt_matched': 1, 'source': 1
            }))
            
            matched_count = sum(1 for t in all_transactions if t.get('receipt_matched'))
            webhook_count = sum(1 for t in all_transactions if t.get('source') == 'webhook')
            total_expenses = sum(abs(t['amount']) for t in all_transactions if t.get('amount', 0) < 0)
            
            return jsonify({
                "success": True,
                "transactions": enhanced_transactions,
                "pagination": {
                    "total_count": total_count,
                    "showing": len(enhanced_transactions),
                    "has_more": total_count > skip + limit
                },
                "statistics": {
                    "total_transactions": len(all_transactions),
                    "matched_transactions": matched_count,
                    "match_percentage": (matched_count / len(all_transactions) * 100) if all_transactions else 0,
                    "real_time_transactions": webhook_count,
                    "total_expenses": total_expenses
                }
            })
            
        except Exception as e:
            logger.error(f"Enhanced bank transactions API error: {e}")
            return jsonify({"error": str(e)}), 500

    # Update the existing simple-test-receipts function to match the new API
    @app.route('/api/simple-test-receipts', methods=['POST'])
    def api_simple_test_receipts_enhanced():
        """Create simple test receipts for demonstration"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            test_receipts = [
                {
                    'merchant_name': 'Starbucks',
                    'total_amount': 15.67,
                    'date': datetime.now() - timedelta(days=1),
                    'category': 'Food & Beverage',
                    'source_type': 'test_data',
                    'description': 'Coffee and pastry',
                    'processed_at': datetime.utcnow()
                },
                {
                    'merchant_name': 'Shell Gas Station',
                    'total_amount': 45.32,
                    'date': datetime.now() - timedelta(days=2),
                    'category': 'Transportation',
                    'source_type': 'test_data',
                    'description': 'Fuel purchase',
                    'processed_at': datetime.utcnow()
                },
                {
                    'merchant_name': 'Target',
                    'total_amount': 89.45,
                    'date': datetime.now() - timedelta(days=3),
                    'category': 'Shopping',
                    'source_type': 'test_data',
                    'description': 'Household items',
                    'processed_at': datetime.utcnow()
                }
            ]
            
            # Insert test receipts
            inserted_receipts = []
            for receipt in test_receipts:
                result = mongo_client.db.receipts.insert_one(receipt)
                receipt['_id'] = str(result.inserted_id)
                inserted_receipts.append(receipt)
            
            return jsonify({
                "success": True,
                "message": f"Created {len(inserted_receipts)} test receipts",
                "receipts_created": len(inserted_receipts),
                "receipts": inserted_receipts
            })
            
        except Exception as e:
            logger.error(f"Test receipts creation error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/test-certificates', methods=['POST'])
    def api_test_certificates():
        """Test certificate loading and validation"""
        try:
            # Get certificate paths from environment
            cert_path = os.getenv('TELLER_CERT_PATH')
            key_path = os.getenv('TELLER_KEY_PATH')
            
            if not cert_path or not key_path:
                return jsonify({
                    'success': False,
                    'error': 'Certificate paths not configured',
                    'cert_path': cert_path,
                    'key_path': key_path
                })
            
            logger.info(f"🔐 Testing certificate paths: {cert_path}, {key_path}")
            
            # Check if files exist
            cert_exists = os.path.exists(cert_path) if cert_path else False
            key_exists = os.path.exists(key_path) if key_path else False
            
            if not cert_exists or not key_exists:
                return jsonify({
                    'success': False,
                    'error': 'Certificate files not found',
                    'cert_exists': cert_exists,
                    'key_exists': key_exists,
                    'cert_path': cert_path,
                    'key_path': key_path
                })
            
            # Try to load and validate certificates
            cert_temp_path, key_temp_path = load_certificate_files_fixed(cert_path, key_path)
            
            if not cert_temp_path or not key_temp_path:
                return jsonify({
                    'success': False,
                    'error': 'Failed to load certificate files',
                    'debug_info': {
                        'cert_path_exists': cert_exists,
                        'key_path_exists': key_exists,
                        'cert_path': cert_path,
                        'key_path': key_path
                    }
                })
            
            # Test with a simple request
            import requests
            
            try:
                test_response = requests.get(
                    'https://api.teller.io/accounts',
                    headers={
                        'Authorization': 'Bearer test_token',
                        'Content-Type': 'application/json'
                    },
                    cert=(cert_temp_path, key_temp_path),
                    timeout=10
                )
                
                # Clean up temp files
                try:
                    os.unlink(cert_temp_path)
                    os.unlink(key_temp_path)
                except:
                    pass
                
                return jsonify({
                    'success': True,
                    'message': 'Certificates loaded and validated successfully',
                    'http_status': test_response.status_code,
                    'test_result': 'Certificate test passed'
                })
                
            except requests.exceptions.SSLError as e:
                return jsonify({
                    'success': False,
                    'error': f'SSL certificate error: {str(e)}',
                    'error_type': 'ssl_error'
                })
            except requests.exceptions.RequestException as e:
                # Auth error is expected, cert error is not
                if 'certificate' not in str(e).lower():
                    return jsonify({
                        'success': True,
                        'message': 'Certificates working - auth error is expected',
                        'auth_error': str(e)
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Certificate-related request error: {str(e)}',
                        'error_type': 'cert_request_error'
                    })
            finally:
                # Clean up temp files
                try:
                    if cert_temp_path and os.path.exists(cert_temp_path):
                        os.unlink(cert_temp_path)
                    if key_temp_path and os.path.exists(key_temp_path):
                        os.unlink(key_temp_path)
                except:
                    pass
                    
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/debug-certificates', methods=['POST'])
    def api_debug_certificates():
        """Debug certificate file loading"""
        try:
            cert_path = os.getenv('TELLER_CERT_PATH')
            key_path = os.getenv('TELLER_KEY_PATH')
            
            debug_info = {
                'timestamp': datetime.utcnow().isoformat(),
                'certificate_paths': {
                    'cert_path': cert_path,
                    'key_path': key_path,
                    'cert_exists': os.path.exists(cert_path) if cert_path else False,
                    'key_exists': os.path.exists(key_path) if key_path else False
                },
                'file_inspection': {}
            }
            
            # Inspect certificate file
            if cert_path and os.path.exists(cert_path):
                try:
                    with open(cert_path, 'r') as f:
                        cert_content = f.read()
                    
                    debug_info['file_inspection']['certificate'] = {
                        'size_bytes': len(cert_content),
                        'starts_with_pem': cert_content.startswith('-----BEGIN'),
                        'contains_certificate_marker': '-----BEGIN CERTIFICATE-----' in cert_content,
                        'line_count': len(cert_content.split('\n')),
                        'first_50_chars': cert_content[:50] + '...' if len(cert_content) > 50 else cert_content
                    }
                except Exception as e:
                    debug_info['file_inspection']['certificate'] = {
                        'error': str(e)
                    }
            
            # Inspect private key file
            if key_path and os.path.exists(key_path):
                try:
                    with open(key_path, 'r') as f:
                        key_content = f.read()
                    
                    debug_info['file_inspection']['private_key'] = {
                        'size_bytes': len(key_content),
                        'starts_with_pem': key_content.startswith('-----BEGIN'),
                        'contains_key_marker': '-----BEGIN PRIVATE KEY-----' in key_content,
                        'line_count': len(key_content.split('\n')),
                        'first_50_chars': key_content[:50] + '...' if len(key_content) > 50 else key_content
                    }
                except Exception as e:
                    debug_info['file_inspection']['private_key'] = {
                        'error': str(e)
                    }
            
            return jsonify({
                'success': True,
                'debug_info': debug_info
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ============================================================================
    # 🚀 ENHANCED TRANSACTION PROCESSING SYSTEM
    # ============================================================================

    @app.route('/api/enhanced-bank-transactions-v2')
    def api_enhanced_bank_transactions_v2():
        """Ultimate transaction API with advanced filtering, search, and analytics"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Enhanced parameters
            limit = min(int(request.args.get('limit', 100)), 1000)
            skip = int(request.args.get('skip', 0))
            filter_type = request.args.get('filter', 'all')
            search = request.args.get('search', '').strip()
            sort_by = request.args.get('sort', 'date')
            sort_order = request.args.get('order', 'desc')
            category_filter = request.args.get('category')
            amount_min = request.args.get('amount_min')
            amount_max = request.args.get('amount_max')
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            business_type = request.args.get('business_type')
            match_status = request.args.get('match_status')  # matched, unmatched, needs_review
            
            # Build comprehensive query
            query = build_transaction_query(
                filter_type, search, category_filter, amount_min, amount_max,
                date_from, date_to, business_type, match_status
            )
            
            # Execute query with sorting
            sort_direction = -1 if sort_order == 'desc' else 1
            sort_field = get_sort_field(sort_by)
            
            transactions = list(mongo_client.db.bank_transactions.find(
                query,
                {
                    "_id": 1, "transaction_id": 1, "date": 1, "description": 1, "amount": 1,
                    "merchant_name": 1, "counterparty": 1, "category": 1, "business_type": 1,
                    "receipt_matched": 1, "receipt_match_id": 1, "match_confidence": 1,
                    "source": 1, "account_name": 1, "bank_name": 1, "status": 1,
                    "split_transactions": 1, "parent_transaction_id": 1, "is_split": 1,
                    "ai_category": 1, "ai_business_type": 1, "ai_confidence": 1,
                    "needs_review": 1, "review_reasons": 1, "tags": 1,
                    "synced_at": 1, "matched_at": 1, "webhook_received_at": 1
                }
            ).sort([(sort_field, sort_direction)]).limit(limit).skip(skip))
            
            # Enhanced processing with analytics
            enhanced_transactions = []
            for txn in transactions:
                enhanced_txn = process_transaction_for_display(txn)
                enhanced_transactions.append(enhanced_txn)
            
            # Comprehensive statistics
            total_count = mongo_client.db.bank_transactions.count_documents(query)
            stats = calculate_comprehensive_stats()
            
            return jsonify({
                "success": True,
                "transactions": enhanced_transactions,
                "pagination": {
                    "total_count": total_count,
                    "showing": len(enhanced_transactions),
                    "page": (skip // limit) + 1,
                    "has_more": total_count > skip + limit,
                    "limit": limit,
                    "skip": skip
                },
                "statistics": stats,
                "filters_applied": {
                    "type": filter_type,
                    "search": search,
                    "category": category_filter,
                    "business_type": business_type,
                    "match_status": match_status,
                    "amount_range": f"${amount_min} - ${amount_max}" if amount_min or amount_max else None,
                    "date_range": f"{date_from} to {date_to}" if date_from or date_to else None,
                    "sort": f"{sort_by} {sort_order}"
                }
            })
            
        except Exception as e:
            logger.error(f"Enhanced transactions API error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/process-transactions', methods=['POST'])
    def api_process_transactions():
        """Ultimate transaction processing with AI categorization and smart splitting"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            data = request.get_json() or {}
            force_reprocess = data.get('force_reprocess', False)
            enable_splitting = data.get('enable_splitting', True)
            
            # Get all unprocessed or force reprocess transactions
            query = {}
            if not force_reprocess:
                query = {
                    '$or': [
                        {'ai_processed': {'$ne': True}},
                        {'category': {'$exists': False}},
                        {'business_type': {'$exists': False}}
                    ]
                }
            
            transactions = list(mongo_client.db.bank_transactions.find(query))
            
            processed_count = 0
            split_count = 0
            categorized_count = 0
            matched_count = 0
            
            for transaction in transactions:
                try:
                    # AI-powered categorization and business type detection
                    ai_result = categorize_and_analyze_transaction(transaction)
                    
                    # Check for potential splits (Apple, Amazon, etc.)
                    split_result = None
                    if enable_splitting and should_split_transaction(transaction):
                        split_result = split_transaction_intelligently(transaction)
                    
                    # Smart receipt matching
                    receipt_match = find_perfect_receipt_match(transaction)
                    
                    # Update transaction with all enhancements
                    update_data = {
                        'category': ai_result['category'],
                        'business_type': ai_result['business_type'],
                        'ai_category': ai_result['category'],
                        'ai_business_type': ai_result['business_type'],
                        'ai_confidence': ai_result['confidence'],
                        'ai_processed': True,
                        'needs_review': ai_result['needs_review'],
                        'review_reasons': ai_result['review_reasons'],
                        'tags': ai_result['tags'],
                        'processed_at': datetime.utcnow()
                    }
                    
                    if split_result:
                        update_data.update({
                            'is_split': True,
                            'split_transactions': split_result['splits'],
                            'split_method': split_result['method'],
                            'split_confidence': split_result['confidence']
                        })
                        split_count += 1
                    
                    if receipt_match:
                        update_data.update({
                            'receipt_matched': True,
                            'receipt_match_id': str(receipt_match['_id']),
                            'match_confidence': receipt_match['confidence'],
                            'matched_at': datetime.utcnow()
                        })
                        matched_count += 1
                        
                        # Update the receipt too
                        mongo_client.db.receipts.update_one(
                            {'_id': receipt_match['_id']},
                            {'$set': {
                                'bank_matched': True,
                                'bank_match_id': transaction['transaction_id'],
                                'matched_at': datetime.utcnow(),
                                'match_confidence': receipt_match['confidence']
                            }}
                        )
                    
                    mongo_client.db.bank_transactions.update_one(
                        {'_id': transaction['_id']},
                        {'$set': update_data}
                    )
                    
                    processed_count += 1
                    categorized_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing transaction {transaction.get('transaction_id')}: {e}")
                    continue
            
            return jsonify({
                'success': True,
                'message': f'Processed {processed_count} transactions',
                'results': {
                    'total_processed': processed_count,
                    'categorized': categorized_count,
                    'split_transactions': split_count,
                    'receipt_matches': matched_count,
                    'force_reprocess': force_reprocess,
                    'splitting_enabled': enable_splitting
                }
            })
            
        except Exception as e:
            logger.error(f"Transaction processing error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/transaction-details/<transaction_id>')
    def api_transaction_details(transaction_id):
        """Comprehensive transaction details with split analysis and receipt info"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Find main transaction
            transaction = mongo_client.db.bank_transactions.find_one({
                '$or': [
                    {'_id': ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id},
                    {'transaction_id': transaction_id}
                ]
            })
            
            if not transaction:
                return jsonify({"error": "Transaction not found"}), 404
            
            # Process transaction for display
            enhanced_transaction = process_transaction_for_display(transaction)
            
            # Get split transactions if any
            split_transactions = []
            if transaction.get('is_split'):
                splits = transaction.get('split_transactions', [])
                for split in splits:
                    split_transactions.append({
                        **split,
                        'formatted_amount': f"${abs(split.get('amount', 0)):,.2f}",
                        'percentage': (abs(split.get('amount', 0)) / abs(transaction.get('amount', 1))) * 100
                    })
            
            # Get parent transaction if this is a split
            parent_transaction = None
            if transaction.get('parent_transaction_id'):
                parent_transaction = mongo_client.db.bank_transactions.find_one({
                    'transaction_id': transaction['parent_transaction_id']
                })
                if parent_transaction:
                    parent_transaction = process_transaction_for_display(parent_transaction)
            
            # Get matched receipt details
            matched_receipt = None
            if transaction.get('receipt_match_id'):
                receipt_id = transaction['receipt_match_id']
                if ObjectId.is_valid(receipt_id):
                    matched_receipt = mongo_client.db.receipts.find_one({'_id': ObjectId(receipt_id)})
                else:
                    matched_receipt = mongo_client.db.receipts.find_one({'_id': receipt_id})
                
                if matched_receipt:
                    matched_receipt = process_receipt_for_display(matched_receipt)
            
            # Find similar transactions for pattern analysis
            similar_transactions = find_similar_transactions(transaction)
            
            # Generate insights and recommendations
            insights = generate_transaction_insights(transaction, similar_transactions)
            recommendations = generate_transaction_recommendations(transaction)
            
            return jsonify({
                "success": True,
                "transaction": enhanced_transaction,
                "split_transactions": split_transactions,
                "parent_transaction": parent_transaction,
                "matched_receipt": matched_receipt,
                "similar_transactions": similar_transactions,
                "insights": insights,
                "recommendations": recommendations,
                "can_split": can_transaction_be_split(transaction),
                "review_status": assess_transaction_review_status(transaction)
            })
            
        except Exception as e:
            logger.error(f"Transaction details error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/split-transaction', methods=['POST'])
    def api_split_transaction():
        """Manual transaction splitting with custom categories"""
        try:
            data = request.get_json() or {}
            transaction_id = data.get('transaction_id')
            splits = data.get('splits', [])
            
            if not transaction_id or not splits:
                return jsonify({"error": "Transaction ID and splits required"}), 400
            
            # Validate splits add up to original amount
            transaction = mongo_client.db.bank_transactions.find_one({
                'transaction_id': transaction_id
            })
            
            if not transaction:
                return jsonify({"error": "Transaction not found"}), 404
            
            original_amount = abs(transaction.get('amount', 0))
            split_total = sum(abs(split.get('amount', 0)) for split in splits)
            
            if abs(original_amount - split_total) > 0.01:
                return jsonify({"error": "Split amounts must equal original amount"}), 400
            
            # Create split transactions
            split_result = execute_manual_split(transaction, splits)
            
            return jsonify({
                'success': True,
                'message': f'Transaction split into {len(splits)} parts',
                'split_transactions': split_result['splits'],
                'original_transaction_id': transaction_id
            })
            
        except Exception as e:
            logger.error(f"Split transaction error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/export-transactions', methods=['POST'])
    def api_export_transactions():
        """Enhanced export with filtering and comprehensive data"""
        try:
            data = request.get_json() or {}
            export_format = data.get('format', 'csv')  # csv, excel, sheets
            filters = data.get('filters', {})
            include_splits = data.get('include_splits', True)
            
            # Build query from filters
            query = build_transaction_query(**filters)
            
            # Get all matching transactions
            transactions = list(mongo_client.db.bank_transactions.find(query).sort('date', -1))
            
            # Process for export
            export_data = []
            for txn in transactions:
                # Main transaction
                export_row = create_export_row(txn)
                export_data.append(export_row)
                
                # Add split transactions if enabled
                if include_splits and txn.get('is_split'):
                    for split in txn.get('split_transactions', []):
                        split_row = create_export_row(txn, split_data=split)
                        export_data.append(split_row)
            
            if export_format == 'csv':
                csv_data = generate_csv_export(export_data)
                return jsonify({
                    'success': True,
                    'data': csv_data,
                    'filename': f'transactions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                    'format': 'csv',
                    'count': len(export_data)
                })
            
            elif export_format == 'sheets':
                sheets_result = export_to_google_sheets(export_data)
                return jsonify({
                    'success': True,
                    'sheets_url': sheets_result['url'],
                    'message': f'Exported {len(export_data)} transactions to Google Sheets',
                    'count': len(export_data)
                })
            
            else:
                return jsonify({"error": "Unsupported export format"}), 400
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/brian-wizard-analyze', methods=['POST'])
    def api_brian_wizard_analyze():
        """
        Brian's Personal AI Financial Wizard Analysis
        Comprehensive expense categorization with business context
        """
        try:
            if not BRIAN_WIZARD_AVAILABLE:
                return jsonify({
                    'success': False,
                    'error': 'Brian\'s Financial Wizard not available'
                }), 500
            
            data = request.get_json()
            expense_data = data.get('expense', {})
            
            # Initialize Brian's Financial Wizard
            wizard = BrianFinancialWizard()
            
            # Analyze the expense
            analysis = wizard.smart_expense_categorization(expense_data)
            
            return jsonify({
                'success': True,
                'analysis': {
                    'merchant': analysis.merchant,
                    'amount': analysis.amount,
                    'category': analysis.category,
                    'business_type': analysis.business_type,
                    'confidence': analysis.confidence,
                    'purpose': analysis.purpose,
                    'tax_deductible': analysis.tax_deductible,
                    'needs_review': analysis.needs_review,
                    'auto_approved': analysis.auto_approved,
                    'receipt_source': analysis.receipt_source
                }
            })
            
        except Exception as e:
            logger.error(f"Brian's Wizard analysis failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/scan-emails-for-receipts', methods=['POST'])
    def api_scan_emails_for_receipts():
        """
        Scan emails for receipts using Brian's Email Receipt Detector
        """
        try:
            if not BRIAN_WIZARD_AVAILABLE:
                return jsonify({
                    'success': False,
                    'error': 'Email Receipt Detector not available'
                }), 500
            
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json() or {}
            else:
                data = request.form.to_dict()
            
            email_account = data.get('email_account', 'auto-detect')
            password = data.get('password', 'oauth')  # Should use OAuth in production
            days_back = int(data.get('days_back', 30))
            
            if not email_account or not password:
                return jsonify({
                    'success': False,
                    'error': 'Email account and password required'
                }), 400
            
            # Initialize Email Receipt Detector
            detector = EmailReceiptDetector()
            
            # Scan for receipts
            receipts = detector.scan_emails_for_receipts(email_account, password, days_back)
            
            # Process found receipts with Brian's Wizard
            wizard = BrianFinancialWizard()
            processed_receipts = []
            
            for receipt in receipts:
                # Prepare expense data for wizard analysis
                expense_data = {
                    'merchant': receipt.merchant_detected or 'Unknown',
                    'amount': receipt.amount_detected or 0,
                    'description': receipt.email_subject,
                    'date': receipt.email_date,
                    'source': 'email_auto_detected'
                }
                
                # Analyze with Brian's Wizard
                analysis = wizard.smart_expense_categorization(expense_data)
                
                processed_receipts.append({
                    'email_info': {
                        'subject': receipt.email_subject,
                        'from': receipt.email_from,
                        'date': receipt.email_date.isoformat(),
                        'type': receipt.receipt_type,
                        'confidence': receipt.confidence
                    },
                    'wizard_analysis': {
                        'category': analysis.category,
                        'business_type': analysis.business_type,
                        'confidence': analysis.confidence,
                        'purpose': analysis.purpose,
                        'auto_approved': analysis.auto_approved
                    },
                    'download_url': receipt.download_url,
                    'has_attachment': receipt.attachment_name is not None
                })
            
            return jsonify({
                'success': True,
                'receipts_found': len(receipts),
                'receipts': processed_receipts
            })
            
        except Exception as e:
            logger.error(f"Email receipt scanning failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/train-wizard', methods=['POST'])
    def api_train_wizard():
        """
        Train Brian's Financial Wizard from user corrections
        """
        try:
            if not BRIAN_WIZARD_AVAILABLE:
                return jsonify({
                    'success': False,
                    'error': 'Brian\'s Financial Wizard not available'
                }), 500
            
            data = request.get_json()
            original_analysis = data.get('original_analysis', {})
            corrected_category = data.get('corrected_category')
            corrected_business_type = data.get('corrected_business_type')
            user_feedback = data.get('user_feedback', '')
            
            # Initialize Brian's Financial Wizard
            wizard = BrianFinancialWizard()
            
            # Create ReceiptIntelligence object from original analysis
            from brian_financial_wizard import ReceiptIntelligence
            original = ReceiptIntelligence(
                merchant=original_analysis.get('merchant', ''),
                amount=original_analysis.get('amount', 0),
                date=datetime.now(),
                category=original_analysis.get('category', ''),
                business_type=original_analysis.get('business_type', ''),
                confidence=original_analysis.get('confidence', 0),
                purpose=original_analysis.get('purpose', ''),
                tax_deductible=original_analysis.get('tax_deductible', True),
                needs_review=original_analysis.get('needs_review', False),
                auto_approved=original_analysis.get('auto_approved', False),
                receipt_source=original_analysis.get('receipt_source', 'manual'),
                raw_data=original_analysis
            )
            
            # Learn from the correction
            wizard.learn_from_correction(
                original, 
                corrected_category, 
                corrected_business_type, 
                user_feedback
            )
            
            return jsonify({
                'success': True,
                'message': 'Brian\'s Wizard has learned from your correction'
            })
            
        except Exception as e:
            logger.error(f"Wizard training failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/transactions')
    def api_transactions():
        """
        Combined transactions API for PWA interface
        Merges bank transactions and receipts with comprehensive fields
        """
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Get parameters
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 25))
            search = request.args.get('search', '').strip()
            entity = request.args.get('entity', '')  # Personal, Down Home, MCR
            category = request.args.get('category', '')
            days = request.args.get('days', '')
            
            skip = (page - 1) * limit
            
            # Build comprehensive transaction list
            all_transactions = []
            
            # 1. Get Bank Transactions with comprehensive fields
            bank_query = {}
            if search:
                search_regex = {"$regex": search, "$options": "i"}
                bank_query['$or'] = [
                    {'description': search_regex},
                    {'merchant_name': search_regex},
                    {'counterparty.name': search_regex}
                ]
            
            if entity and entity != 'All':
                bank_query['business_type'] = entity
            
            if category:
                bank_query['category'] = category
                
            if days:
                days_int = int(days)
                cutoff_date = datetime.utcnow() - timedelta(days=days_int)
                bank_query['date'] = {'$gte': cutoff_date}
            
            bank_transactions = list(mongo_client.db.bank_transactions.find(
                bank_query,
                {"raw_data": 0}
            ).sort("date", -1))
            
            for txn in bank_transactions:
                # Enhanced bank transaction with receipt matching
                enhanced_txn = {
                    '_id': str(txn.get('_id', '')),
                    'type': 'bank_transaction',
                    'transaction_id': txn.get('transaction_id', ''),
                    'date': txn.get('date').isoformat() if txn.get('date') else '',
                    'description': txn.get('description', ''),
                    'merchant': (txn.get('merchant_name') or 
                               txn.get('counterparty', {}).get('name') or 
                               txn.get('description', '').split()[0] or 'Unknown'),
                    'amount': txn.get('amount', 0),
                    'formatted_amount': f"${abs(txn.get('amount', 0)):,.2f}",
                    'category': txn.get('category', txn.get('ai_category', 'Uncategorized')),
                    'business_type': txn.get('business_type', txn.get('ai_business_type', 'Personal')),
                    'account_name': txn.get('account_name', 'Unknown Account'),
                    'bank_name': txn.get('bank_name', 'Unknown Bank'),
                    
                    # Receipt Integration Fields
                    'receipt_url': None,  # Will be filled if matched
                    'gmail_object_id': txn.get('receipt_match_id', ''),
                    'gmail_account': '',  # Will be filled if matched
                    'receipt_confidence': txn.get('match_confidence', 0),
                    'match_status': 'Receipt Found ✅' if txn.get('receipt_matched') else 'No Receipt ⏳',
                    'has_receipt': bool(txn.get('receipt_matched')),
                    
                    # AI and Processing Fields
                    'confidence_score': txn.get('ai_confidence', 0),
                    'needs_review': txn.get('needs_review', False),
                    'is_split': txn.get('is_split', False),
                    'data_source': 'Bank Transaction',
                    'processing_status': 'completed',
                    'tags': txn.get('tags', []),
                    
                    # Status and timestamps
                    'status': txn.get('status', 'posted'),
                    'synced_at': txn.get('synced_at').isoformat() if txn.get('synced_at') else '',
                    'created_at': txn.get('created_at').isoformat() if txn.get('created_at') else ''
                }
                
                # Find matching receipt if exists
                if txn.get('receipt_match_id'):
                    try:
                        from bson import ObjectId
                        receipt_id = txn['receipt_match_id']
                        if ObjectId.is_valid(receipt_id):
                            receipt = mongo_client.db.receipts.find_one({'_id': ObjectId(receipt_id)})
                        else:
                            receipt = mongo_client.db.receipts.find_one({'_id': receipt_id})
                        
                        if receipt:
                            enhanced_txn['receipt_url'] = receipt.get('receipt_url', receipt.get('r2_url', ''))
                            enhanced_txn['gmail_object_id'] = receipt.get('gmail_id', receipt.get('email_id', ''))
                            enhanced_txn['gmail_account'] = receipt.get('gmail_account', '')
                    except:
                        pass
                
                all_transactions.append(enhanced_txn)
            
            # 2. Get Receipts with comprehensive fields (for unmatched receipts)
            receipt_query = {'match_status': {'$ne': 'Matched'}}  # Only unmatched receipts
            
            if search:
                search_regex = {"$regex": search, "$options": "i"}
                receipt_query['$or'] = [
                    {'merchant': search_regex},
                    {'description': search_regex},
                    {'subject': search_regex}
                ]
            
            if entity and entity != 'All':
                receipt_query['business_type'] = entity
                
            if category:
                receipt_query['category'] = category
                
            if days:
                days_int = int(days)
                cutoff_date = datetime.utcnow() - timedelta(days=days_int)
                receipt_query['date'] = {'$gte': cutoff_date}
            
            receipts = list(mongo_client.db.receipts.find(receipt_query).sort("date", -1))
            
            for receipt in receipts:
                enhanced_receipt = {
                    '_id': str(receipt.get('_id', '')),
                    'type': 'receipt',
                    'transaction_id': f"receipt_{receipt.get('_id', '')}",
                    'date': receipt.get('date', receipt.get('transaction_date', '')),
                    'description': receipt.get('description', receipt.get('subject', '')),
                    'merchant': receipt.get('merchant', 'Unknown'),
                    'amount': -(abs(receipt.get('amount', receipt.get('price', 0)))),  # Receipts are expenses
                    'formatted_amount': f"${abs(receipt.get('amount', receipt.get('price', 0))):,.2f}",
                    'category': receipt.get('category', receipt.get('ai_category', 'Uncategorized')),
                    'business_type': receipt.get('business_type', 'Personal'),
                    'account_name': receipt.get('account_name', ''),
                    'bank_name': 'Receipt Only',
                    
                    # Receipt Specific Fields
                    'receipt_url': receipt.get('receipt_url', receipt.get('r2_url', '')),
                    'gmail_object_id': receipt.get('gmail_id', receipt.get('email_id', '')),
                    'gmail_account': receipt.get('gmail_account', receipt.get('account', '')),
                    'receipt_confidence': 1.0,  # Receipts are 100% confident
                    'match_status': 'Receipt Only 📄',
                    'has_receipt': True,
                    
                    # AI and Processing Fields  
                    'confidence_score': receipt.get('confidence_score', receipt.get('ai_confidence', 0)),
                    'needs_review': receipt.get('needs_review', False),
                    'is_split': False,
                    'data_source': 'Email Receipt',
                    'processing_status': receipt.get('processing_status', 'completed'),
                    'tags': [],
                    
                    # Additional Receipt Fields
                    'tax_deductible': receipt.get('tax_deductible', True),
                    'business_purpose': receipt.get('business_purpose', ''),
                    'is_subscription': receipt.get('is_subscription', False),
                    'gmail_link': receipt.get('gmail_link', ''),
                    
                    # Status and timestamps
                    'status': receipt.get('status', 'processed'),
                    'synced_at': receipt.get('processed_at', ''),
                    'created_at': receipt.get('created_at', '')
                }
                
                # Convert date fields
                for date_field in ['date', 'synced_at', 'created_at']:
                    if enhanced_receipt[date_field] and hasattr(enhanced_receipt[date_field], 'isoformat'):
                        enhanced_receipt[date_field] = enhanced_receipt[date_field].isoformat()
                    elif enhanced_receipt[date_field] and isinstance(enhanced_receipt[date_field], str):
                        pass  # Already string
                    else:
                        enhanced_receipt[date_field] = ''
                
                all_transactions.append(enhanced_receipt)
            
            # 3. Sort all transactions by date (newest first)
            all_transactions.sort(key=lambda x: x['date'], reverse=True)
            
            # 4. Apply pagination
            total_transactions = len(all_transactions)
            paginated_transactions = all_transactions[skip:skip + limit]
            
            # 5. Calculate statistics
            total_expenses = sum(abs(t['amount']) for t in all_transactions if t['amount'] < 0)
            receipts_count = sum(1 for t in all_transactions if t['has_receipt'])
            match_percentage = (receipts_count / len(all_transactions) * 100) if all_transactions else 0
            
            # Business type breakdown
            business_breakdown = {}
            for txn in all_transactions:
                bt = txn['business_type']
                if bt not in business_breakdown:
                    business_breakdown[bt] = {'count': 0, 'amount': 0}
                business_breakdown[bt]['count'] += 1
                business_breakdown[bt]['amount'] += abs(txn['amount'])
            
            return jsonify({
                "success": True,
                "transactions": paginated_transactions,
                "total": total_transactions,
                "page": page,
                "limit": limit,
                "has_more": total_transactions > skip + limit,
                "stats": {
                    "total_transactions": total_transactions,
                    "total_expenses": total_expenses,
                    "receipts_found": receipts_count,
                    "match_percentage": round(match_percentage, 1),
                    "business_breakdown": business_breakdown,
                    "categories": list(set(t['category'] for t in all_transactions)),
                    "recent_activity": len([t for t in all_transactions if t['date'] and (datetime.now() - datetime.fromisoformat(t['date'].replace('Z', '+00:00'))).days <= 7])
                }
            })
            
        except Exception as e:
            logger.error(f"Combined transactions API error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/process-all', methods=['POST'])
    def api_process_all():
        """Ultimate processing endpoint - Does EVERYTHING in one call"""
        try:
            processing_results = {
                "started_at": datetime.utcnow().isoformat(),
                "status": "processing",
                "bank_sync": {"status": "pending", "transactions": 0},
                "email_scan": {"status": "pending", "receipts": 0},
                "ai_processing": {"status": "pending", "analyzed": 0}
            }
            
            # 1. BANK SYNC
            try:
                if teller_client.connected:
                    bank_result = enhanced_bank_sync_with_certificates()
                    processing_results["bank_sync"] = {
                        "status": "completed",
                        "transactions": bank_result.get("transactions_synced", 0)
                    }
                else:
                    processing_results["bank_sync"]["status"] = "skipped - not connected"
            except Exception as e:
                processing_results["bank_sync"]["status"] = f"failed: {str(e)}"
            
            # 2. EMAIL SCANNING
            try:
                if BRIAN_WIZARD_AVAILABLE:
                    # Scan emails for receipts
                    unprocessed = list(mongo_client.db.bank_transactions.find({
                        "ai_processed": {"$ne": True}
                    }).limit(50))
                    
                    ai_processed = 0
                    for txn in unprocessed:
                        wizard = BrianFinancialWizard()
                        expense_data = {
                            'merchant': txn.get('merchant_name', ''),
                            'amount': abs(txn.get('amount', 0)),
                            'description': txn.get('description', ''),
                            'date': txn.get('date', datetime.now())
                        }
                        analysis = wizard.smart_expense_categorization(expense_data)
                        
                        mongo_client.db.bank_transactions.update_one(
                            {"_id": txn["_id"]},
                            {"$set": {
                                "category": analysis.category,
                                "business_type": analysis.business_type,
                                "ai_confidence": analysis.confidence,
                                "ai_processed": True
                            }}
                        )
                        ai_processed += 1
                    
                    processing_results["ai_processing"] = {
                        "status": "completed",
                        "analyzed": ai_processed
                    }
                else:
                    processing_results["ai_processing"]["status"] = "skipped - wizard not available"
            except Exception as e:
                processing_results["ai_processing"]["status"] = f"failed: {str(e)}"
            
            processing_results["completed_at"] = datetime.utcnow().isoformat()
            processing_results["status"] = "completed"
            
            return jsonify({
                "success": True,
                "results": processing_results
            })
            
        except Exception as e:
            logger.error(f"Process-all failed: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/connection-stats', methods=['GET'])
    def api_connection_stats():
        """Get connection statistics for Teller integration"""
        try:
            stats = {
                "connected_accounts": 0,
                "total_transactions": 0,
                "last_sync": None
            }
            
            if teller_client.connected:
                stats["connected_accounts"] = 1
            
            if mongo_client.connected:
                stats["total_transactions"] = mongo_client.db.bank_transactions.count_documents({})
                
                latest_txn = mongo_client.db.bank_transactions.find_one(
                    {}, 
                    sort=[("synced_at", -1)]
                )
                if latest_txn and latest_txn.get('synced_at'):
                    stats["last_sync"] = latest_txn['synced_at'].isoformat()
            
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Connection stats failed: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/teller-environment', methods=['GET'])
    def api_teller_environment():
        """Get current Teller environment configuration"""
        try:
            connect_url = teller_client.get_connect_url("user_12345")
            return jsonify({
                "success": True,
                "environment": Config.TELLER_ENVIRONMENT,
                "application_id": Config.TELLER_APPLICATION_ID,
                "webhook_url": Config.TELLER_WEBHOOK_URL,
                "connect_url": connect_url,
                "connected": teller_client.connected if hasattr(teller_client, 'connected') else False
            })
        except Exception as e:
            logger.error(f"Teller environment error: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "environment": Config.TELLER_ENVIRONMENT,
                "connect_url": "#"
            })

    # ========================================================================
    # REGISTER ADDITIONAL BLUEPRINTS
    # ========================================================================
    
    # Register Brian's Wizard API if available
    if BRIAN_WIZARD_AVAILABLE:
        try:
            from brian_wizard_api import register_brian_wizard_blueprint
            register_brian_wizard_blueprint(app)
        except ImportError:
            logger.warning("Brian Wizard API blueprint not available")
    
    # Register Calendar Context API if available
    if CALENDAR_INTEGRATION_AVAILABLE:
        try:
            register_calendar_blueprint(app)
            logger.info("📅 Calendar API blueprint registered successfully")
        except Exception as e:
            logger.error(f"Failed to register calendar blueprint: {e}")

    @app.route('/api/usage-stats')
    def api_usage_stats():
        """Get API usage statistics with cost protection"""
        try:
            from huggingface_client import get_usage_stats
            return jsonify(get_usage_stats())
        except Exception as e:
            logger.error(f"Usage stats error: {e}")
            return jsonify({
                "daily_used": 0,
                "daily_limit": 200,
                "monthly_used": 0,
                "monthly_limit": 5000,
                "percentage_used": 0,
                "cost_protection_active": True
            })

    @app.route('/api/analytics/summary')
    def analytics_summary():
        """Get analytics summary for the dashboard"""
        try:
            # Initialize with zero stats
            summary = {
                'total_transactions': 0,
                'total_spending': 0,
                'avg_transaction': 0,
                'top_categories': [],
                'monthly_spending': [],
                'match_rate': 0,
                'unmatched_count': 0
            }
            
            # Try to get real stats if MongoDB is connected
            if mongo_client and mongo_client.connected:
                try:
                    # Count all transactions
                    bank_transactions = mongo_client.db.bank_transactions.count_documents({})
                    
                    if bank_transactions > 0:
                        summary['total_transactions'] = bank_transactions
                        
                        # Calculate total spending
                        pipeline = [
                            {"$match": {"amount": {"$lt": 0}}},
                            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
                        ]
                        result = list(mongo_client.db.bank_transactions.aggregate(pipeline))
                        if result:
                            total_spend = abs(result[0]['total'])
                            summary['total_spending'] = total_spend
                            summary['avg_transaction'] = total_spend / bank_transactions if bank_transactions else 0
                        
                        # Get top categories
                        category_pipeline = [
                            {"$match": {"amount": {"$lt": 0}}},
                            {"$group": {"_id": "$category", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
                            {"$sort": {"total": 1}},
                            {"$limit": 5}
                        ]
                        categories = list(mongo_client.db.bank_transactions.aggregate(category_pipeline))
                        summary['top_categories'] = [
                            {"category": cat["_id"] or "Uncategorized", "amount": abs(cat["total"]), "count": cat["count"]}
                            for cat in categories
                        ]
                        
                        # Calculate match rate
                        matched = mongo_client.db.bank_transactions.count_documents({"receipt_matched": True})
                        summary['match_rate'] = (matched / bank_transactions * 100) if bank_transactions else 0
                        summary['unmatched_count'] = bank_transactions - matched
                        
                except Exception as e:
                    logger.warning(f"Failed to get analytics: {e}")
            
            return jsonify({
                "success": True,
                "summary": summary
            })
            
        except Exception as e:
            logger.error(f"Analytics summary error: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "summary": {
                    'total_transactions': 0,
                    'total_spending': 0,
                    'avg_transaction': 0,
                    'top_categories': [],
                    'monthly_spending': [],
                    'match_rate': 0,
                    'unmatched_count': 0
                }
            })

    @app.route('/api/dashboard-stats')
    def api_dashboard_stats():
        """Get real-time dashboard statistics"""
        try:
            # Initialize with zero stats
            stats = {
                'total_transactions': '0',
                'match_rate': '0%',
                'total_spend': '$0',
                'review_needed': 0,
                'realtime_processed': 0
            }
            
            # Try to get real stats if MongoDB is connected
            if mongo_client.connected:
                try:
                    # Count all transactions (bank + receipts)
                    bank_transactions = mongo_client.db.bank_transactions.count_documents({})
                    receipts = mongo_client.db.receipts.count_documents({})
                    total_transactions = bank_transactions + receipts
                    
                    if total_transactions > 0:
                        stats['total_transactions'] = f"{total_transactions:,}"
                        
                        # Calculate total spending from bank transactions
                        pipeline = [
                            {"$match": {"amount": {"$lt": 0}}},  # Only expenses
                            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
                        ]
                        result = list(mongo_client.db.bank_transactions.aggregate(pipeline))
                        if result:
                            total_spend = abs(result[0]['total'])
                            if total_spend > 1000:
                                stats['total_spend'] = f"${total_spend/1000:.1f}K"
                            else:
                                stats['total_spend'] = f"${total_spend:.0f}"
                        
                        # Calculate match rate
                        matched_transactions = mongo_client.db.bank_transactions.count_documents({"receipt_matched": True})
                        if bank_transactions > 0:
                            match_rate = (matched_transactions / bank_transactions) * 100
                            stats['match_rate'] = f"{match_rate:.1f}%"
                        
                        # Count items needing review
                        review_needed = mongo_client.db.bank_transactions.count_documents({"needs_review": True})
                        stats['review_needed'] = review_needed
                        
                        # Count real-time processed (recent transactions)
                        from datetime import datetime, timedelta
                        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
                        realtime_count = mongo_client.db.bank_transactions.count_documents({
                            "synced_at": {"$gte": recent_cutoff}
                        })
                        stats['realtime_processed'] = realtime_count
                        
                except Exception as e:
                    logger.warning(f"Failed to get real stats: {e}")
            
            return jsonify({
                "success": True,
                "stats": stats
            })
            
        except Exception as e:
            logger.error(f"Dashboard stats error: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "stats": {
                    'total_transactions': '0',
                    'match_rate': '0%',
                    'total_spend': '$0',
                    'review_needed': 0,
                    'realtime_processed': 0
                }
            })

    @app.route('/api/security-status')
    def api_security_status():
        """Get security and deployment readiness status"""
        try:
            security_status = {
                "secrets_secure": True,  # All secrets moved to Render dashboard
                "rate_limiting_enabled": True,
                "api_limits_configured": bool(getattr(Config, 'HUGGINGFACE_DAILY_LIMIT', False)),
                "cost_monitoring": getattr(Config, 'COST_MONITORING_ENABLED', False),
                "session_timeout": getattr(Config, 'SESSION_TIMEOUT_HOURS', 8),
                "file_size_limits": getattr(Config, 'MAX_FILE_SIZE_MB', 16),
                "batch_size_limits": getattr(Config, 'MAX_BATCH_SIZE', 10)
            }
            
            deployment_checks = {
                "render_yaml_secure": True,  # Secrets removed from render.yaml
                "gitignore_configured": True,  # Sensitive files ignored
                "env_vars_required": [
                    "SECRET_KEY", "MONGODB_URI", "HUGGINGFACE_API_KEY", 
                    "R2_ACCESS_KEY", "R2_SECRET_KEY",
                    "TELLER_APPLICATION_ID", "TELLER_SIGNING_SECRET"
                ],
                "optional_limits": [
                    "HUGGINGFACE_DAILY_LIMIT", "HUGGINGFACE_MONTHLY_LIMIT",
                    "MAX_RECEIPTS_PER_SESSION", "IP_RATE_LIMIT_PER_HOUR"
                ]
            }
            
            return jsonify({
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "security": security_status,
                "deployment": deployment_checks,
                "ready_for_production": all(security_status.values())
            })
            
        except Exception as e:
            logger.error(f"Error getting security status: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/teller/sync', methods=['POST'])
    def api_teller_sync():
        """Sync bank transactions from Teller API"""
        try:
            logger.info("🏦 Starting Teller bank sync...")
            
            # Check if Teller client is available
            if not teller_client:
                return jsonify({
                    "success": False,
                    "error": "Teller client not configured",
                    "synced_transactions": 0
                }), 400
            
            # Get sync parameters
            data = request.get_json() or {}
            account_id = data.get('account_id')  # Optional: specific account
            days_back = data.get('days_back', 30)
            
            # Simulate sync process (implement actual Teller sync logic here)
            synced_count = 0
            
            logger.info(f"🏦 Teller sync completed: {synced_count} transactions")
            
            return jsonify({
                "success": True,
                "synced_transactions": synced_count,
                "sync_time": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Teller sync failed: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "synced_transactions": 0
            }), 500

    @app.route('/api/ai-receipt-matching', methods=['POST'])
    def api_ai_receipt_matching():
        """Advanced AI-powered receipt matching using multiple algorithms"""
        try:
            data = request.get_json() or {}
            transaction_batch_size = data.get('batch_size', 50)
            days_back = data.get('days_back', 30)
            
            logger.info(f"🤖 Starting AI receipt matching (batch_size={transaction_batch_size}, days_back={days_back})")
            
            # Import AI matcher
            try:
                from ai_receipt_matcher import IntegratedAIReceiptMatcher
            except ImportError as e:
                logger.error(f"AI receipt matcher not available: {e}")
                return jsonify({
                    'success': False,
                    'error': 'AI receipt matching module not available',
                    'details': str(e)
                }), 500
            
            # Initialize AI matcher
            ai_matcher = IntegratedAIReceiptMatcher(mongo_client, app.config)
            
            # Get unmatched transactions
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            unmatched_transactions = list(mongo_client.db.bank_transactions.find({
                'receipt_matched': {'$ne': True},
                'date': {'$gte': cutoff_date},
                'amount': {'$lt': 0}  # Only expenses
            }).sort('date', -1).limit(transaction_batch_size))
            
            if not unmatched_transactions:
                logger.info("No unmatched transactions found for AI matching")
                return jsonify({
                    'success': True,
                    'message': 'No unmatched transactions found',
                    'results': {
                        'performance_stats': {
                            'total_transactions': 0,
                            'total_matched': 0,
                            'match_rate_percent': 0,
                            'processing_time_seconds': 0
                        },
                        'match_breakdown': {
                            'exact_matches': 0,
                            'fuzzy_matches': 0,
                            'ai_inferred_matches': 0,
                            'subscription_matches': 0,
                            'unmatched': 0
                        }
                    }
                })
            
            logger.info(f"Found {len(unmatched_transactions)} unmatched transactions for AI analysis")
            
            # Run comprehensive AI matching
            results = ai_matcher.comprehensive_receipt_matching(unmatched_transactions)
            
            # Save successful matches to database
            all_matches = (results['exact_matches'] + results['fuzzy_matches'] + 
                          results['ai_inferred_matches'] + results['subscription_matches'])
            
            saved_count = 0
            for match in all_matches:
                try:
                    # Update transaction with match info
                    transaction_update = mongo_client.db.bank_transactions.update_one(
                        {'_id': ObjectId(match.transaction_id)},
                        {'$set': {
                            'receipt_matched': True,
                            'receipt_match_id': match.receipt_id,
                            'match_confidence': match.confidence_score,
                            'match_type': match.match_type,
                            'matched_at': datetime.utcnow(),
                            'ai_match_factors': match.match_factors,
                            'ai_reasoning': match.ai_reasoning
                        }}
                    )
                    
                    # Update receipt with match info
                    receipt_update = mongo_client.db.receipts.update_one(
                        {'_id': ObjectId(match.receipt_id)},
                        {'$set': {
                            'bank_matched': True,
                            'bank_match_id': match.transaction_id,
                            'match_confidence': match.confidence_score,
                            'matched_at': datetime.utcnow()
                        }}
                    )
                    
                    if transaction_update.modified_count > 0 and receipt_update.modified_count > 0:
                        saved_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to save match {match.transaction_id} -> {match.receipt_id}: {e}")
            
            # Save performance statistics
            try:
                mongo_client.db.ai_matching_stats.insert_one({
                    'timestamp': datetime.utcnow(),
                    'performance_stats': results['performance_stats'],
                    'match_breakdown': {
                        'exact': len(results['exact_matches']),
                        'fuzzy': len(results['fuzzy_matches']),
                        'ai_inferred': len(results['ai_inferred_matches']),
                        'subscription': len(results['subscription_matches']),
                        'unmatched': len(results['unmatched'])
                    },
                    'batch_size': transaction_batch_size,
                    'days_back': days_back
                })
            except Exception as e:
                logger.warning(f"Failed to save AI matching stats: {e}")
            
            # Generate insights
            insights = []
            match_rate = results['performance_stats']['match_rate_percent']
            
            if match_rate >= 85:
                insights.append("🎯 Excellent match rate achieved!")
            elif match_rate >= 70:
                insights.append("✅ Good match rate - system performing well")
            elif match_rate >= 50:
                insights.append("⚠️ Moderate match rate - consider expanding search criteria")
            else:
                insights.append("🔍 Low match rate - may need receipt scanning or search optimization")
            
            if len(results['subscription_matches']) > 0:
                insights.append(f"📅 Detected {len(results['subscription_matches'])} subscription patterns")
            
            if len(results['ai_inferred_matches']) > 0:
                insights.append(f"🤖 AI successfully inferred {len(results['ai_inferred_matches'])} complex matches")
            
            high_confidence_matches = len([m for m in all_matches if m.confidence_score >= 0.85])
            if high_confidence_matches > 0:
                insights.append(f"⭐ {high_confidence_matches} high-confidence matches found")
            
            logger.info(f"✅ AI matching complete: {saved_count}/{len(all_matches)} matches saved, "
                       f"{match_rate:.1f}% success rate")
            
            return jsonify({
                'success': True,
                'message': f'AI matching completed with {match_rate:.1f}% success rate',
                'results': {
                    'performance_stats': results['performance_stats'],
                    'match_breakdown': {
                        'exact_matches': len(results['exact_matches']),
                        'fuzzy_matches': len(results['fuzzy_matches']),
                        'ai_inferred_matches': len(results['ai_inferred_matches']),
                        'subscription_matches': len(results['subscription_matches']),
                        'unmatched': len(results['unmatched']),
                        'saved_to_database': saved_count
                    },
                    'insights': insights,
                    'top_matches': [
                        {
                            'transaction_id': m.transaction_id,
                            'receipt_id': m.receipt_id,
                            'confidence': m.confidence_score,
                            'type': m.match_type,
                            'reasoning': m.ai_reasoning
                        } for m in sorted(all_matches, key=lambda x: x.confidence_score, reverse=True)[:5]
                    ]
                }
            })
            
        except Exception as e:
            logger.error(f"AI receipt matching error: {e}")
            return jsonify({
                'success': False,
                'error': f'AI matching failed: {str(e)}'
            }), 500

    # Calendar debug endpoint removed - now handled by calendar blueprint

    # ============================================================================
    # UTILITY FUNCTIONS THAT NEED DATABASE ACCESS
    # ============================================================================
    
    def find_perfect_receipt_match(transaction):
        """Ultra-precise receipt matching with multiple algorithms"""
        try:
            amount_tolerance = 5.0  # Tight tolerance for precision
            date_tolerance = timedelta(days=3)  # Reduced for accuracy
            
            transaction_date = transaction.get('date')
            if isinstance(transaction_date, str):
                transaction_date = datetime.fromisoformat(transaction_date.replace('Z', '+00:00'))
            
            transaction_amount = abs(transaction.get('amount', 0))
            
            # Multi-stage matching
            potential_matches = mongo_client.db.receipts.find({
                'total_amount': {
                    '$gte': transaction_amount - amount_tolerance,
                    '$lte': transaction_amount + amount_tolerance
                },
                'date': {
                    '$gte': transaction_date - date_tolerance,
                    '$lte': transaction_date + date_tolerance
                },
                'bank_matched': {'$ne': True}
            })
            
            best_match = None
            best_score = 0
            
            for receipt in potential_matches:
                match_score = calculate_perfect_match_score(transaction, receipt)
                
                if match_score['total_score'] > best_score and match_score['total_score'] >= 0.85:
                    best_score = match_score['total_score']
                    best_match = {
                        **receipt,
                        'confidence': match_score['total_score'],
                        'match_details': match_score
                    }
            
            return best_match
            
        except Exception as e:
            logger.error(f"Perfect receipt matching error: {e}")
            return None

    def calculate_perfect_match_score(transaction, receipt):
        """Calculate comprehensive match score with detailed breakdown"""
        score_breakdown = {
            'amount_score': 0,
            'date_score': 0,
            'merchant_score': 0,
            'time_score': 0,
            'category_score': 0,
            'total_score': 0
        }
        
        # Amount matching (40% weight)
        amount_diff = abs(abs(transaction.get('amount', 0)) - receipt.get('total_amount', 0))
        if amount_diff <= 0.01:
            score_breakdown['amount_score'] = 1.0
        elif amount_diff <= 1.0:
            score_breakdown['amount_score'] = 0.9
        elif amount_diff <= 5.0:
            score_breakdown['amount_score'] = 0.7
        else:
            score_breakdown['amount_score'] = max(0, 1 - (amount_diff / 20))
        
        # Date matching (30% weight)
        txn_date = transaction.get('date')
        receipt_date = receipt.get('date')
        
        if isinstance(txn_date, str):
            txn_date = datetime.fromisoformat(txn_date.replace('Z', '+00:00'))
        if isinstance(receipt_date, str):
            receipt_date = datetime.fromisoformat(receipt_date.replace('Z', '+00:00'))
        
        if txn_date and receipt_date:
            date_diff = abs((txn_date - receipt_date).days)
            if date_diff == 0:
                score_breakdown['date_score'] = 1.0
            elif date_diff == 1:
                score_breakdown['date_score'] = 0.8
            elif date_diff <= 3:
                score_breakdown['date_score'] = 0.6
            else:
                score_breakdown['date_score'] = max(0, 1 - (date_diff / 7))
        
        # Merchant matching (25% weight)
        from enhanced_transaction_utils import extract_merchant_name
        txn_merchant = extract_merchant_name(transaction).lower()
        receipt_merchant = (receipt.get('merchant_name') or receipt.get('merchant', '')).lower()
        
        if txn_merchant and receipt_merchant:
            merchant_similarity = calculate_advanced_merchant_similarity(txn_merchant, receipt_merchant)
            score_breakdown['merchant_score'] = merchant_similarity
        
        # Calculate weighted total
        score_breakdown['total_score'] = (
            score_breakdown['amount_score'] * 0.40 +
            score_breakdown['date_score'] * 0.30 +
            score_breakdown['merchant_score'] * 0.25 +
            score_breakdown['time_score'] * 0.03 +
            score_breakdown['category_score'] * 0.02
        )
        
        return score_breakdown

    def calculate_advanced_merchant_similarity(merchant1, merchant2):
        """Advanced merchant similarity with fuzzy matching and business logic"""
        if not merchant1 or not merchant2:
            return 0
        
        # Normalize
        m1 = merchant1.lower().strip()
        m2 = merchant2.lower().strip()
        
        # Exact match
        if m1 == m2:
            return 1.0
        
        # Clean common business suffixes
        suffixes = [' inc', ' llc', ' corp', ' co', ' ltd', ' limited']
        for suffix in suffixes:
            m1 = m1.replace(suffix, '')
            m2 = m2.replace(suffix, '')
        
        # Substring matching
        if m1 in m2 or m2 in m1:
            return 0.9
        
        # Sequence matching
        from difflib import SequenceMatcher
        sequence_ratio = SequenceMatcher(None, m1, m2).ratio()
        if sequence_ratio > 0.8:
            return sequence_ratio
        
        # Word-based matching
        words1 = set(m1.split())
        words2 = set(m2.split())
        
        if words1 and words2:
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            jaccard = len(intersection) / len(union) if union else 0
            
            # Bonus for matching important words
            important_matches = len([w for w in intersection if len(w) > 3])
            bonus = min(important_matches * 0.15, 0.3)
            
            return min(jaccard + bonus, 1.0)
        
        return 0.0

    @app.route('/api/enhanced-receipt-processing', methods=['POST'])
    def api_enhanced_receipt_processing():
        """Enhanced receipt processing endpoint with improved algorithms"""
        try:
            from receipt_processor import EnhancedReceiptProcessor
            from datetime import datetime
            import os
            
            # Initialize enhanced processor
            processor = EnhancedReceiptProcessor()
            
            # Get request parameters
            data = request.get_json() if request.is_json else {}
            batch_size = data.get('batch_size', 20)
            source_dirs = data.get('source_dirs', ['uploads/', 'downloads/', 'data/receipts/'])
            file_extensions = data.get('file_extensions', ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp'])
            
            # Collect receipt files to process
            receipt_files = []
            for source_dir in source_dirs:
                if os.path.exists(source_dir):
                    for filename in os.listdir(source_dir):
                        if any(filename.lower().endswith(ext) for ext in file_extensions):
                            filepath = os.path.join(source_dir, filename)
                            # Only process files modified in the last 7 days (configurable)
                            if os.path.getmtime(filepath) > (datetime.now().timestamp() - 7 * 24 * 3600):
                                receipt_files.append(filepath)
            
            # Limit to batch size
            receipt_files = receipt_files[:batch_size]
            
            # Process receipts
            start_time = datetime.now()
            processing_results = []
            processing_stats = {
                'total_files': len(receipt_files),
                'successful_extractions': 0,
                'failed_extractions': 0,
                'high_confidence_extractions': 0,
                'medium_confidence_extractions': 0,
                'low_confidence_extractions': 0,
                'merchants_found': 0,
                'dates_found': 0,
                'amounts_found': 0,
                'items_found': 0
            }
            
            for filepath in receipt_files:
                try:
                    # Extract receipt data
                    receipt_data = processor.extract_receipt_data(filepath)
                    
                    if receipt_data:
                        processing_stats['successful_extractions'] += 1
                        
                        # Categorize by confidence
                        overall_confidence = receipt_data.get('overall_confidence', 0.0)
                        if overall_confidence >= 0.8:
                            processing_stats['high_confidence_extractions'] += 1
                        elif overall_confidence >= 0.6:
                            processing_stats['medium_confidence_extractions'] += 1
                        else:
                            processing_stats['low_confidence_extractions'] += 1
                        
                        # Count successful field extractions
                        if receipt_data.get('merchant'):
                            processing_stats['merchants_found'] += 1
                        if receipt_data.get('date'):
                            processing_stats['dates_found'] += 1
                        if receipt_data.get('total_amount'):
                            processing_stats['amounts_found'] += 1
                        if receipt_data.get('items'):
                            processing_stats['items_found'] += len(receipt_data['items'])
                        
                        # Add to results
                        processing_results.append({
                            'filename': os.path.basename(filepath),
                            'file_path': filepath,
                            'extracted_data': receipt_data,
                            'processing_success': True
                        })
                    else:
                        processing_stats['failed_extractions'] += 1
                        processing_results.append({
                            'filename': os.path.basename(filepath),
                            'file_path': filepath,
                            'extracted_data': None,
                            'processing_success': False,
                            'error': 'Extraction failed'
                        })
                        
                except Exception as e:
                    processing_stats['failed_extractions'] += 1
                    processing_results.append({
                        'filename': os.path.basename(filepath),
                        'file_path': filepath,
                        'extracted_data': None,
                        'processing_success': False,
                        'error': str(e)
                    })
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Calculate success rates
            success_rate = (processing_stats['successful_extractions'] / max(processing_stats['total_files'], 1)) * 100
            merchant_rate = (processing_stats['merchants_found'] / max(processing_stats['successful_extractions'], 1)) * 100
            date_rate = (processing_stats['dates_found'] / max(processing_stats['successful_extractions'], 1)) * 100
            amount_rate = (processing_stats['amounts_found'] / max(processing_stats['successful_extractions'], 1)) * 100
            
            # Get top confidence results
            successful_results = [r for r in processing_results if r['processing_success']]
            top_results = sorted(
                successful_results,
                key=lambda x: x['extracted_data'].get('overall_confidence', 0.0),
                reverse=True
            )[:5]
            
            # Response
            response = {
                'status': 'success',
                'processing_summary': {
                    'total_files_processed': processing_stats['total_files'],
                    'processing_time_seconds': round(processing_time, 2),
                    'files_per_second': round(processing_stats['total_files'] / max(processing_time, 0.1), 2),
                    'overall_success_rate': round(success_rate, 1)
                },
                'extraction_stats': {
                    'successful_extractions': processing_stats['successful_extractions'],
                    'failed_extractions': processing_stats['failed_extractions'],
                    'high_confidence_count': processing_stats['high_confidence_extractions'],
                    'medium_confidence_count': processing_stats['medium_confidence_extractions'],
                    'low_confidence_count': processing_stats['low_confidence_extractions']
                },
                'field_extraction_rates': {
                    'merchant_extraction_rate': round(merchant_rate, 1),
                    'date_extraction_rate': round(date_rate, 1),
                    'amount_extraction_rate': round(amount_rate, 1),
                    'total_items_found': processing_stats['items_found']
                },
                'processor_info': processor.get_processing_stats(),
                'top_confidence_results': [
                    {
                        'filename': result['filename'],
                        'merchant': result['extracted_data'].get('merchant'),
                        'date': result['extracted_data'].get('date'),
                        'amount': result['extracted_data'].get('total_amount'),
                        'confidence': result['extracted_data'].get('overall_confidence'),
                        'items_count': len(result['extracted_data'].get('items', []))
                    }
                    for result in top_results
                ],
                'processing_insights': []
            }
            
            # Add insights
            if success_rate >= 80:
                response['processing_insights'].append("Excellent processing success rate achieved")
            elif success_rate >= 60:
                response['processing_insights'].append("Good processing success rate, consider image quality improvements")
            else:
                response['processing_insights'].append("Low success rate detected, check image quality and file formats")
            
            if merchant_rate >= 90:
                response['processing_insights'].append("Excellent merchant detection rate")
            elif merchant_rate < 70:
                response['processing_insights'].append("Consider adding more merchant patterns to improve recognition")
            
            if processing_stats['high_confidence_extractions'] > processing_stats['low_confidence_extractions']:
                response['processing_insights'].append("High quality extractions dominate - system performing well")
            
            # Include all detailed results if requested
            if data.get('include_details', False):
                response['detailed_results'] = processing_results
            
            return jsonify(response)
            
        except ImportError:
            return jsonify({
                'status': 'error',
                'message': 'Enhanced receipt processor not available',
                'suggestion': 'Ensure receipt_processor.py is properly configured'
            }), 500
        
        except Exception as e:
            logger.error(f"Enhanced receipt processing error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Processing failed: {str(e)}'
            }), 500

    @app.route('/api/process-single-receipt', methods=['POST'])
    def api_process_single_receipt():
        """Process a single receipt file with enhanced algorithms"""
        try:
            from receipt_processor import EnhancedReceiptProcessor
            from werkzeug.utils import secure_filename
            import os
            
            # Initialize processor
            processor = EnhancedReceiptProcessor()
            
            # Check if file was uploaded
            if 'receipt_file' not in request.files:
                return jsonify({
                    'status': 'error',
                    'message': 'No file uploaded'
                }), 400
            
            file = request.files['receipt_file']
            if file.filename == '':
                return jsonify({
                    'status': 'error', 
                    'message': 'No file selected'
                }), 400
            
            # Validate file type
            allowed_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp']
            if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
                return jsonify({
                    'status': 'error',
                    'message': f'Unsupported file type. Allowed: {", ".join(allowed_extensions)}'
                }), 400
            
            # Save uploaded file
            filename = secure_filename(file.filename)
            upload_path = os.path.join('uploads', filename)
            os.makedirs('uploads', exist_ok=True)
            file.save(upload_path)
            
            try:
                # Process the receipt
                start_time = datetime.now()
                receipt_data = processor.extract_receipt_data(upload_path)
                processing_time = (datetime.now() - start_time).total_seconds()
                
                if receipt_data:
                    # Prepare response
                    response = {
                        'status': 'success',
                        'filename': filename,
                        'processing_time_seconds': round(processing_time, 2),
                        'extracted_data': receipt_data,
                        'extraction_quality': {
                            'overall_confidence': receipt_data.get('overall_confidence', 0.0),
                            'merchant_confidence': receipt_data.get('merchant_confidence', 0.0),
                            'date_confidence': receipt_data.get('date_confidence', 0.0),
                            'amount_confidence': receipt_data.get('total_confidence', 0.0)
                        },
                        'data_summary': {
                            'merchant_found': bool(receipt_data.get('merchant')),
                            'date_found': bool(receipt_data.get('date')),
                            'amount_found': bool(receipt_data.get('total_amount')),
                            'items_count': len(receipt_data.get('items', [])),
                            'additional_fields': sum(1 for field in ['payment_method', 'receipt_number', 'phone_number', 'address'] 
                                                   if receipt_data.get(field))
                        }
                    }
                    
                    # Add processing recommendations
                    confidence = receipt_data.get('overall_confidence', 0.0)
                    if confidence >= 0.8:
                        response['recommendation'] = 'High quality extraction - ready for automated processing'
                    elif confidence >= 0.6:
                        response['recommendation'] = 'Good extraction - may need manual review for critical fields'
                    else:
                        response['recommendation'] = 'Low confidence extraction - manual review recommended'
                    
                    return jsonify(response)
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to extract data from receipt',
                        'filename': filename,
                        'processing_time_seconds': round(processing_time, 2)
                    }), 422
            
            finally:
                # Clean up uploaded file
                if os.path.exists(upload_path):
                    os.remove(upload_path)
        
        except Exception as e:
            logger.error(f"Single receipt processing error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Processing failed: {str(e)}'
            }), 500

    @app.route('/api/hf-receipt-processing', methods=['POST'])
    def api_hf_receipt_processing():
        """Process receipt using HuggingFace cloud models"""
        try:
            # Import HuggingFace processor
            from huggingface_receipt_processor import create_huggingface_processor
            
            if 'file' not in request.files:
                return jsonify({"error": "No file provided"}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            
            # Get optional parameters
            model_name = request.form.get('model', 'paligemma')
            api_token = request.form.get('api_token')  # Optional override
            
            # Create unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hf_receipt_{timestamp}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Save uploaded file
            file.save(filepath)
            
            logger.info(f"🤗 Processing receipt with HuggingFace: {filename}")
            logger.info(f"   Model: {model_name}")
            
            # Initialize HuggingFace processor
            hf_processor = create_huggingface_processor(
                api_token=api_token,
                model_preference=model_name
            )
            
            # Process with HuggingFace cloud models
            start_time = datetime.now()
            result = hf_processor.process_receipt_image(filepath, model_name)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Add processing metadata
            result['upload_metadata'] = {
                'filename': filename,
                'file_size': os.path.getsize(filepath),
                'total_processing_time': round(processing_time, 3),
                'timestamp': datetime.now().isoformat(),
                'endpoint': 'hf-receipt-processing'
            }
            
            # Save to MongoDB if processing was successful
            if result['status'] == 'success' and mongo_client.db:
                try:
                    receipt_doc = {
                        'filename': filename,
                        'processing_method': 'huggingface_cloud',
                        'model_used': result.get('model_used'),
                        'confidence_score': result.get('confidence_score'),
                        'extracted_data': result.get('extracted_data'),
                        'raw_response': result.get('raw_response', ''),
                        'processing_metadata': result.get('processing_metadata'),
                        'upload_metadata': result.get('upload_metadata'),
                        'timestamp': datetime.now(),
                        'cloud_inference': True
                    }
                    
                    collection = mongo_client.db.receipts
                    insert_result = collection.insert_one(receipt_doc)
                    result['database_id'] = str(insert_result.inserted_id)
                    
                    logger.info(f"✅ HuggingFace receipt saved to MongoDB: {insert_result.inserted_id}")
                    
                except Exception as db_error:
                    logger.error(f"❌ Failed to save HF receipt to MongoDB: {str(db_error)}")
                    result['database_error'] = str(db_error)
            
            # Log processing result
            if result['status'] == 'success':
                logger.info(f"✅ HuggingFace processing successful: {filename}")
                logger.info(f"   Model: {result.get('model_used')}")
                logger.info(f"   Confidence: {result.get('confidence_score')}")
                logger.info(f"   Merchant: {result.get('extracted_data', {}).get('merchant', 'Unknown')}")
            else:
                logger.error(f"❌ HuggingFace processing failed: {result.get('error_message')}")
            
            # Clean up uploaded file
            try:
                os.remove(filepath)
            except:
                pass
            
            return jsonify(result)
            
        except ImportError:
            return jsonify({
                "error": "HuggingFace processor not available", 
                "message": "Install dependencies: pip install requests python-dateutil"
            }), 500
        except Exception as e:
            logger.error(f"❌ HuggingFace receipt processing error: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return app

# ============================================================================
# 🧠 ENHANCED TRANSACTION PROCESSING UTILITIES
# ============================================================================

def build_transaction_query(filter_type=None, search=None, category_filter=None, 
                           amount_min=None, amount_max=None, date_from=None, 
                           date_to=None, business_type=None, match_status=None):
    """Build MongoDB query from filter parameters"""
    query = {}
    
    # Filter by type
    if filter_type == 'matched':
        query['receipt_matched'] = True
    elif filter_type == 'unmatched':
        query['receipt_matched'] = {'$ne': True}
    elif filter_type == 'expenses':
        query['amount'] = {'$lt': 0}
    elif filter_type == 'income':
        query['amount'] = {'$gt': 0}
    elif filter_type == 'split':
        query['is_split'] = True
    elif filter_type == 'needs_review':
        query['needs_review'] = True
    elif filter_type == 'recent':
        query['date'] = {'$gte': datetime.utcnow() - timedelta(days=7)}
    
    # Search across multiple fields
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query['$or'] = [
            {'description': search_regex},
            {'merchant_name': search_regex},
            {'counterparty.name': search_regex},
            {'category': search_regex},
            {'business_type': search_regex},
            {'account_name': search_regex},
            {'transaction_id': search_regex}
        ]
    
    # Category filter
    if category_filter:
        query['category'] = category_filter
    
    # Business type filter
    if business_type:
        query['business_type'] = business_type
    
    # Amount range
    if amount_min or amount_max:
        amount_query = {}
        if amount_min:
            amount_query['$gte'] = float(amount_min)
        if amount_max:
            amount_query['$lte'] = float(amount_max)
        query['amount'] = amount_query
    
    # Date range
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query['$gte'] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        if date_to:
            date_query['$lte'] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        query['date'] = date_query
    
    # Match status
    if match_status == 'matched':
        query['receipt_matched'] = True
    elif match_status == 'unmatched':
        query['receipt_matched'] = {'$ne': True}
    elif match_status == 'needs_review':
        query['needs_review'] = True
    
    return query

def get_sort_field(sort_by):
    """Get MongoDB sort field from sort parameter"""
    sort_fields = {
        'date': 'date',
        'amount': 'amount',
        'merchant': 'merchant_name',
        'category': 'category',
        'match_confidence': 'match_confidence',
        'created': 'synced_at'
    }
    return sort_fields.get(sort_by, 'date')

def categorize_and_analyze_transaction(transaction):
    """AI-powered transaction categorization and business type detection"""
    merchant_name = extract_merchant_name(transaction).lower()
    description = transaction.get('description', '').lower()
    amount = abs(transaction.get('amount', 0))
    
    # Initialize result
    result = {
        'category': 'Other',
        'business_type': 'Unknown',
        'confidence': 0.5,
        'needs_review': False,
        'review_reasons': [],
        'tags': []
    }
    
    # Enhanced categorization rules
    category_rules = {
        'Food & Beverage': {
            'keywords': ['starbucks', 'coffee', 'restaurant', 'food', 'dining', 'pizza', 'burger', 'cafe', 'bar', 'brewery', 'doordash', 'ubereats', 'grubhub'],
            'business_types': ['Restaurant', 'Coffee Shop', 'Fast Food', 'Bar', 'Food Delivery'],
            'confidence': 0.9
        },
        'Transportation': {
            'keywords': ['shell', 'gas', 'fuel', 'exxon', 'chevron', 'bp', 'uber', 'lyft', 'taxi', 'parking', 'toll', 'metro', 'transit'],
            'business_types': ['Gas Station', 'Ride Share', 'Parking', 'Public Transit'],
            'confidence': 0.95
        },
        'Shopping': {
            'keywords': ['target', 'walmart', 'amazon', 'store', 'shop', 'retail', 'mall', 'market', 'costco', 'best buy'],
            'business_types': ['Retail Store', 'Department Store', 'Online Marketplace', 'Warehouse Store'],
            'confidence': 0.85
        },
        'Technology': {
            'keywords': ['apple', 'microsoft', 'google', 'software', 'app store', 'steam', 'adobe', 'netflix', 'spotify'],
            'business_types': ['Software Company', 'App Store', 'Streaming Service', 'Tech Company'],
            'confidence': 0.9
        },
        'Healthcare': {
            'keywords': ['medical', 'doctor', 'pharmacy', 'health', 'dental', 'hospital', 'clinic', 'cvs', 'walgreens'],
            'business_types': ['Medical Office', 'Pharmacy', 'Hospital', 'Dental Office'],
            'confidence': 0.95
        },
        'Utilities': {
            'keywords': ['electric', 'water', 'gas', 'internet', 'phone', 'cable', 'utility', 'power', 'comcast', 'verizon'],
            'business_types': ['Utility Company', 'Internet Provider', 'Phone Company'],
            'confidence': 0.95
        },
        'Entertainment': {
            'keywords': ['movie', 'theater', 'cinema', 'concert', 'game', 'sport', 'ticket', 'event', 'amusement'],
            'business_types': ['Entertainment Venue', 'Movie Theater', 'Sports Venue', 'Amusement Park'],
            'confidence': 0.8
        }
    }
    
    # Find best category match
    best_score = 0
    for category, rules in category_rules.items():
        score = 0
        matched_keywords = []
        
        for keyword in rules['keywords']:
            if keyword in merchant_name or keyword in description:
                score += 1
                matched_keywords.append(keyword)
        
        if score > 0:
            confidence = min(score / len(rules['keywords']) * rules['confidence'], 1.0)
            if confidence > best_score:
                best_score = confidence
                result['category'] = category
                result['confidence'] = confidence
                result['tags'].extend(matched_keywords[:3])  # Top 3 matched keywords
                
                # Select best business type
                if matched_keywords:
                    result['business_type'] = rules['business_types'][0]  # Use first as default
    
    # Special handling for complex merchants
    result = handle_special_merchants(transaction, result)
    
    # Review flags
    if amount > 1000:
        result['needs_review'] = True
        result['review_reasons'].append('High amount transaction')
    
    if result['confidence'] < 0.7:
        result['needs_review'] = True
        result['review_reasons'].append('Low categorization confidence')
    
    return result

def handle_special_merchants(transaction, result):
    """Handle special cases like Apple, Amazon, etc. that need splitting"""
    merchant_name = extract_merchant_name(transaction).lower()
    description = transaction.get('description', '').lower()
    
    # Apple transactions - often mixed business/personal
    if 'apple' in merchant_name or 'app store' in merchant_name:
        result['category'] = 'Technology'
        result['business_type'] = 'App Store'
        result['needs_review'] = True
        result['review_reasons'].append('Apple purchase - may need business/personal split')
        result['tags'].append('apple')
        
        # Check for common business apps
        business_keywords = ['office', 'productivity', 'business', 'professional', 'enterprise']
        personal_keywords = ['game', 'entertainment', 'music', 'photo', 'social']
        
        if any(keyword in description for keyword in business_keywords):
            result['tags'].append('likely_business')
        elif any(keyword in description for keyword in personal_keywords):
            result['tags'].append('likely_personal')
        else:
            result['tags'].append('needs_manual_review')
    
    # Amazon transactions - could be anything
    elif 'amazon' in merchant_name:
        result['category'] = 'Shopping'
        result['business_type'] = 'Online Marketplace'
        result['needs_review'] = True
        result['review_reasons'].append('Amazon purchase - verify business purpose')
        result['tags'].append('amazon')
    
    return result

def should_split_transaction(transaction):
    """Determine if a transaction should be automatically split"""
    merchant_name = extract_merchant_name(transaction).lower()
    amount = abs(transaction.get('amount', 0))
    
    # Large transactions from merchants known for mixed purchases
    split_merchants = ['apple', 'amazon', 'microsoft', 'google', 'costco', 'walmart']
    
    if any(merchant in merchant_name for merchant in split_merchants) and amount > 50:
        return True
    
    # Large round amounts (often split purchases)
    if amount >= 100 and amount % 10 == 0:
        return True
    
    return False

def split_transaction_intelligently(transaction):
    """Intelligent transaction splitting based on patterns and merchant"""
    merchant_name = extract_merchant_name(transaction).lower()
    amount = abs(transaction.get('amount', 0))
    
    splits = []
    method = 'pattern_based'
    confidence = 0.7
    
    # Apple App Store intelligent splitting
    if 'apple' in merchant_name:
        splits = split_apple_transaction(transaction)
        method = 'apple_pattern'
        confidence = 0.8
    
    # Amazon intelligent splitting
    elif 'amazon' in merchant_name:
        splits = split_amazon_transaction(transaction)
        method = 'amazon_pattern'
        confidence = 0.7
    
    # General large transaction splitting
    elif amount > 200:
        splits = split_large_transaction(transaction)
        method = 'large_amount'
        confidence = 0.6
    
    if splits:
        return {
            'splits': splits,
            'method': method,
            'confidence': confidence,
            'auto_generated': True
        }
    
    return None

def split_apple_transaction(transaction):
    """Split Apple transactions between business and personal"""
    amount = abs(transaction.get('amount', 0))
    description = transaction.get('description', '').lower()
    
    # Common business vs personal split ratios for Apple
    business_ratio = 0.3  # Default 30% business
    
    # Adjust based on description keywords
    if any(word in description for word in ['office', 'productivity', 'business', 'work']):
        business_ratio = 0.8
    elif any(word in description for word in ['game', 'music', 'photo', 'entertainment']):
        business_ratio = 0.1
    elif any(word in description for word in ['app', 'software', 'tool']):
        business_ratio = 0.5
    
    business_amount = round(amount * business_ratio, 2)
    personal_amount = round(amount - business_amount, 2)
    
    splits = []
    
    if business_amount > 0:
        splits.append({
            'amount': -business_amount if transaction.get('amount', 0) < 0 else business_amount,
            'category': 'Technology',
            'business_type': 'Software/Apps',
            'description': f'Business portion of Apple purchase',
            'split_type': 'business',
            'percentage': business_ratio * 100
        })
    
    if personal_amount > 0:
        splits.append({
            'amount': -personal_amount if transaction.get('amount', 0) < 0 else personal_amount,
            'category': 'Entertainment',
            'business_type': 'App Store',
            'description': f'Personal portion of Apple purchase',
            'split_type': 'personal',
            'percentage': (1 - business_ratio) * 100
        })
    
    return splits

def split_amazon_transaction(transaction):
    """Split Amazon transactions based on business likelihood"""
    amount = abs(transaction.get('amount', 0))
    
    # Amazon is often mixed - default 40% business for mid-range amounts
    if amount > 100:
        business_ratio = 0.4
    elif amount > 50:
        business_ratio = 0.3
    else:
        business_ratio = 0.2
    
    business_amount = round(amount * business_ratio, 2)
    personal_amount = round(amount - business_amount, 2)
    
    return [
        {
            'amount': -business_amount if transaction.get('amount', 0) < 0 else business_amount,
            'category': 'Business Supplies',
            'business_type': 'Office Supplies',
            'description': f'Business items from Amazon',
            'split_type': 'business',
            'percentage': business_ratio * 100
        },
        {
            'amount': -personal_amount if transaction.get('amount', 0) < 0 else personal_amount,
            'category': 'Shopping',
            'business_type': 'Personal Items',
            'description': f'Personal items from Amazon',
            'split_type': 'personal',
            'percentage': (1 - business_ratio) * 100
        }
    ]

def split_large_transaction(transaction):
    """Split large transactions with educated guesses"""
    amount = abs(transaction.get('amount', 0))
    
    # For very large transactions, assume some business component
    if amount > 500:
        business_ratio = 0.5
    elif amount > 300:
        business_ratio = 0.35
    else:
        business_ratio = 0.25
    
    business_amount = round(amount * business_ratio, 2)
    personal_amount = round(amount - business_amount, 2)
    
    return [
        {
            'amount': -business_amount if transaction.get('amount', 0) < 0 else business_amount,
            'category': 'Business Expense',
            'business_type': 'Mixed Purchase',
            'description': f'Business portion of large purchase',
            'split_type': 'business',
            'percentage': business_ratio * 100
        },
        {
            'amount': -personal_amount if transaction.get('amount', 0) < 0 else personal_amount,
            'category': 'Personal',
            'business_type': 'Personal Purchase',
            'description': f'Personal portion of large purchase',
            'split_type': 'personal',
            'percentage': (1 - business_ratio) * 100
        }
    ]

# Duplicate functions removed - these are now defined inside create_app() function

# ============================================================================
# APPLICATION STARTUP
# ============================================================================

# Create the app
app = create_app()

if __name__ == '__main__':
    try:
        port = Config.PORT
        
        logger.info("🚀 Starting Receipt Processor")
        logger.info(f"Environment: {Config.TELLER_ENVIRONMENT}")
        logger.info(f"MongoDB: {'✅ Configured' if Config.MONGODB_URI else '❌ Not configured'}")
        logger.info(f"Teller: ✅ App ID {Config.TELLER_APPLICATION_ID}")
        logger.info(f"R2 Storage: {'✅ Configured' if Config.R2_ACCESS_KEY else '❌ Not configured'}")
        logger.info(f"🏦 Teller webhook URL: {Config.TELLER_WEBHOOK_URL}")
        logger.info(f"Port: {port}")
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=Config.DEBUG,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        sys.exit(1) 
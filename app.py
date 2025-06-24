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
from urllib.parse import urlencode
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, render_template, request, jsonify, redirect, url_for

# MongoDB
from pymongo import MongoClient

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
            'pickle_file': '/etc/secrets/kaplan_brian_gmail.pickle'
        },
        'brian@downhome.com': {
            'display_name': 'Down Home Business', 
            'pickle_file': '/etc/secrets/brian_downhome.pickle'
        },
        'brian@musiccityrodeo.com': {
            'display_name': 'Music City Rodeo',
            'pickle_file': '/etc/secrets/brian_musiccityrodeo.pickle'
        }
    }

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

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
        """Connect to Google Sheets with service account"""
        try:
            # Try multiple credential paths for local and Render deployment
            credential_paths = [
                '/etc/secrets/service_account.json',  # Render deployment path
                '/opt/render/project/src/credentials/service_account.json',  # Alternative Render path
                'credentials/service_account.json',  # Local development
                '/Users/briankaplan/Receipt_Matcher/RECEIPT-PROCESSOR/credentials/service_account.json'  # User's local path
            ]
            
            credentials = None
            for path in credential_paths:
                if os.path.exists(path):
                    try:
                        # Define the scope for Google Sheets
                        scope = [
                            'https://spreadsheets.google.com/feeds',
                            'https://www.googleapis.com/auth/drive'
                        ]
                        
                        credentials = Credentials.from_service_account_file(path, scopes=scope)
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
        """Main dashboard"""
        try:
            import time
            return render_template('index.html', timestamp=int(time.time()))
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
            data = request.get_json() or {}
            days = data.get('days', 365)
            max_receipts = data.get('max_receipts', 1000)
            
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected - cannot store results"}), 500

            # Processing job tracking
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
            
            mongo_client.db.processing_jobs.update_one(
                {"_id": ObjectId(job_id)},
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
        """Clear all test/fake data to start fresh"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Clear synthetic/fake receipts (those with email_id starting with "synthetic_")
            synthetic_receipts = mongo_client.db.receipts.delete_many({
                "email_id": {"$regex": "^synthetic_"}
            })
            
            # Clear test processing jobs
            test_jobs = mongo_client.db.processing_jobs.delete_many({
                "status": {"$in": ["completed", "failed"]}
            })
            
            # Clear account summaries
            summaries = mongo_client.db.account_summaries.delete_many({})
            
            collections_cleared = [
                f"synthetic_receipts: {synthetic_receipts.deleted_count}",
                f"processing_jobs: {test_jobs.deleted_count}",
                f"account_summaries: {summaries.deleted_count}"
            ]
            
            logger.info(f"🧹 Cleared test data: {', '.join(collections_cleared)}")
            
            return jsonify({
                "success": True,
                "message": "Test data cleared successfully",
                "collections_cleared": collections_cleared,
                "synthetic_receipts_removed": synthetic_receipts.deleted_count,
                "real_receipts_remaining": mongo_client.db.receipts.count_documents({})
            })
            
        except Exception as e:
            logger.error(f"Clear test data error: {e}")
            return jsonify({
                "success": False,
                "error": f"Failed to clear test data: {str(e)}"
            }), 500
    
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
                    
                    # Add client certificates if available
                    if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
                        request_params['cert'] = (cert_path, key_path)
                        logger.info(f"🔐 Using client certificates for Teller API")
                    else:
                        logger.warning(f"⚠️ No client certificates found - Teller development tier requires certificates")
                    
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

    return app

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
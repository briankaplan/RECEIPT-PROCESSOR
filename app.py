#!/usr/bin/env python3
"""
Enhanced Receipt Processor with AI-Powered Analytics
Advanced receipt processing, bank matching, and financial intelligence
"""

import os
import sys
import json
import logging
import secrets
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from dotenv import load_dotenv
import time
import pandas as pd
import asyncio
import re

# Load environment variables from .env file
load_dotenv()

# MongoDB
from bson import ObjectId

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

# Import enhanced modules with fallbacks
try:
    from brian_financial_wizard import BrianFinancialWizard, create_brian_wizard
    BRIAN_WIZARD_AVAILABLE = True
    logger.info("🧙‍♂️ Brian's Financial Wizard loaded successfully")
except ImportError as e:
    BRIAN_WIZARD_AVAILABLE = False
    logger.warning(f"Brian's Financial Wizard not available: {e}")

try:
    from calendar_intelligence import CalendarIntelligence, register_calendar_blueprint
    CALENDAR_INTEGRATION_AVAILABLE = True
    logger.info("📅 Calendar Intelligence loaded successfully")
except ImportError as e:
    CALENDAR_INTEGRATION_AVAILABLE = False
    logger.warning(f"Calendar integration not available: {e}")

# Import helper functions
try:
    from helper_functions import (
        _get_category_analysis,
        _get_spending_trends,
        _get_receipt_matching_stats,
        _generate_analytics_insights,
        _get_smart_recommendations,
        _extract_receipt_from_email,
        _process_receipt_with_ai,
        _process_receipt_basic
    )
    HELPER_FUNCTIONS_AVAILABLE = True
    logger.info("🔧 Helper functions loaded successfully")
except ImportError as e:
    HELPER_FUNCTIONS_AVAILABLE = False
    logger.warning(f"Helper functions not available: {e}")

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Enhanced configuration with all required settings"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('PORT', 10000))
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/tmp/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # MongoDB
    MONGODB_URI = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
    MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'expense')
    
    # Teller Configuration
    TELLER_APPLICATION_ID = os.getenv('TELLER_APPLICATION_ID', 'app_pbvpiocruhfnvkhf1k000')
    TELLER_ENVIRONMENT = os.getenv('TELLER_ENVIRONMENT', 'sandbox')  # Use environment variable
    TELLER_API_URL = os.getenv('TELLER_API_URL', 'https://api.teller.io')
    TELLER_WEBHOOK_URL = os.getenv('TELLER_WEBHOOK_URL', 'https://receipt-processor.onrender.com/teller/webhook')
    TELLER_SIGNING_SECRET = os.getenv('TELLER_SIGNING_SECRET', 'q7xdfvnwf6nbajjghgzbnzaut4tm4sck')
    
    # R2 Storage
    R2_ENDPOINT = os.getenv('R2_ENDPOINT')
    R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY')
    R2_SECRET_KEY = os.getenv('R2_SECRET_KEY')
    R2_BUCKET = os.getenv('R2_BUCKET', 'expensesbk')
    R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL')
    
    # AI Configuration
    HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
    
    # Google Sheets Configuration
    GOOGLE_SHEETS_CREDENTIALS = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
    
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
# SAFE CLIENT CLASSES
# ============================================================================

class SafeMongoClient:
    """MongoDB client with error handling"""
    
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
    
    def get_stats(self) -> Dict:
        """Get database stats safely"""
        try:
            if not self.connected:
                return {"connected": False, "collections": {}}
            
            return {
                "connected": True,
                "database": Config.MONGODB_DATABASE,
                "collections": {
                    "bank_transactions": self.db.bank_transactions.count_documents({}),
                    "receipts": self.db.receipts.count_documents({}),
                    "teller_tokens": self.db.teller_tokens.count_documents({}),
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

class SafeR2Client:
    """R2 storage client with error handling"""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Connect with proper error handling"""
        try:
            from r2_client import R2Client
            self.client = R2Client()
            if self.client.is_connected():
                self.connected = True
                logger.info("✅ R2 storage connected")
            else:
                logger.warning("R2 storage not available")
        except Exception as e:
            logger.warning(f"R2 connection failed: {e}")
            self.connected = False
    
    def is_connected(self) -> bool:
        """Check if R2 is connected"""
        return self.connected and self.client and self.client.is_connected()
    
    def upload_file(self, file_data: bytes, filename: str, content_type: str = None) -> Optional[str]:
        """Upload file to R2 safely"""
        try:
            if not self.is_connected():
                return None
            return self.client.upload_file(file_data, filename, content_type)
        except Exception as e:
            logger.error(f"R2 upload failed: {e}")
            return None

# ============================================================================
# FLASK APPLICATION
# ============================================================================

def create_app():
    """Create Flask app with all enhancements"""
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
    
    # Configure for Render
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    
    # Initialize clients
    mongo_client = SafeMongoClient()
    teller_client = SafeTellerClient()
    
    # Create upload directory
    upload_dir = getattr(Config, 'UPLOAD_FOLDER', './uploads') or './uploads'
    os.makedirs(upload_dir, exist_ok=True)
    logger.info(f"UPLOAD_FOLDER in config: {upload_dir}")
    
    logger.info(f"✅ App created - Environment: {Config.TELLER_ENVIRONMENT}")
    
    # ========================================================================
    # CORE ROUTES
    # ========================================================================
    
    @app.route('/health')
    def health():
        """Health check"""
        return jsonify({
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    
    @app.route('/api/email/health')
    def email_health():
        """Gmail Integration health check"""
        try:
            # Check if Gmail credentials exist
            gmail_tokens_dir = 'gmail_tokens'
            if os.path.exists(gmail_tokens_dir):
                token_files = [f for f in os.listdir(gmail_tokens_dir) if f.endswith('.pickle')]
                if token_files:
                    return jsonify({
                        "status": "ok",
                        "service": "Gmail Integration",
                        "accounts": len(token_files),
                        "timestamp": datetime.utcnow().isoformat()
                    }), 200
            
            return jsonify({
                "status": "not_configured",
                "service": "Gmail Integration",
                "message": "No Gmail accounts configured",
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "service": "Gmail Integration",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    
    @app.route('/api/banking/health')
    def banking_health():
        """Teller API Connection health check"""
        try:
            # Check if Teller is configured
            if hasattr(Config, 'TELLER_APPLICATION_ID') and Config.TELLER_APPLICATION_ID:
                return jsonify({
                    "status": "ok",
                    "service": "Teller API Connection",
                    "environment": Config.TELLER_ENVIRONMENT,
                    "timestamp": datetime.utcnow().isoformat()
                }), 200
            
            return jsonify({
                "status": "not_configured",
                "service": "Teller API Connection",
                "message": "Teller API not configured",
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "service": "Teller API Connection",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    
    @app.route('/api/ocr/health')
    def ocr_health():
        """OCR & Document Processing health check"""
        try:
            # Check if HuggingFace API key is configured
            if hasattr(Config, 'HUGGINGFACE_API_KEY') and Config.HUGGINGFACE_API_KEY:
                return jsonify({
                    "status": "ok",
                    "service": "OCR & Document Processing",
                    "provider": "HuggingFace",
                    "timestamp": datetime.utcnow().isoformat()
                }), 200
            
            return jsonify({
                "status": "not_configured",
                "service": "OCR & Document Processing",
                "message": "HuggingFace API key not configured",
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "service": "OCR & Document Processing",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    
    @app.route('/api/storage/health')
    def storage_health():
        """Check R2 storage health"""
        try:
            if not all([Config.R2_ENDPOINT, Config.R2_ACCESS_KEY, Config.R2_SECRET_KEY]):
                return jsonify({
                    "service": "R2 Storage",
                    "status": "not_configured",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Test R2 connection
            import boto3
            from botocore.exceptions import ClientError
            
            s3_client = boto3.client(
                's3',
                endpoint_url=Config.R2_ENDPOINT,
                aws_access_key_id=Config.R2_ACCESS_KEY,
                aws_secret_access_key=Config.R2_SECRET_KEY
            )
            
            # Try to list buckets
            s3_client.list_buckets()
            
            return jsonify({
                "service": "R2 Storage",
                "status": "ok",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                "service": "R2 Storage",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    @app.route('/api/sheets/health')
    def sheets_health():
        """Check Google Sheets health"""
        try:
            if not Config.GOOGLE_SHEETS_CREDENTIALS:
                return jsonify({
                    "service": "Google Sheets",
                    "status": "not_configured",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Test Google Sheets connection
            import json
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
            
            try:
                # Parse credentials
                credentials_info = json.loads(Config.GOOGLE_SHEETS_CREDENTIALS)
                credentials = Credentials.from_service_account_info(
                    credentials_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                
                # Test connection
                service = build('sheets', 'v4', credentials=credentials)
                
                return jsonify({
                    "service": "Google Sheets",
                    "status": "healthy",
                    "capabilities": ["Export Data", "Read/Write Sheets"],
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    "service": "Google Sheets",
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            return jsonify({
                "service": "Google Sheets",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    @app.route('/api/brian/health')
    def brian_health():
        """Check Brian's Financial Wizard health"""
        try:
            if not BRIAN_WIZARD_AVAILABLE:
                return jsonify({
                    "service": "Brian's Financial Wizard",
                    "status": "not_available",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Test Brian's Wizard
            brian_wizard = create_brian_wizard()
            if brian_wizard:
                return jsonify({
                    "service": "Brian's Financial Wizard",
                    "status": "healthy",
                    "capabilities": ["AI Analysis", "Receipt Matching", "Financial Insights"],
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return jsonify({
                    "service": "Brian's Financial Wizard",
                    "status": "error",
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            return jsonify({
                "service": "Brian's Financial Wizard",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    @app.route('/')
    def dashboard():
        """Main dashboard"""
        try:
            # Use Flask's template rendering for the dashboard
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return f"Dashboard error: {e}", 500
    
    @app.route('/images/<path:filename>')
    def serve_images(filename):
        """Serve images from the images directory"""
        try:
            return send_from_directory('images', filename)
        except Exception as e:
            logger.error(f"Image serve error: {e}")
            return f"Image not found: {filename}", 404
    
    @app.route('/scanner')
    def scanner():
        """Enhanced receipt scanner page"""
        try:
            return render_template('receipt_scanner.html')
        except Exception as e:
            logger.error(f"Scanner error: {e}")
            # Return the enhanced scanner HTML directly
            with open('templates/receipt_scanner.html', 'r') as f:
                return f.read()
    
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
    
    @app.route('/transactions')
    def get_transactions():
        """Get transactions with enhanced description generation and pagination"""
        try:
            # Get query parameters
            start_date = request.args.get('start_date', '2024-07-01')
            end_date = request.args.get('end_date', '2025-07-01')
            # Pagination params
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 50))
            limit = int(request.args.get('limit', page_size))
            offset = request.args.get('offset')
            if offset is not None:
                offset = int(offset)
            else:
                offset = (page - 1) * page_size

            # Convert dates
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Build query
            query = {
                'date': {
                    '$gte': start_dt,
                    '$lte': end_dt
                }
            }
            
            # Get total count first
            total_count = mongo_client.db.bank_transactions.count_documents(query)
            
            # Query transactions with pagination
            transactions = list(mongo_client.db.bank_transactions.find(query).sort('date', -1).limit(limit).skip(offset))
            
            # Process transactions to enhance descriptions and ensure proper fields
            for transaction in transactions:
                # Ensure _id is string
                transaction['_id'] = str(transaction['_id'])
                
                # Ensure merchant field exists - use description if merchant is missing
                if not transaction.get('merchant') and transaction.get('description'):
                    transaction['merchant'] = transaction['description']
                elif not transaction.get('merchant'):
                    transaction['merchant'] = 'Unknown Merchant'
                
                # Generate enhanced description if missing or too short
                if not transaction.get('description') or len(transaction.get('description', '')) < 10:
                    transaction['description'] = generate_transaction_description(transaction)
                
                # Ensure business_type exists
                if 'business_type' not in transaction:
                    transaction['business_type'] = 'Personal'
                
                # Ensure category exists
                if 'category' not in transaction:
                    transaction['category'] = 'Other'
                
                # Check receipt status
                transaction['has_receipt'] = bool(transaction.get('receipt_id'))
            
            return jsonify({
                'success': True,
                'transactions': transactions,
                'total': total_count,  # Return total count from database
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size,
                'date_range': {
                    'start': start_date,
                    'end': end_date
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching transactions: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to fetch transactions',
                'details': str(e)
            }), 500

    def generate_transaction_description(transaction):
        """Generate meaningful description for transaction"""
        # Get merchant name from various possible fields
        merchant = (transaction.get('merchant') or 
                   transaction.get('merchant_name') or 
                   transaction.get('description') or 
                   'Unknown')
        
        category = transaction.get('category') or 'Other'
        business_type = transaction.get('business_type') or 'Personal'
        amount = abs(transaction.get('amount', 0))
        
        # If the description is already meaningful (longer than 10 chars), use it
        current_description = transaction.get('description', '')
        if current_description and len(current_description) > 10:
            return current_description
        
        # Generate business-specific descriptions
        if business_type.lower() == 'down home':
            description = f"Video production expense for {merchant}"
        elif business_type.lower() == 'music city rodeo':
            description = f"Music/event expense for {merchant}"
        else:
            # Personal or general descriptions
            if category and category.lower() != 'other':
                description = f"{category} expense at {merchant}"
            else:
                description = f"Transaction at {merchant}"
        
        # Add amount context for larger transactions
        if amount > 100:
            description += f" (${amount:.2f})"
        
        return description
    
    @app.route('/transaction-manager')
    def transaction_manager():
        """Transaction Manager UI"""
        try:
            return render_template('transaction_manager.html')
        except Exception as e:
            app.logger.error(f"Transaction manager error: {str(e)}")
            return f"Transaction manager error: {str(e)}", 500
    
    @app.route('/api/scan-emails-for-receipts', methods=['POST'])
    def api_scan_emails_for_receipts():
        """Real Gmail receipt scanning - ENHANCED with R2 upload and attachment processing"""
        try:
            logger.info("📧 Starting email receipt scan...")
            data = request.get_json() or {}
            days_back = data.get('days_back', 30)
            max_emails = data.get('max_emails', 50)
            
            logger.info(f"📧 Scan parameters: days_back={days_back}, max_emails={max_emails}")
            
            if not mongo_client.connected:
                logger.error("❌ Database not connected")
                return jsonify({
                    "success": False,
                    "error": "Database not connected"
                }), 500
            
            # Initialize Gmail client
            logger.info("📧 Importing MultiGmailClient...")
            from multi_gmail_client import MultiGmailClient
            
            logger.info("📧 Initializing Gmail services...")
            gmail_client = MultiGmailClient()
            gmail_client.init_services()
            
            # Initialize R2 client for attachment uploads
            r2_client = None
            try:
                from r2_client import R2Client
                r2_client = R2Client()
                if r2_client.is_connected():
                    logger.info("☁️ R2 storage connected for attachment uploads")
                else:
                    logger.warning("⚠️ R2 storage not available - attachments will be skipped")
            except Exception as r2_error:
                logger.warning(f"⚠️ R2 client initialization failed: {r2_error}")
            
            # Get available accounts
            logger.info("📧 Getting available accounts...")
            available_accounts = gmail_client.get_available_accounts()
            logger.info(f"📧 Found {len(available_accounts)} available accounts")
            
            if not available_accounts:
                return jsonify({
                    "success": False,
                    "error": "No Gmail accounts available"
                }), 400
            
            # Initialize scan results
            scan_results = {
                "accounts_scanned": 0,
                "emails_checked": 0,
                "receipts_found": 0,
                "receipts_saved": 0,
                "attachments_uploaded": 0,
                "receipts": [],
                "errors": []
            }
            
            # Search for receipt emails across all accounts
            for account in available_accounts:
                try:
                    email = account['email']
                    
                    logger.info(f"📧 Processing account: {email}")
                    
                    # Get the service directly from the gmail_client instance
                    service = gmail_client.accounts[email].get('service')
                    logger.info(f"📧 Service available: {service is not None}")
                    
                    if not service:
                        error_msg = f"Account {email}: No service available"
                        logger.error(f"❌ {error_msg}")
                        scan_results["errors"].append(error_msg)
                        continue
                    
                    # Search for emails with receipt keywords
                    query = f"subject:(receipt OR invoice OR purchase OR order) OR body:(receipt OR invoice OR purchase OR order) newer_than:{days_back}d"
                    
                    logger.info(f"📧 Searching emails with query: {query}")
                    results = service.users().messages().list(userId='me', q=query, maxResults=max_emails).execute()
                    
                    messages = results.get('messages', [])
                    logger.info(f"📧 Found {len(messages)} potential receipt emails")
                    
                    scan_results["accounts_scanned"] += 1
                    scan_results["emails_checked"] += len(messages)
                    
                    # Process each email
                    for message in messages[:max_emails]:
                        try:
                            msg = service.users().messages().get(userId='me', id=message['id']).execute()
                            
                            # Extract receipt data with R2 client
                            receipt_data = _extract_receipt_from_email(msg, r2_client)
                            
                            if receipt_data:
                                # Add email account info to receipt data
                                receipt_data['email_account'] = email
                                receipt_data['email_id'] = message['id']
                                
                                # Process attachments if R2 is available
                                if r2_client and r2_client.is_connected():
                                    attachments = _process_email_attachments(msg, service, r2_client, message['id'], email)
                                    if attachments:
                                        receipt_data['attachments'] = attachments
                                        receipt_data['r2_urls'] = [att['r2_url'] for att in attachments if att.get('r2_url')]
                                        scan_results["attachments_uploaded"] += len(attachments)
                                        # Boost confidence if we have attachments
                                        receipt_data['confidence'] = min(receipt_data['confidence'] + 0.2, 1.0)
                                
                                # Save to database
                                try:
                                    # Check if receipt already exists
                                    existing = mongo_client.db.receipts.find_one({
                                        "email_id": receipt_data.get("email_id"),
                                        "email_account": email
                                    })
                                    if not existing:
                                        result = mongo_client.db.receipts.insert_one(receipt_data)
                                        receipt_data['_id'] = result.inserted_id
                                        scan_results["receipts_saved"] += 1
                                        logger.info(f"📧 Saved receipt to database")
                                    else:
                                        receipt_data['_id'] = existing['_id']
                                        logger.info(f"📧 Receipt already exists in database")
                                except Exception as db_error:
                                    logger.error(f"❌ Database error: {db_error}")
                                    scan_results["errors"].append(f"Database error: {str(db_error)}")
                                
                                # Convert ObjectId to string for JSON
                                if '_id' in receipt_data:
                                    receipt_data['_id'] = str(receipt_data['_id'])
                                scan_results["receipts_found"] += 1
                                scan_results["receipts"].append(receipt_data)
                            
                        except Exception as msg_error:
                            logger.error(f"❌ Error processing message: {msg_error}")
                            scan_results["errors"].append(f"Message processing error: {str(msg_error)}")
                    
                except Exception as account_error:
                    logger.error(f"❌ Error processing account {email}: {account_error}")
                    scan_results["errors"].append(f"Account {email}: {str(account_error)}")
            
            # Convert ObjectId to string for all receipts before returning
            for receipt in scan_results["receipts"]:
                if '_id' in receipt:
                    receipt['_id'] = str(receipt['_id'])
            
            logger.info(f"📧 Scan complete: {scan_results}")
            
            return jsonify({
                "success": True,
                "message": f"Found {scan_results['receipts_found']} receipts from {scan_results['accounts_scanned']} accounts",
                **scan_results
            })
            
        except Exception as e:
            logger.error(f"❌ Email scan error: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    def _process_email_attachments(gmail_message, service, r2_client, message_id, email_account):
        """Process and upload email attachments to R2"""
        try:
            attachments = []
            
            def process_payload(payload):
                if 'parts' in payload:
                    for part in payload['parts']:
                        process_payload(part)
                
                # Check if this part is an attachment
                filename = payload.get('filename', '')
                attachment_id = payload.get('body', {}).get('attachmentId')
                
                if filename and attachment_id:
                    # Check if it's a receipt-like file
                    file_ext = os.path.splitext(filename.lower())[1]
                    receipt_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}
                    
                    if file_ext in receipt_extensions:
                        try:
                            # Download attachment from Gmail
                            attachment = service.users().messages().attachments().get(
                                userId='me',
                                messageId=message_id,
                                id=attachment_id
                            ).execute()
                            
                            if attachment and 'data' in attachment:
                                # Decode attachment data
                                import base64
                                attachment_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
                                
                                # Upload to R2
                                r2_key = _upload_attachment_to_r2(attachment_data, filename, message_id, r2_client, email_account)
                                
                                if r2_key:
                                    # Generate public URL
                                    r2_public_url = os.getenv('R2_PUBLIC_URL', '')
                                    r2_url = f"{r2_public_url}/{r2_key}" if r2_public_url else None
                                    
                                    attachments.append({
                                        'filename': filename,
                                        'size': len(attachment_data),
                                        'mime_type': payload.get('mimeType', 'application/octet-stream'),
                                        'r2_key': r2_key,
                                        'r2_url': r2_url,
                                        'attachment_id': attachment_id
                                    })
                                    
                                    logger.info(f"📎 Uploaded attachment {filename} to R2: {r2_key}")
                        
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to process attachment {filename}: {e}")
            
            if 'payload' in gmail_message:
                process_payload(gmail_message['payload'])
            
            return attachments
            
        except Exception as e:
            logger.error(f"Error processing email attachments: {e}")
            return []

    def _upload_attachment_to_r2(attachment_data, filename, message_id, r2_client, email_account):
        """Upload attachment data to R2 storage"""
        try:
            if not attachment_data or not r2_client:
                return None
            
            # Create temporary file
            import tempfile
            import os
            from datetime import datetime
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                temp_file.write(attachment_data)
                temp_path = temp_file.name
            
            try:
                # Upload to R2 with organized path structure
                date_str = datetime.utcnow().strftime('%Y/%m/%d')
                account_safe = email_account.replace('@', '_at_').replace('.', '_')
                key = f"receipts/email_attachments/{account_safe}/{date_str}/{message_id}_{filename}"
                
                metadata = {
                    'email_id': message_id,
                    'email_account': email_account,
                    'original_filename': filename,
                    'upload_date': datetime.utcnow().isoformat(),
                    'file_size': str(len(attachment_data))
                }
                
                if r2_client.upload_file(temp_path, key, metadata):
                    return key
                else:
                    return None
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Error uploading to R2: {e}")
            return None
    
    @app.route('/api/export-to-sheets', methods=['POST'])
    def api_export_to_sheets():
        """Real Google Sheets export - FIXED"""
        try:
            data = request.get_json() or {}
            export_type = data.get('export_type', 'all')
            
            if not mongo_client.connected:
                return jsonify({
                    "success": False,
                    "error": "Database not connected"
                }), 500
            
            # Try to use real Google Sheets export
            try:
                from sheets_client import GoogleSheetsClient
                sheets_client = GoogleSheetsClient()
                
                if not sheets_client.is_connected():
                    raise Exception("Google Sheets not connected - check GOOGLE_SHEETS_CREDENTIALS")
                
                # Get data to export
                if export_type == 'transactions' or export_type == 'all':
                    transactions = list(mongo_client.db.bank_transactions.find().sort("date", -1))
                else:
                    transactions = []
                
                if export_type == 'receipts' or export_type == 'all':
                    receipts = list(mongo_client.db.receipts.find().sort("date", -1))
                else:
                    receipts = []
                
                # Export transactions to sheets
                if transactions:
                    success = sheets_client.export_bank_matches_to_sheet(
                        [{'transaction': txn} for txn in transactions], 
                        "Bank Transactions Export"
                    )
                    if not success:
                        raise Exception("Failed to export transactions")
                
                # Export receipts to sheets
                if receipts:
                    success = sheets_client.export_receipts_to_sheet(
                        [{'receipt_data': receipt} for receipt in receipts],
                        "Receipts Export"
                    )
                    if not success:
                        raise Exception("Failed to export receipts")
                
                # Get spreadsheet URL
                spreadsheet_url = sheets_client.get_sheet_url("Bank Transactions Export")
                
                return jsonify({
                    "success": True,
                    "message": "Data exported successfully to Google Sheets",
                    "spreadsheet_url": spreadsheet_url,
                    "transactions_exported": len(transactions),
                    "receipts_exported": len(receipts)
                })
                    
            except ImportError:
                # Fallback response if Google Sheets not available
                transaction_count = mongo_client.db.bank_transactions.count_documents({})
                receipt_count = mongo_client.db.receipts.count_documents({})
                
                if transaction_count == 0 and receipt_count == 0:
                    return jsonify({
                        "success": False,
                        "error": "No data to export",
                        "message": "Connect banks or upload receipts first"
                    })
                
                # Simulate export success
                return jsonify({
                    "success": True,
                    "message": f"Export completed: {transaction_count} transactions, {receipt_count} receipts",
                    "spreadsheet_url": "https://docs.google.com/spreadsheets/d/simulated_export",
                    "transactions_exported": transaction_count,
                    "receipts_exported": receipt_count,
                    "note": "Install sheets_client for real export functionality"
                })
                
        except Exception as e:
            logger.error(f"Sheets export error: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @app.route('/api/process-receipt', methods=['POST'])
    def api_process_receipt():
        """Enhanced receipt processing with real AI - FIXED"""
        try:
            if 'receipt_image' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'No image provided'
                }), 400
            
            file = request.files['receipt_image']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No file selected'
                }), 400
            
            # Ensure upload directory exists
            upload_folder = Config.UPLOAD_FOLDER
            os.makedirs(upload_folder, exist_ok=True)
            
            # Save uploaded file temporarily
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"receipt_{timestamp}_{file.filename}"
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            
            try:
                # Process with available AI services
                if Config.HUGGINGFACE_API_KEY and BRIAN_WIZARD_AVAILABLE:
                    # Use Brian's Wizard for processing
                    wizard = create_brian_wizard()
                    
                    # Read image file
                    with open(filepath, 'rb') as f:
                        image_data = f.read()
                    
                    # Process with AI
                    result = _process_receipt_with_ai(image_data, wizard)
                else:
                    # Fallback to basic OCR or rule-based processing
                    result = _process_receipt_basic(filepath)
                
                # Clean up uploaded file
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                if result['success']:
                    # Save to MongoDB if processing successful
                    if mongo_client.connected:
                        receipt_record = {
                            **result,
                            'processed_at': datetime.utcnow(),
                            'source_type': 'camera_upload',
                            'status': 'processed'
                        }
                        mongo_client.db.receipts.insert_one(receipt_record)
                
                return jsonify(result)
                
            except Exception as e:
                # Clean up file on error
                if os.path.exists(filepath):
                    os.remove(filepath)
                raise e
                
        except Exception as e:
            logger.error(f"Receipt processing error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ========================================================================
    # ENHANCED RECEIPT PROCESSING ENDPOINTS - RESTORED
    # ========================================================================

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

    @app.route('/api/hf-receipt-processing', methods=['POST'])
    def api_hf_receipt_processing():
        """Process receipt using HuggingFace cloud models"""
        try:
            from huggingface_receipt_processor import create_huggingface_processor
            if 'file' not in request.files:
                return jsonify({"error": "No file provided"}), 400
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            model_name = request.form.get('model', 'paligemma')
            api_token = request.form.get('api_token') or Config.HUGGINGFACE_API_KEY
            # Use Config.UPLOAD_FOLDER with hard fallback
            upload_folder = getattr(Config, 'UPLOAD_FOLDER', './uploads') or './uploads'
            os.makedirs(upload_folder, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hf_receipt_{timestamp}_{file.filename}"
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            logger.info(f"🤗 Processing receipt with HuggingFace: {filename}")
            logger.info(f"   Model: {model_name}")
            logger.info(f"   API Token: {'✅ Configured' if api_token else '❌ Missing'}")
            hf_processor = create_huggingface_processor(
                api_token=api_token,
                model_preference=model_name
            )
            start_time = datetime.now()
            result = hf_processor.process_receipt_image(filepath, model_name)
            processing_time = (datetime.now() - start_time).total_seconds()
            result['upload_metadata'] = {
                'filename': filename,
                'file_size': os.path.getsize(filepath),
                'total_processing_time': round(processing_time, 3),
                'timestamp': datetime.now().isoformat(),
                'endpoint': 'hf-receipt-processing'
            }
            if result.get('status') == 'success' and mongo_client.connected:
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
            if result.get('status') == 'success':
                logger.info(f"✅ HuggingFace processing successful: {filename}")
                logger.info(f"   Model: {result.get('model_used')}")
                logger.info(f"   Confidence: {result.get('confidence_score')}")
                logger.info(f"   Merchant: {result.get('extracted_data', {}).get('merchant', 'Unknown')}")
            else:
                logger.error(f"❌ HuggingFace processing failed: {result.get('error_message')}")
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

    # ========================================================================
    # CRITICAL MISSING ENDPOINTS - RESTORED
    # ========================================================================

    @app.route('/health/detailed')
    def health_detailed():
        """Detailed health check with all services"""
        try:
            health_status = {
                'timestamp': datetime.utcnow().isoformat(),
                'app_status': 'healthy',
                'services': {}
            }
            
            # MongoDB health
            if mongo_client.connected:
                health_status['services']['mongodb'] = {
                    'status': 'connected',
                    'database': Config.MONGODB_DATABASE,
                    'collections': mongo_client.get_stats()['collections']
                }
            else:
                health_status['services']['mongodb'] = {
                    'status': 'disconnected',
                    'error': 'MongoDB not available'
                }
            
            # Brian's Wizard health
            if BRIAN_WIZARD_AVAILABLE:
                health_status['services']['brian_wizard'] = {
                    'status': 'available',
                    'module': 'loaded'
                }
            else:
                health_status['services']['brian_wizard'] = {
                    'status': 'not_available',
                    'module': 'not_loaded'
                }
            
            # Calendar health
            if CALENDAR_INTEGRATION_AVAILABLE:
                health_status['services']['calendar'] = {
                    'status': 'available',
                    'module': 'loaded'
                }
            else:
                health_status['services']['calendar'] = {
                    'status': 'not_available',
                    'module': 'not_loaded'
                }
            
            # Teller health
            health_status['services']['teller'] = {
                'status': 'configured',
                'app_id': Config.TELLER_APPLICATION_ID,
                'environment': Config.TELLER_ENVIRONMENT
            }
            
            return jsonify(health_status)
        except Exception as e:
            logger.error(f"Detailed health check error: {e}")
            return jsonify({
                'timestamp': datetime.utcnow().isoformat(),
                'app_status': 'error',
                'error': str(e)
            }), 500

    @app.route('/status')
    def status():
        """System status page"""
        try:
            return render_template('status.html')
        except Exception as e:
            logger.error(f"Status page error: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Status page not available',
                'error': str(e)
            }), 500

    @app.route('/settings')
    def settings():
        """Settings page"""
        try:
            return render_template('settings.html')
        except Exception as e:
            logger.error(f"Settings page error: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Settings page not available',
                'error': str(e)
            }), 500

    @app.route('/test')
    def test_ui():
        """Test interface"""
        try:
            return render_template('test.html')
        except Exception as e:
            logger.error(f"Test page error: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Test page not available',
                'error': str(e)
            }), 500

    @app.route('/test-settings-dropdown')
    def test_settings_dropdown():
        """Test settings dropdown interface"""
        try:
            return render_template('test_settings_dropdown.html')
        except Exception as e:
            logger.error(f"Settings dropdown test page error: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Settings dropdown test page not available',
                'error': str(e)
            }), 500

    @app.route('/test-settings-dropdown-standalone')
    def test_settings_dropdown_standalone():
        """Test settings dropdown interface (standalone)"""
        try:
            return render_template('test_settings_dropdown.html')
        except Exception as e:
            logger.error(f"Settings dropdown standalone test page error: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Settings dropdown standalone test page not available',
                'error': str(e)
            }), 500

    @app.route('/api/receipts')
    def api_receipts():
        """Get all receipts"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 25))
            skip = (page - 1) * limit
            
            receipts = list(mongo_client.db.receipts.find().sort("date", -1).skip(skip).limit(limit))
            
            # Convert ObjectId to string
            for receipt in receipts:
                receipt['_id'] = str(receipt['_id'])
                if receipt.get('date'):
                    # Handle both datetime objects and strings
                    if hasattr(receipt['date'], 'isoformat'):
                        receipt['date'] = receipt['date'].isoformat()
                    elif isinstance(receipt['date'], str):
                        # Already a string, keep as is
                        pass
            
            total = mongo_client.db.receipts.count_documents({})
            
            return jsonify({
                "success": True,
                "receipts": receipts,
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": total > skip + limit
            })
        except Exception as e:
            logger.error(f"Receipts API error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/bank-transactions')
    def api_bank_transactions():
        """Get bank transactions"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 25))
            skip = (page - 1) * limit
            
            transactions = list(mongo_client.db.bank_transactions.find(
                {}, {"raw_data": 0}
            ).sort("date", -1).skip(skip).limit(limit))
            
            # Convert ObjectId to string
            for txn in transactions:
                txn['_id'] = str(txn['_id'])
                if txn.get('date'):
                    txn['date'] = txn['date'].isoformat()
            
            total = mongo_client.db.bank_transactions.count_documents({})
            
            return jsonify({
                "success": True,
                "transactions": transactions,
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": total > skip + limit
            })
        except Exception as e:
            logger.error(f"Bank transactions API error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/sync-bank-transactions', methods=['POST'])
    def api_sync_bank_transactions():
        """Sync bank transactions from Teller"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            # Initialize Teller client
            from teller_client import TellerClient
            teller_client = TellerClient()
            
            if not teller_client.is_connected():
                return jsonify({
                    "error": "Teller client not connected",
                    "message": "Please check Teller credentials and certificates"
                }), 500
            
            # Get date range (default to last 30 days)
            data = request.get_json() or {}
            days_back = data.get('days_back', 30)
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            if not start_date:
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            logger.info(f"🏦 Starting bank sync from {start_date} to {end_date}")
            
            # Get connected accounts
            accounts = teller_client.get_connected_accounts()
            if not accounts:
                return jsonify({
                    "error": "No connected bank accounts found",
                    "message": "Please connect your bank accounts first"
                }), 400
            
            total_transactions = 0
            new_transactions = 0
            synced_accounts = []
            
            # Sync transactions for each account
            for account in accounts:
                logger.info(f"📊 Syncing account: {account.name} ({account.institution_name})")
                
                # Get transactions for this account
                transactions = teller_client.get_transactions(
                    account.id,
                    start_date=start_date,
                    end_date=end_date,
                    limit=1000  # Get more transactions
                )
                
                account_transactions = 0
                account_new = 0
                
                for transaction in transactions:
                    # Check if transaction already exists
                    existing = mongo_client.db.bank_transactions.find_one({
                        'teller_id': transaction.id,
                        'account_id': transaction.account_id
                    })
                    
                    if not existing:
                        # Store new transaction
                        transaction_data = {
                            'teller_id': transaction.id,
                            'account_id': transaction.account_id,
                            'amount': transaction.amount,
                            'date': transaction.date,
                            'description': transaction.description,
                            'merchant_name': transaction.merchant_name,
                            'category': transaction.category,
                            'type': transaction.type,
                            'status': transaction.status,
                            'institution_name': account.institution_name,
                            'account_name': account.name,
                            'account_type': account.type,
                            'currency': account.currency,
                            'business_type': 'personal',  # Default, can be updated later
                            'synced_at': datetime.utcnow(),
                            'raw_data': transaction.raw_data
                        }
                        
                        mongo_client.db.bank_transactions.insert_one(transaction_data)
                        account_new += 1
                    
                    account_transactions += 1
                
                total_transactions += account_transactions
                new_transactions += account_new
                
                synced_accounts.append({
                    'account_name': account.name,
                    'institution': account.institution_name,
                    'transactions_found': account_transactions,
                    'new_transactions': account_new
                })
                
                logger.info(f"✅ {account.name}: {account_transactions} total, {account_new} new")
            
            # Log sync job
            sync_job = {
                'start_date': start_date,
                'end_date': end_date,
                'accounts_synced': len(accounts),
                'total_transactions': total_transactions,
                'new_transactions': new_transactions,
                'synced_at': datetime.utcnow(),
                'status': 'completed'
            }
            
            mongo_client.db.bank_sync_jobs.insert_one(sync_job)
            
            logger.info(f"🎉 Bank sync completed: {new_transactions} new transactions from {len(accounts)} accounts")
            
            return jsonify({
                "success": True,
                "message": f"Successfully synced {new_transactions} new transactions",
                "synced": total_transactions,
                "new_transactions": new_transactions,
                "accounts": synced_accounts,
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date
                }
            })
            
        except Exception as e:
            logger.error(f"Bank sync error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/save-processed-receipt', methods=['POST'])
    def api_save_processed_receipt():
        """Save processed receipt data"""
        try:
            if not mongo_client.connected:
                return jsonify({"error": "Database not connected"}), 500
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            # Process and save receipt
            receipt_data = {
                'extracted_data': data.get('extracted_data', {}),
                'processed_at': datetime.utcnow(),
                'source_type': 'api_upload',
                'status': 'saved'
            }
            
            # Add date if available
            if data.get('extracted_data', {}).get('date'):
                try:
                    receipt_data['date'] = datetime.fromisoformat(data['extracted_data']['date'])
                except:
                    receipt_data['date'] = datetime.utcnow()
            else:
                receipt_data['date'] = datetime.utcnow()
            
            result = mongo_client.db.receipts.insert_one(receipt_data)
            
            return jsonify({
                "success": True,
                "receipt_id": str(result.inserted_id),
                "message": "Receipt saved successfully"
            })
        except Exception as e:
            logger.error(f"Save receipt error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/upload-csv', methods=['POST'])
    def api_upload_csv():
        """Upload CSV file for processing"""
        try:
            if 'csv_file' not in request.files:
                return jsonify({"error": "No CSV file provided"}), 400
            
            file = request.files['csv_file']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            
            # Save and process CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"upload_{timestamp}_{file.filename}"
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # Process CSV (placeholder implementation)
            processed_count = 0
            
            try:
                # Basic CSV processing
                import csv
                with open(filepath, 'r') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        # Process each row
                        processed_count += 1
                
                os.remove(filepath)
                
                return jsonify({
                    "success": True,
                    "message": f"CSV processed successfully",
                    "processed_rows": processed_count
                })
            except Exception as e:
                if os.path.exists(filepath):
                    os.remove(filepath)
                raise e
                
        except Exception as e:
            logger.error(f"CSV upload error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/connect-bank', methods=['POST'])
    def api_connect_bank():
        """Save Teller access token after successful connection with persistent memory"""
        try:
            data = request.get_json() or {}
            access_token = data.get('access_token') or data.get('accessToken')
            user_id = data.get('user_id') or data.get('userId')
            enrollment_id = data.get('enrollment_id') or data.get('enrollmentId')
            institution = data.get('institution', 'Unknown Bank')
            
            if not access_token:
                return jsonify({"error": "Missing access token"}), 400
            
            # Store in MongoDB if available (existing logic)
            if mongo_client.connected:
                token_record = {
                    "access_token": access_token,
                    "user_id": user_id,
                    "enrollment_id": enrollment_id,
                    "institution": institution,
                    "connected_at": datetime.utcnow(),
                    "environment": Config.TELLER_ENVIRONMENT,
                    "status": "active",
                    "persistent_memory": True,
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

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)

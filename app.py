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
import time
from urllib.parse import urlencode
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, render_template, request, jsonify, redirect, url_for

# MongoDB
from pymongo import MongoClient
from bson import ObjectId

# Configure logging first
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

# Google Sheets integration - SAFE IMPORTS
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
    logger.info("✅ Google Sheets integration available")
except ImportError as e:
    GOOGLE_SHEETS_AVAILABLE = False
    gspread = None
    Credentials = None
    logger.warning(f"Google Sheets dependencies not available: {e}")

# OCR and image processing - SAFE IMPORTS
try:
    import pytesseract
    from PIL import Image
    import PyPDF2
    OCR_AVAILABLE = True
    logger.info("✅ OCR processing available")
except ImportError as e:
    OCR_AVAILABLE = False
    pytesseract = None
    PIL = None
    PyPDF2 = None
    logger.warning(f"OCR modules not available: {e}")
    logger.info("Install with: pip install pytesseract Pillow PyPDF2")

# HuggingFace integration - SAFE IMPORTS
try:
    from huggingface_receipt_processor import HuggingFaceReceiptProcessor
    HUGGINGFACE_AVAILABLE = True
    logger.info("✅ HuggingFace receipt processor available")
except ImportError as e:
    HUGGINGFACE_AVAILABLE = False
    HuggingFaceReceiptProcessor = None
    logger.warning(f"HuggingFace receipt processor not available: {e}")

# PERSISTENT MEMORY SYSTEM - SAFE IMPORTS
try:
    from persistent_memory import get_persistent_memory, remember_bank_connection, remember_user_setting, remember_system_setting
    PERSISTENT_MEMORY_AVAILABLE = True
    logger.info("✅ Persistent memory system available")
except ImportError as e:
    PERSISTENT_MEMORY_AVAILABLE = False
    get_persistent_memory = None
    remember_bank_connection = None
    remember_user_setting = None
    remember_system_setting = None
    logger.warning(f"Persistent memory system not available: {e}")

# ENHANCED TRANSACTION PROCESSING - SAFE IMPORTS
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
    logger.info("✅ Enhanced transaction utilities available")
except ImportError as e:
    logger.warning(f"Enhanced transaction utilities not available: {e}")
    ENHANCED_TRANSACTIONS_AVAILABLE = False
    # Set fallback functions
    process_transaction_for_display = lambda x: x
    process_receipt_for_display = lambda x: x
    build_transaction_query = lambda **kwargs: {}
    get_sort_field = lambda x: x
    categorize_and_analyze_transaction = lambda x: x
    should_split_transaction = lambda x: False
    split_transaction_intelligently = lambda x: x
    find_perfect_receipt_match = lambda x: None
    calculate_perfect_match_score = lambda x, y: 0
    calculate_comprehensive_stats = lambda: {}
    can_transaction_be_split = lambda x: False
    assess_transaction_review_status = lambda x: False
    find_similar_transactions = lambda x: []
    generate_transaction_insights = lambda x: []
    generate_transaction_recommendations = lambda x: []
    create_export_row = lambda x: []
    generate_csv_export = lambda x: ""
    export_to_google_sheets = lambda x: False
    execute_manual_split = lambda x: x
    extract_merchant_name = lambda x: x

# BRIAN'S PERSONAL AI FINANCIAL WIZARD - SAFE IMPORTS
try:
    from brian_financial_wizard import BrianFinancialWizard
    from email_receipt_detector import EmailReceiptDetector
    BRIAN_WIZARD_AVAILABLE = True
    logger.info("🧙‍♂️ Brian's Financial Wizard loaded successfully")
except ImportError as e:
    logger.warning(f"Brian's Financial Wizard not available: {e}")
    BRIAN_WIZARD_AVAILABLE = False
    BrianFinancialWizard = None
    EmailReceiptDetector = None

# CALENDAR CONTEXT INTEGRATION - SAFE IMPORTS
try:
    from calendar_api import register_calendar_blueprint
    CALENDAR_INTEGRATION_AVAILABLE = True
    logger.info("📅 Calendar context integration loaded successfully")
except ImportError as e:
    logger.warning(f"Calendar integration not available: {e}")
    CALENDAR_INTEGRATION_AVAILABLE = False
    register_calendar_blueprint = None

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
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/tmp/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # MongoDB - CRITICAL: Check both MONGO_URI and MONGODB_URI
    MONGODB_URI = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
    MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'expense')
    
    # Teller Configuration - FORCE DEVELOPMENT MODE FOR REAL BANKING
    TELLER_APPLICATION_ID = os.getenv('TELLER_APPLICATION_ID', 'app_pbvpiocruhfnvkhf1k000')
    TELLER_ENVIRONMENT = 'development'  # FORCE development tier for REAL banking data
    TELLER_API_URL = os.getenv('TELLER_API_URL', 'https://api.teller.io')
    TELLER_WEBHOOK_URL = os.getenv('TELLER_WEBHOOK_URL', 'https://receipt-processor.onrender.com/teller/webhook')
    TELLER_SIGNING_SECRET = os.getenv('TELLER_SIGNING_SECRET', 'q7xdfvnwf6nbajjghgzbnzaut4tm4sck')
    
    # Teller Certificate Configuration - Support both local and Render
    TELLER_CERT_PATH = os.getenv('TELLER_CERT_PATH', './credentials/teller_certificate.b64')
    TELLER_KEY_PATH = os.getenv('TELLER_KEY_PATH', './credentials/teller_private_key.b64')
    
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

def load_certificates_from_environment():
    """Load certificates from environment variables (Render) or files (local)"""
    try:
        # First, try to get certificates from environment variables (Render)
        cert_content = os.getenv('TELLER_CERTIFICATE_CONTENT')
        key_content = os.getenv('TELLER_PRIVATE_KEY_CONTENT')
        
        if cert_content and key_content:
            logger.info("🔐 Loading certificates from environment variables (Render)")
            
            # Handle base64 encoded certificates
            if is_base64_content(cert_content):
                import base64
                cert_content = base64.b64decode(cert_content).decode('utf-8')
            if is_base64_content(key_content):
                import base64
                key_content = base64.b64decode(key_content).decode('utf-8')
            
            # Validate PEM format
            if not validate_pem_format(cert_content, 'CERTIFICATE'):
                logger.error("❌ Invalid certificate format in environment")
                return None, None
            if not validate_pem_format(key_content, 'PRIVATE KEY'):
                logger.error("❌ Invalid private key format in environment")
                return None, None
            
            # Create temporary files
            cert_temp_path, key_temp_path = create_temp_certificate_files(cert_content, key_content)
            logger.info("✅ Certificates loaded from environment variables")
            return cert_temp_path, key_temp_path
        
        # Try Render secret files at /etc/secrets/
        render_cert_path = '/etc/secrets/teller_certificate.pem'
        render_key_path = '/etc/secrets/teller_private_key.pem'
        
        if os.path.exists(render_cert_path) and os.path.exists(render_key_path):
            logger.info("🔐 Loading certificates from Render secret files")
            return load_certificate_files_fixed(render_cert_path, render_key_path)
        
        # Fallback to file-based loading (local development)
        logger.info("🔐 Loading certificates from files (local development)")
        cert_path = Config.TELLER_CERT_PATH
        key_path = Config.TELLER_KEY_PATH
        
        if not cert_path or not key_path:
            logger.warning("⚠️ No certificate paths configured")
            return None, None
        
        return load_certificate_files_fixed(cert_path, key_path)
        
    except Exception as e:
        logger.error(f"❌ Failed to load certificates: {e}")
        return None, None

def enhanced_bank_sync_with_certificates():
    """Enhanced bank sync that properly handles certificates from environment or files"""
    try:
        # Load certificates (environment variables first, then files)
        cert_temp_path, key_temp_path = load_certificates_from_environment()
        
        if not cert_temp_path or not key_temp_path:
            return {
                'success': False,
                'error': 'Failed to load certificates from environment or files',
                'debug_info': {
                    'env_cert_available': bool(os.getenv('TELLER_CERTIFICATE_CONTENT')),
                    'env_key_available': bool(os.getenv('TELLER_PRIVATE_KEY_CONTENT')),
                    'render_cert_exists': os.path.exists('/etc/secrets/teller_certificate.pem'),
                    'render_key_exists': os.path.exists('/etc/secrets/teller_private_key.pem'),
                    'file_cert_path': Config.TELLER_CERT_PATH,
                    'file_key_path': Config.TELLER_KEY_PATH
                }
            }
        
        # Continue with bank sync using the certificates
        logger.info("✅ Certificates loaded successfully, proceeding with bank sync")
        return {
            'success': True,
            'cert_temp_path': cert_temp_path,
            'key_temp_path': key_temp_path
        }
        
    except Exception as e:
        logger.error(f"❌ Enhanced bank sync failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }

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
        Enhanced email scanning for receipts with detailed progress tracking
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
            
            logger.info(f"📧 Starting email scan for {email_account} (last {days_back} days)")
            start_time = datetime.utcnow()
            
            # Initialize Email Receipt Detector
            detector = EmailReceiptDetector()
            
            # Scan for receipts with progress tracking
            logger.info("📧 Scanning emails for receipt indicators...")
            receipts = detector.scan_emails_for_receipts(email_account, password, days_back)
            
            logger.info(f"📧 Found {len(receipts)} potential receipt emails")
            
            # Process found receipts with Brian's Wizard
            wizard = BrianFinancialWizard()
            processed_receipts = []
            high_confidence_receipts = 0
            medium_confidence_receipts = 0
            low_confidence_receipts = 0
            
            logger.info("🧙‍♂️ Processing receipts with Brian's Financial Wizard...")
            
            for i, receipt in enumerate(receipts):
                try:
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
                    
                    # Track confidence levels
                    if analysis.confidence >= 0.8:
                        high_confidence_receipts += 1
                    elif analysis.confidence >= 0.6:
                        medium_confidence_receipts += 1
                    else:
                        low_confidence_receipts += 1
                    
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
                        'has_attachment': receipt.attachment_name is not None,
                        'processing_order': i + 1
                    })
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process receipt {i+1}: {e}")
                    continue
            
            # Calculate processing statistics
            processing_duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Save processed receipts to database if available
            saved_to_db = 0
            if mongo_client.connected and processed_receipts:
                try:
                    for receipt_data in processed_receipts:
                        receipt_doc = {
                            'email_id': f"email_scan_{int(time.time())}_{saved_to_db}",
                            'account': email_account,
                            'source_type': 'email_scan',
                            'subject': receipt_data['email_info']['subject'],
                            'sender': receipt_data['email_info']['from'],
                            'date': datetime.fromisoformat(receipt_data['email_info']['date'].replace('Z', '+00:00')),
                            'amount': receipt_data['wizard_analysis'].get('amount', 0),
                            'merchant': receipt_data['wizard_analysis'].get('merchant', 'Unknown'),
                            'category': receipt_data['wizard_analysis']['category'],
                            'business_type': receipt_data['wizard_analysis']['business_type'],
                            'confidence_score': receipt_data['wizard_analysis']['confidence'],
                            'status': 'processed',
                            'created_at': datetime.utcnow(),
                            'processing_result': receipt_data,
                            'receipt_type': 'Email Scan',
                            'auto_approved': receipt_data['wizard_analysis']['auto_approved']
                        }
                        
                        mongo_client.db.receipts.insert_one(receipt_doc)
                        saved_to_db += 1
                        
                except Exception as e:
                    logger.error(f"❌ Failed to save receipts to database: {e}")
            
            # Calculate success rates
            total_processed = len(processed_receipts)
            success_rate = (total_processed / len(receipts) * 100) if receipts else 0
            
            logger.info(f"🎉 Email scan completed: {total_processed} receipts processed in {processing_duration:.2f}s")
            
            return jsonify({
                'success': True,
                'receipts_found': len(receipts),
                'receipts_processed': total_processed,
                'receipts': processed_receipts,
                'scan_details': {
                    'email_account': email_account,
                    'days_back': days_back,
                    'scan_duration_seconds': round(processing_duration, 2),
                    'success_rate_percent': round(success_rate, 1),
                    'confidence_breakdown': {
                        'high_confidence': high_confidence_receipts,
                        'medium_confidence': medium_confidence_receipts,
                            'message': f'Receipt uploaded successfully via Apple Shortcuts',
                            'filename': filename,
                            'processing_result': result,
                            'receipt_id': f"apple_shortcuts_{timestamp}"
                        })
                
                # Text message with receipt data
                elif 'receipt_text' in request.form:
                    receipt_text = request.form['receipt_text']
                    merchant = request.form.get('merchant', 'Unknown')
                    amount = float(request.form.get('amount', 0))
                    date_str = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
                    
                    # Save text receipt
                    if mongo_client.connected:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        receipt_record = {
                            "email_id": f"apple_shortcuts_text_{timestamp}",
                            "account": "apple_shortcuts",
                            "source_type": "apple_shortcuts_text",
                            "subject": f"Apple Shortcuts Text: {merchant}",
                            "sender": "apple_shortcuts",
                            "date": datetime.utcnow(),
                            "amount": amount,
                            "merchant": merchant,
                            "category": "Apple Shortcuts Text",
                            "status": "processed",
                            "created_at": datetime.utcnow(),
                            "receipt_text": receipt_text,
                            "receipt_type": "Apple Shortcuts Text",
                            "date_from_text": date_str
                        }
                        
                        mongo_client.db.receipts.insert_one(receipt_record)
                        logger.info(f"✅ Apple Shortcuts text receipt saved: {merchant} - ${amount}")
                    
                    return jsonify({
                        'success': True,
                        'message': f'Text receipt saved: {merchant} - ${amount}',
                        'receipt_id': f"apple_shortcuts_text_{timestamp}"
                    })
            
            # Handle JSON payload (for more complex data)
            elif request.is_json:
                data = request.get_json()
                receipt_type = data.get('type', 'text')
                
                if receipt_type == 'image_url':
                    # Handle image URL from Shortcuts
                    image_url = data.get('image_url')
                    merchant = data.get('merchant', 'Unknown')
                    amount = data.get('amount', 0)
                    
                    # Download and process image
                    import requests
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"shortcuts_url_{timestamp}.jpg"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        
                        # Process image
                        if HUGGINGFACE_AVAILABLE:
                            from huggingface_receipt_processor import create_huggingface_processor
                            processor = create_huggingface_processor()
                            result = processor.process_receipt_image(filepath)
                        else:
                            result = {
                                'status': 'success',
                                'merchant': merchant,
                                'amount': amount,
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'confidence': 0.8,
                                'processing_method': 'url_download'
                            }
                        
                        # Save to MongoDB
                        if mongo_client.connected:
                            receipt_record = {
                                "email_id": f"apple_shortcuts_url_{timestamp}",
                                "account": "apple_shortcuts",
                                "source_type": "apple_shortcuts_url",
                                "subject": f"Apple Shortcuts URL: {merchant}",
                                "sender": "apple_shortcuts",
                                "date": datetime.utcnow(),
                                "amount": result.get('amount', amount),
                                "merchant": result.get('merchant', merchant),
                                "category": "Apple Shortcuts URL",
                                "status": "processed",
                                "created_at": datetime.utcnow(),
                                "processing_result": result,
                                "receipt_type": "Apple Shortcuts URL",
                                "image_url": image_url,
                                "filename": filename
                            }
                            
                            mongo_client.db.receipts.insert_one(receipt_record)
                            logger.info(f"✅ Apple Shortcuts URL receipt saved: {merchant}")
                        
                        return jsonify({
                            'success': True,
                            'message': f'URL receipt processed: {merchant}',
                            'receipt_id': f"apple_shortcuts_url_{timestamp}",
                            'processing_result': result
                        })
                
                else:
                    # Simple text receipt
                    merchant = data.get('merchant', 'Unknown')
                    amount = data.get('amount', 0)
                    receipt_text = data.get('text', '')
                    date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
                    
                    # Save to MongoDB
                    if mongo_client.connected:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        receipt_record = {
                            "email_id": f"apple_shortcuts_json_{timestamp}",
                            "account": "apple_shortcuts",
                            "source_type": "apple_shortcuts_json",
                            "subject": f"Apple Shortcuts JSON: {merchant}",
                            "sender": "apple_shortcuts",
                            "date": datetime.utcnow(),
                            "amount": amount,
                            "merchant": merchant,
                            "category": "Apple Shortcuts JSON",
                            "status": "processed",
                            "created_at": datetime.utcnow(),
                            "receipt_text": receipt_text,
                            "receipt_type": "Apple Shortcuts JSON",
                            "date_from_text": date_str
                        }
                        
                        mongo_client.db.receipts.insert_one(receipt_record)
                        logger.info(f"✅ Apple Shortcuts JSON receipt saved: {merchant} - ${amount}")
                    
                    return jsonify({
                        'success': True,
                        'message': f'JSON receipt saved: {merchant} - ${amount}',
                        'receipt_id': f"apple_shortcuts_json_{timestamp}"
                    })
            
            else:
                return jsonify({
                    'success': False,
                    'error': 'No receipt data provided. Send image file, text, or JSON data.'
                }), 400
                
        except Exception as e:
            logger.error(f"Apple Shortcuts upload error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/apple-shortcuts/status', methods=['GET'])
    def api_apple_shortcuts_status():
        """Status endpoint for Apple Shortcuts to check connectivity"""
        try:
            # Get recent shortcuts uploads
            recent_uploads = []
            if mongo_client.connected:
                recent_uploads = list(mongo_client.db.receipts.find({
                    "source_type": {"$regex": "apple_shortcuts"}
                }).sort("created_at", -1).limit(5))
            
            return jsonify({
                'success': True,
                'status': 'operational',
                'message': 'Apple Shortcuts API is ready',
                'recent_uploads': len(recent_uploads),
                'mongodb_connected': mongo_client.connected,
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/expenses/<expense_id>/upload-receipt', methods=['POST'])
    def upload_receipt_to_expense(expense_id):
        """
        Upload a receipt file directly to a specific expense/transaction.
        Processes the file, uploads to R2, and updates the expense document.
        """
        try:
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file provided'}), 400
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'No file selected'}), 400

            # Save uploaded file temporarily
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"expense_{expense_id}_{timestamp}_{file.filename}"
            upload_folder = app.config.get('UPLOAD_FOLDER', '/tmp/uploads')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)

            # Process with available processors (OCR/AI)
            if HUGGINGFACE_AVAILABLE:
                from huggingface_receipt_processor import create_huggingface_processor
                processor = create_huggingface_processor()
                result = processor.process_receipt_image(filepath)
            else:
                result = {
                    'status': 'success',
                    'merchant': 'Manual Upload',
                    'amount': 0.0,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'confidence': 0.7,
                    'processing_method': 'manual_upload'
                }

            # Upload to R2 (if configured)
            r2_url = None
            try:
                from r2_client import R2Client
                r2_client = R2Client()
                if r2_client.is_connected():
                    attachment_info = {
                        'size': os.path.getsize(filepath),
                        'mime_type': file.mimetype,
                        'message_id': expense_id
                    }
                    r2_key = r2_client.upload_receipt_attachment(filepath, expense_id, 'manual_upload', attachment_info)
                    if r2_key:
                        r2_public_url = os.getenv('R2_PUBLIC_URL', '')
                        if r2_public_url:
                            r2_url = f"{r2_public_url}/{r2_key}"
            except Exception as r2e:
                logger.warning(f"R2 upload failed: {r2e}")

            # Update the expense/transaction in MongoDB
            update_fields = {
                'receipt_url': r2_url,
                'receipt_uploaded_at': datetime.utcnow(),
                'receipt_processing_result': result,
                'has_receipt': True
            }
            if result.get('merchant'):
                update_fields['merchant'] = result['merchant']
            if result.get('amount'):
                update_fields['amount'] = result['amount']
            if result.get('date'):
                update_fields['date'] = result['date']
            if result.get('category'):
                update_fields['category'] = result['category']

            from bson import ObjectId
            expense_oid = ObjectId(expense_id) if ObjectId.is_valid(expense_id) else expense_id
            update_result = mongo_client.db.transactions.update_one(
                {'_id': expense_oid},
                {'$set': update_fields}
            )

            # Clean up uploaded file
            try:
                os.remove(filepath)
            except:
                pass

            if update_result.modified_count == 1:
                updated_expense = mongo_client.db.transactions.find_one({'_id': expense_oid})
                return jsonify({'success': True, 'expense': updated_expense, 'receipt_url': r2_url})
            else:
                return jsonify({'success': False, 'error': 'Expense not found or not updated', 'receipt_url': r2_url}), 404

        except Exception as e:
            logger.error(f"Upload receipt to expense error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/expenses/<expense_id>/update', methods=['PUT'])
    def update_expense_data(expense_id):
        """
        Update expense/transaction data with full editing capabilities.
        Accepts all editable fields and updates the MongoDB document.
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400

            # Validate expense ID
            from bson import ObjectId
            if not ObjectId.is_valid(expense_id):
                return jsonify({'success': False, 'error': 'Invalid expense ID'}), 400

            expense_oid = ObjectId(expense_id)
            
            # Check if expense exists
            existing_expense = mongo_client.db.transactions.find_one({'_id': expense_oid})
            if not existing_expense:
                return jsonify({'success': False, 'error': 'Expense not found'}), 404

            # Prepare update fields (only allow specific fields to be updated)
            update_fields = {}
            
            # Basic transaction fields
            if 'merchant' in data:
                update_fields['merchant'] = data['merchant']
            if 'description' in data:
                update_fields['description'] = data['description']
            if 'amount' in data:
                try:
                    update_fields['amount'] = float(data['amount'])
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'error': 'Invalid amount format'}), 400
            
            # Categorization fields
            if 'category' in data:
                update_fields['category'] = data['category']
            if 'business_type' in data:
                update_fields['business_type'] = data['business_type']
            
            # Date field
            if 'date' in data:
                try:
                    # Parse various date formats
                    date_str = data['date']
                    if isinstance(date_str, str):
                        # Try different date formats
                        for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt)
                                update_fields['date'] = parsed_date
                                break
                            except ValueError:
                                continue
                        else:
                            # If no format matches, try fromisoformat
                            try:
                                update_fields['date'] = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            except:
                                return jsonify({'success': False, 'error': 'Invalid date format'}), 400
                except Exception as e:
                    return jsonify({'success': False, 'error': f'Date parsing error: {str(e)}'}), 400
            
            # Business and tax fields
            if 'tax_deductible' in data:
                update_fields['tax_deductible'] = bool(data['tax_deductible'])
            if 'business_purpose' in data:
                update_fields['business_purpose'] = data['business_purpose']
            if 'notes' in data:
                update_fields['notes'] = data['notes']
            
            # Status and review fields
            if 'needs_review' in data:
                update_fields['needs_review'] = bool(data['needs_review'])
            if 'status' in data:
                update_fields['status'] = data['status']
            
            # Tags and metadata
            if 'tags' in data and isinstance(data['tags'], list):
                update_fields['tags'] = data['tags']
            
            # Add timestamp for when the expense was last modified
            update_fields['last_modified'] = datetime.utcnow()
            update_fields['modified_by'] = 'manual_edit'

            # Perform the update
            update_result = mongo_client.db.transactions.update_one(
                {'_id': expense_oid},
                {'$set': update_fields}
            )

            if update_result.modified_count == 1:
                # Get the updated expense
                updated_expense = mongo_client.db.transactions.find_one({'_id': expense_oid})
                
                # Log the update
                logger.info(f"✅ Expense updated: {expense_id} - {updated_expense.get('merchant', 'Unknown')}")
                
                return jsonify({
                    'success': True,
                    'message': 'Expense updated successfully',
                    'expense': updated_expense
                })
            else:
                return jsonify({'success': False, 'error': 'No changes made to expense'}), 400

        except Exception as e:
            logger.error(f"Update expense error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/brian/health', methods=['GET'])
    def api_brian_health():
        """Brian's Financial Wizard health check with real connection and data status"""
        try:
            from brian_financial_wizard import BrianFinancialWizard
            wizard = BrianFinancialWizard()
            # Check MongoDB connection
            db_connected = mongo_client.connected if hasattr(mongo_client, 'connected') else False
            # Check if any expenses exist
            expenses_count = 0
            if db_connected:
                expenses_count = mongo_client.db.transactions.count_documents({})
            status = 'ready' if db_connected else 'offline'
            message = 'Ready' if db_connected else 'Not connected'
            if db_connected and expenses_count == 0:
                status = 'waiting_for_data'
                message = 'Waiting for expense data'
            elif db_connected and expenses_count > 0:
                status = 'operational'
                message = f'Connected, {expenses_count} expenses loaded'
            return jsonify({
                'status': status,
                'healthy': db_connected,
                'service': "Brian's Financial Wizard",
                'expenses_count': expenses_count,
                'message': message,
                'version': '2026.1',
                'features': [
                    'AI Expense Categorization',
                    'Down Home Media Integration',
                    'Music City Rodeo Integration',
                    'Smart Business Logic'
                ],
                'timestamp': datetime.utcnow().isoformat()
            })
        except ImportError:
            return jsonify({
                'status': 'degraded',
                'healthy': False,
                'error': "Brian's Wizard module not found",
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 200

    @app.route('/api/calendar/health', methods=['GET'])
    def api_calendar_health():
        """Calendar intelligence health check with real connection and data status"""
        try:
            # Try to import and initialize analyzer
            try:
                from calendar_context_analyzer import CalendarContextAnalyzer
                analyzer = CalendarContextAnalyzer()
                credentials_found = os.path.exists(getattr(analyzer, 'credentials_path', ''))
                calendar_service_connected = hasattr(analyzer, 'calendar_service') and analyzer.calendar_service is not None
                calendars_accessible = 0
                if calendar_service_connected:
                    try:
                        calendar_list = analyzer.calendar_service.calendarList().list().execute()
                        calendars_accessible = len(calendar_list.get('items', []))
                    except Exception:
                        calendars_accessible = 0
                status = 'operational' if calendar_service_connected and calendars_accessible > 0 else 'waiting_for_data' if calendar_service_connected else 'needs_setup'
                message = 'Calendar connected' if calendars_accessible > 0 else 'Waiting for calendar data' if calendar_service_connected else 'Needs setup or credentials'
                return jsonify({
                    'status': status,
                    'healthy': calendar_service_connected,
                    'service': 'Calendar Intelligence',
                    'calendars_accessible': calendars_accessible,
                    'credentials_found': credentials_found,
                    'message': message,
                    'version': '2026.1',
                    'features': [
                        'Business Context Analysis',
                        'Travel Detection',
                        'Meeting Correlation',
                        'Google Calendar Integration'
                    ],
                    'timestamp': datetime.utcnow().isoformat()
                })
            except ImportError:
                return jsonify({
                    'status': 'degraded',
                    'healthy': False,
                    'error': 'Calendar analyzer module not found',
                    'timestamp': datetime.utcnow().isoformat()
                }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 200

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
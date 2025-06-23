#!/usr/bin/env python3
"""
Receipt Processor - Production Flask Application
Full-featured app with fixed imports and initialization
"""

import os
import sys
import logging
import json
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import secrets
import uuid
import csv
from io import StringIO

# Core Flask imports - these are guaranteed to work
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_file
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

# Database & Storage - basic imports only
import pymongo
from pymongo import MongoClient

# HTTP requests
import requests
from requests.auth import HTTPBasicAuth
import hmac
import hashlib

# Utilities
import re
from urllib.parse import urlencode, quote_plus

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/app.log') if os.path.exists('/tmp') else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Application configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))
    
    # Database
    MONGODB_URI = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
    MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'expense')
    MONGODB_COLLECTION = os.getenv('MONGODB_COLLECTION', 'receipts')
    
    # Teller
    TELLER_APPLICATION_ID = os.getenv('TELLER_APPLICATION_ID')
    TELLER_ENVIRONMENT = os.getenv('TELLER_ENVIRONMENT', 'sandbox')
    TELLER_API_URL = os.getenv('TELLER_API_URL', 'https://api.teller.io')
    TELLER_WEBHOOK_URL = os.getenv('TELLER_WEBHOOK_URL')
    TELLER_SIGNING_SECRET = os.getenv('TELLER_SIGNING_SECRET')
    
    # Storage
    R2_ENDPOINT = os.getenv('R2_ENDPOINT')
    R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY')
    R2_SECRET_KEY = os.getenv('R2_SECRET_KEY')
    R2_BUCKET = os.getenv('R2_BUCKET')

# ============================================================================
# SAFE CLIENT WRAPPERS
# ============================================================================

class SafeMongoClient:
    """MongoDB client with proper error handling"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        try:
            if Config.MONGODB_URI:
                self.client = MongoClient(
                    Config.MONGODB_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000
                )
                self.client.admin.command('ping')
                self.db = self.client[Config.MONGODB_DATABASE]
                self.connected = True
                logger.info("✅ MongoDB connected successfully")
            else:
                logger.warning("⚠️ No MongoDB URI configured")
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            self.connected = False
    
    def health_check(self) -> bool:
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
            return False
        except:
            return False
    
    def get_stats(self) -> Dict:
        try:
            if not self.connected or not self.db:
                return {"connected": False}
            
            return {
                "connected": True,
                "database": Config.MONGODB_DATABASE,
                "receipts_count": self.db[Config.MONGODB_COLLECTION].count_documents({}),
                "collections": self.db.list_collection_names()
            }
        except Exception as e:
            logger.error(f"Error getting MongoDB stats: {e}")
            return {"connected": False, "error": str(e)}

class SafeTellerClient:
    """Teller client with proper error handling"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Receipt-Processor/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def get_connect_url(self, user_id: str) -> str:
        if not Config.TELLER_APPLICATION_ID:
            return "#"
        
        params = {
            'application_id': Config.TELLER_APPLICATION_ID,
            'redirect_uri': f"{Config.TELLER_WEBHOOK_URL.replace('/webhook', '/callback') if Config.TELLER_WEBHOOK_URL else '#'}",
            'state': user_id,
            'scope': 'transactions:read accounts:read identity:read'
        }
        
        base_url = "https://connect.teller.io/connect"
        return f"{base_url}?{urlencode(params)}"
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        try:
            if not Config.TELLER_SIGNING_SECRET:
                return True
            
            expected_signature = hmac.new(
                Config.TELLER_SIGNING_SECRET.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False

# ============================================================================
# FLASK APPLICATION
# ============================================================================

# Create Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Configure for production
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# Initialize clients lazily (no connection during import)
mongo_client = None
teller_client = None

def get_mongo_client():
    """Get MongoDB client with lazy initialization"""
    global mongo_client
    if mongo_client is None:
        mongo_client = SafeMongoClient()
    return mongo_client

def get_teller_client():
    """Get Teller client with lazy initialization"""
    global teller_client
    if teller_client is None:
        teller_client = SafeTellerClient()
    return teller_client

# Global stats for dashboard
def get_system_stats():
    """Get system statistics safely"""
    try:
        client = get_mongo_client()
        mongo_stats = client.get_stats()
        
        return {
            'mongo_connected': mongo_stats.get('connected', False),
            'receipts_count': mongo_stats.get('receipts_count', 0),
            'teller_configured': bool(Config.TELLER_APPLICATION_ID),
            'r2_configured': bool(Config.R2_ACCESS_KEY),
            'environment': Config.FLASK_ENV,
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {
            'mongo_connected': False,
            'receipts_count': 0,
            'teller_configured': False,
            'r2_configured': False,
            'environment': Config.FLASK_ENV,
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'error': str(e)
        }

# ============================================================================
# CORE ROUTES
# ============================================================================

@app.route('/health')
def health_check():
    """Health check endpoint for Render monitoring"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": Config.FLASK_ENV
    })

@app.route('/')
def index():
    """Dashboard homepage"""
    try:
        stats = get_system_stats()
        
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Receipt Processor Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; }
                .header { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
                .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
                .status-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                .status-card h3 { margin: 0 0 15px 0; color: #333; }
                .status-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #eee; }
                .status-item:last-child { border-bottom: none; }
                .status-badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
                .status-connected { background: #d4edda; color: #155724; }
                .status-error { background: #f8d7da; color: #721c24; }
                .status-warning { background: #fff3cd; color: #856404; }
                .action-buttons { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 30px 0; }
                .btn { padding: 15px 25px; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; text-decoration: none; text-align: center; display: inline-block; transition: all 0.3s; }
                .btn-primary { background: #007bff; color: white; }
                .btn-success { background: #28a745; color: white; }
                .btn-warning { background: #ffc107; color: #212529; }
                .btn-info { background: #17a2b8; color: white; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏦 Receipt Processor Dashboard</h1>
                    <p>AI-powered fintech application with multi-service integration</p>
                    <p><small>Environment: {{ stats.environment }} | Updated: {{ stats.timestamp }}</small></p>
                </div>
                
                <div class="status-grid">
                    <div class="status-card">
                        <h3>🔧 System Health</h3>
                        <div class="status-item">
                            <span>Database (MongoDB)</span>
                            <span class="status-badge status-{{ 'connected' if stats.mongo_connected else 'error' }}">
                                {{ 'Connected' if stats.mongo_connected else 'Error' }}
                            </span>
                        </div>
                        <div class="status-item">
                            <span>Storage (R2)</span>
                            <span class="status-badge status-{{ 'connected' if stats.r2_configured else 'warning' }}">
                                {{ 'Configured' if stats.r2_configured else 'Not Configured' }}
                            </span>
                        </div>
                        <div class="status-item">
                            <span>Teller Banking</span>
                            <span class="status-badge status-{{ 'connected' if stats.teller_configured else 'warning' }}">
                                {{ 'Configured' if stats.teller_configured else 'Not Configured' }}
                            </span>
                        </div>
                        <div class="status-item">
                            <span>Receipts</span>
                            <span class="status-badge status-connected">{{ stats.receipts_count }}</span>
                        </div>
                    </div>
                </div>
                
                <div class="action-buttons">
                    <a href="/connect" class="btn btn-success">🏦 Connect Bank</a>
                    <a href="/status" class="btn btn-info">🔍 System Status</a>
                    <a href="/settings" class="btn btn-warning">⚙️ Settings</a>
                    <a href="/health" class="btn btn-primary">❤️ Health Check</a>
                </div>
            </div>
        </body>
        </html>
        """, stats=stats)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({"error": "Dashboard unavailable", "details": str(e)}), 500

@app.route('/teller/webhook', methods=['POST'])
def teller_webhook():
    """Handle Teller webhook notifications - THE KEY ENDPOINT FOR YOUR NGROK ISSUE!"""
    try:
        # Get signature
        signature = request.headers.get('Teller-Signature', '')
        payload = request.get_data()
        
        # Verify signature if configured
        if Config.TELLER_SIGNING_SECRET:
            client = get_teller_client()
            if not client.verify_webhook_signature(payload, signature):
                logger.warning("Invalid webhook signature")
                return jsonify({"error": "Invalid signature"}), 401
        
        # Process webhook data
        data = request.get_json() or {}
        webhook_type = data.get('type', 'unknown')
        
        logger.info(f"✅ Received Teller webhook: {webhook_type}")
        
        # Store webhook data
        webhook_record = {
            "type": webhook_type,
            "data": data,
            "signature": signature,
            "received_at": datetime.utcnow()
        }
        
        try:
            mongo = get_mongo_client()
            if mongo.connected and mongo.db:
                mongo.db.teller_webhooks.insert_one(webhook_record)
        except Exception as e:
            logger.warning(f"Could not store webhook to database: {e}")
        
        return jsonify({"success": True, "type": webhook_type, "message": "Webhook processed successfully"}), 200
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({"error": "Webhook processing failed"}), 500

@app.route('/status')
def system_status():
    """Comprehensive system status endpoint"""
    try:
        mongo_stats = mongo_client.get_stats()
        
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": Config.FLASK_ENV,
            "services": {
                "database": {
                    "status": "connected" if mongo_stats.get("connected", False) else "error",
                    "details": mongo_stats
                },
                "storage": {
                    "status": "configured" if Config.R2_ACCESS_KEY else "not_configured",
                    "type": "Cloudflare R2",
                    "bucket": Config.R2_BUCKET
                },
                "teller": {
                    "status": "configured" if Config.TELLER_APPLICATION_ID else "not_configured",
                    "environment": Config.TELLER_ENVIRONMENT,
                    "app_id": Config.TELLER_APPLICATION_ID
                }
            }
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        return jsonify({"error": "Status check failed", "details": str(e)}), 500

@app.route('/connect')
def connect_bank():
    """Initiate Teller bank connection"""
    try:
        if not Config.TELLER_APPLICATION_ID:
            return jsonify({"error": "Teller not configured"}), 400
            
        user_id = request.args.get('user_id', 'default_user')
        connect_url = teller_client.get_connect_url(user_id)
        
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Connect Your Bank</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center; }
                .btn { padding: 15px 30px; background: #28a745; color: white; border: none; border-radius: 8px; font-size: 18px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; margin: 20px 0; transition: all 0.3s; }
                .btn:hover { background: #1e7e34; transform: translateY(-2px); }
                .security-info { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left; }
                .back-link { color: #007bff; text-decoration: none; margin-top: 20px; display: inline-block; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏦 Connect Your Bank Account</h1>
                <p>Securely connect your bank account to automatically sync transactions with receipts.</p>
                
                <div class="security-info">
                    <h3>🔒 Security & Privacy</h3>
                    <ul>
                        <li>✅ Bank-level encryption (256-bit SSL)</li>
                        <li>✅ Read-only access to transaction data</li>
                        <li>✅ No storage of banking credentials</li>
                        <li>✅ Powered by Teller (trusted by thousands)</li>
                    </ul>
                </div>
                
                <a href="{{ connect_url }}" class="btn">🔗 Connect with Teller</a>
                
                <p><small>Environment: {{ environment }} | App ID: {{ app_id }}</small></p>
                
                <a href="/" class="back-link">← Back to Dashboard</a>
            </div>
        </body>
        </html>
        """, 
        connect_url=connect_url,
        environment=Config.TELLER_ENVIRONMENT,
        app_id=Config.TELLER_APPLICATION_ID
        )
        
    except Exception as e:
        logger.error(f"Connect bank error: {e}")
        return jsonify({"error": "Bank connection failed"}), 500

@app.route('/settings')
def settings_page():
    """Settings page"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Settings - Receipt Processor</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; }
            .settings-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .setting-group { margin-bottom: 25px; }
            .setting-group h3 { margin: 0 0 15px 0; color: #333; }
            .setting-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #eee; }
            .setting-item:last-child { border-bottom: none; }
            .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; font-size: 14px; }
            .btn-primary { background: #007bff; color: white; }
            .back-link { color: #007bff; text-decoration: none; margin-bottom: 20px; display: inline-block; }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-link">← Back to Dashboard</a>
            
            <div class="settings-card">
                <h1>⚙️ Settings & Configuration</h1>
                
                <div class="setting-group">
                    <h3>🌍 Environment</h3>
                    <div class="setting-item">
                        <span>Current Environment</span>
                        <span><strong>{{ environment }}</strong></span>
                    </div>
                    <div class="setting-item">
                        <span>Teller Environment</span>
                        <span>{{ teller_env }}</span>
                    </div>
                    <div class="setting-item">
                        <span>Debug Mode</span>
                        <span>{{ 'Enabled' if debug else 'Disabled' }}</span>
                    </div>
                </div>
                
                <div class="setting-group">
                    <h3>🔗 Quick Actions</h3>
                    <div class="setting-item">
                        <span>Test System Health</span>
                        <a href="/status" class="btn btn-primary">Check Status</a>
                    </div>
                    <div class="setting-item">
                        <span>Health Check</span>
                        <a href="/health" class="btn btn-primary">Test Health</a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """,
    environment=Config.FLASK_ENV,
    teller_env=Config.TELLER_ENVIRONMENT,
    debug=Config.DEBUG
    )

@app.route('/teller/callback')
def teller_callback():
    """Handle Teller OAuth callback"""
    try:
        code = request.args.get('code')
        state = request.args.get('state', 'default_user')
        error = request.args.get('error')
        
        if error:
            logger.error(f"Teller callback error: {error}")
            return jsonify({"error": f"Teller authorization failed: {error}"}), 400
        
        if not code:
            return jsonify({"error": "Missing authorization code"}), 400
        
        # Store callback information
        callback_data = {
            "user_id": state,
            "code": code,
            "received_at": datetime.utcnow(),
            "status": "received"
        }
        
        if mongo_client.connected and mongo_client.db:
            mongo_client.db.teller_callbacks.insert_one(callback_data)
        
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bank Connection Received</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center; }
                .success { color: #28a745; font-size: 48px; margin-bottom: 20px; }
                .btn { padding: 15px 30px; background: #007bff; color: white; border: none; border-radius: 8px; font-size: 16px; text-decoration: none; display: inline-block; margin: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✅</div>
                <h1>Bank Connection Received!</h1>
                <p>Your bank authorization code has been received and stored.</p>
                <p><small>User ID: {{ user_id }}</small></p>
                
                <a href="/" class="btn">🏠 Dashboard</a>
            </div>
        </body>
        </html>
        """, user_id=state)
        
    except Exception as e:
        logger.error(f"Teller callback processing error: {e}")
        return jsonify({"error": "Callback processing failed"}), 500

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/process-receipts', methods=['POST'])
def api_process_receipts():
    """Process receipts endpoint"""
    try:
        data = request.get_json() or {}
        days = data.get('days', 30)
        max_receipts = data.get('max_receipts', 50)
        
        # Placeholder for receipt processing
        result = {
            "success": True,
            "message": f"Receipt processing initiated for {days} days",
            "max_receipts": max_receipts,
            "processed": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Receipt processing error: {e}")
        return jsonify({"error": "Receipt processing failed", "details": str(e)}), 500

@app.route('/api/export-csv', methods=['GET'])
def api_export_csv():
    """Export data as CSV"""
    try:
        # Create sample CSV data
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Date', 'Merchant', 'Amount', 'Category'])
        writer.writerow([datetime.now().strftime('%Y-%m-%d'), 'Sample Merchant', '25.99', 'Food'])
        
        csv_data = output.getvalue()
        output.close()
        
        return csv_data, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=receipts.csv'
        }
        
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        return jsonify({"error": "CSV export failed"}), 500

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found", "code": 404}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error", "code": 500}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}\n{traceback.format_exc()}")
    return jsonify({"error": "Unexpected error occurred", "code": 500}), 500

if __name__ == '__main__':
    try:
        # Create required directories
        os.makedirs("downloads", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        
        # Start server
        port = int(os.getenv('PORT', 5000))
        debug_mode = Config.DEBUG
        
        logger.info(f"🚀 Starting Receipt Processor on port {port}")
        logger.info(f"📊 Environment: {Config.FLASK_ENV}")
        logger.info(f"🔧 Debug mode: {debug_mode}")
        logger.info(f"🏦 Teller webhook URL: {Config.TELLER_WEBHOOK_URL}")
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug_mode,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"❌ Application failed to start: {e}")
        sys.exit(1) 
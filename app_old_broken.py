#!/usr/bin/env python3
"""
IMMEDIATE FIX for Render.com freezing issue
This replaces your current app.py to fix the deployment problems
"""

import os
import sys
import logging
import json
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import secrets

# Core Flask imports
from flask import Flask, request, jsonify, render_template_string, redirect
from werkzeug.middleware.proxy_fix import ProxyFix

# Database & HTTP
import pymongo
from pymongo import MongoClient
import requests
import hmac
import hashlib

# Utilities
from urllib.parse import urlencode

# Configure basic logging for Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ============================================================================
# FIXED CONFIGURATION
# ============================================================================

class Config:
    """Fixed configuration that works on Render"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))
    
    # MongoDB - CRITICAL: Check both MONGO_URI and MONGODB_URI
    MONGODB_URI = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
    MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'expense')
    
    # Teller Configuration
    TELLER_APPLICATION_ID = os.getenv('TELLER_APPLICATION_ID', 'app_pbvpiocruhfnvkhf1k000')
    TELLER_ENVIRONMENT = os.getenv('TELLER_ENVIRONMENT', 'development')  # Changed to development for real data
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
    
    logger.info(f"✅ App created - Environment: {Config.TELLER_ENVIRONMENT}")
    
    # ========================================================================
    # CORE ROUTES
    # ========================================================================
    
    @app.route('/health')
    def health():
        """Health check for Render"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": Config.TELLER_ENVIRONMENT,
            "mongo": mongo_client.connected
        }), 200
    
    @app.route('/status')
    def status():
        """System status"""
        try:
            mongo_stats = mongo_client.get_stats()
            
            return jsonify({
                "timestamp": datetime.utcnow().isoformat(),
                "environment": Config.TELLER_ENVIRONMENT,
                "application_id": Config.TELLER_APPLICATION_ID,
                "services": {
                    "mongodb": {
                        "status": "connected" if mongo_stats.get("connected") else "error",
                        "stats": mongo_stats
                    },
                    "teller": {
                        "status": "configured",
                        "environment": Config.TELLER_ENVIRONMENT,
                        "application_id": Config.TELLER_APPLICATION_ID
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
            mongo_stats = mongo_client.get_stats()
            
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Receipt Processor - Teller Development Tier</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .header { text-align: center; margin-bottom: 40px; }
                    .title { font-size: 3rem; margin-bottom: 10px; }
                    .subtitle { font-size: 1.2rem; opacity: 0.9; margin-bottom: 20px; }
                    .tier-badge { background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 20px; display: inline-block; margin-bottom: 30px; }
                    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
                    .card { background: rgba(255,255,255,0.1); backdrop-filter: blur(20px); border-radius: 16px; padding: 30px; border: 1px solid rgba(255,255,255,0.2); }
                    .card h3 { margin-top: 0; font-size: 1.5rem; }
                    .stat { display: flex; justify-content: space-between; margin: 15px 0; }
                    .stat-value { font-weight: bold; }
                    .status-connected { color: #4ade80; }
                    .status-error { color: #f87171; }
                    .status-warning { color: #fbbf24; }
                    .btn { background: rgba(255,255,255,0.2); color: white; border: none; padding: 15px 30px; border-radius: 12px; font-size: 16px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; margin: 10px; transition: all 0.3s; }
                    .btn:hover { background: rgba(255,255,255,0.3); transform: translateY(-2px); }
                    .action-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 class="title">🏦 Receipt Processor</h1>
                        <p class="subtitle">Real Banking Integration with AI-Powered Receipt Processing</p>
                        <div class="tier-badge">{{ environment.title() }} Tier - Real Banking Data</div>
                        <p><small>Updated: {{ timestamp }}</small></p>
                    </div>
                    
                    <div class="grid">
                        <div class="card">
                            <h3>📊 System Status</h3>
                            <div class="stat">
                                <span>Database (MongoDB)</span>
                                <span class="stat-value status-{{ 'connected' if mongo_stats.connected else 'error' }}">
                                    {{ 'Connected' if mongo_stats.connected else 'Error' }}
                                </span>
                            </div>
                            <div class="stat">
                                <span>Teller Banking</span>
                                <span class="stat-value status-connected">{{ environment.title() }}</span>
                            </div>
                            <div class="stat">
                                <span>Storage (R2)</span>
                                <span class="stat-value status-{{ 'connected' if r2_configured else 'warning' }}">
                                    {{ 'Connected' if r2_configured else 'Not Configured' }}
                                </span>
                            </div>
                            <div class="stat">
                                <span>Gmail Accounts</span>
                                <span class="stat-value status-connected">{{ gmail_accounts }} Configured</span>
                            </div>
                        </div>
                        
                        <div class="card">
                            <h3>💰 Banking Data</h3>
                            <div class="stat">
                                <span>Bank Accounts</span>
                                <span class="stat-value">{{ mongo_stats.collections.teller_accounts if mongo_stats.connected else 0 }}</span>
                            </div>
                            <div class="stat">
                                <span>Transactions</span>
                                <span class="stat-value">{{ mongo_stats.collections.teller_transactions if mongo_stats.connected else 0 }}</span>
                            </div>
                            <div class="stat">
                                <span>Receipts</span>
                                <span class="stat-value">{{ mongo_stats.collections.receipts if mongo_stats.connected else 0 }}</span>
                            </div>
                            <div class="stat">
                                <span>Webhooks</span>
                                <span class="stat-value">{{ mongo_stats.collections.teller_webhooks if mongo_stats.connected else 0 }}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="action-grid">
                        <a href="/connect" class="btn">🏦 Connect Bank Account</a>
                        <a href="/accounts" class="btn">💳 View Accounts</a>
                        <a href="/transactions" class="btn">💰 Recent Transactions</a>
                        <a href="/process" class="btn">🔄 Process Receipts</a>
                        <a href="/status" class="btn">📊 System Status</a>
                        <a href="/settings" class="btn">⚙️ Settings</a>
                    </div>
                </div>
            </body>
            </html>
            """,
            mongo_stats=mongo_stats,
            environment=Config.TELLER_ENVIRONMENT,
            timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            r2_configured=bool(Config.R2_ACCESS_KEY),
            gmail_accounts=len(Config.GMAIL_ACCOUNTS)
            )
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return jsonify({"error": "Dashboard unavailable"}), 500
    
    @app.route('/connect')
    def connect():
        """Bank connection page"""
        try:
            user_id = request.args.get('user_id', 'default_user')
            connect_url = teller_client.get_connect_url(user_id)
            
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Connect Bank - Teller Development Tier</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
                    .container { background: rgba(255,255,255,0.1); backdrop-filter: blur(20px); padding: 40px; border-radius: 20px; text-align: center; max-width: 600px; color: white; border: 1px solid rgba(255,255,255,0.2); }
                    .btn { background: #10b981; color: white; border: none; padding: 15px 30px; border-radius: 12px; font-size: 18px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; margin: 20px 0; transition: all 0.3s; }
                    .btn:hover { background: #059669; transform: translateY(-2px); }
                    .tier-info { background: rgba(16, 185, 129, 0.1); padding: 20px; border-radius: 12px; margin: 20px 0; border-left: 4px solid #10b981; }
                    .back-link { color: rgba(255,255,255,0.8); text-decoration: none; margin-top: 20px; display: inline-block; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🏦 Connect Your Real Bank Account</h1>
                    <p>Connect your actual bank account using Teller's Development tier for real banking data integration.</p>
                    
                    <div class="tier-info">
                        <h4>🔧 Teller Development Tier Features</h4>
                        <ul style="text-align: left;">
                            <li>✅ Real banking data (up to 100 connections)</li>
                            <li>✅ Production-grade security</li>
                            <li>✅ Live transaction webhooks</li>
                            <li>✅ Free for development use</li>
                        </ul>
                    </div>
                    
                    <a href="{{ connect_url }}" class="btn">🔗 Connect Real Bank Account</a>
                    
                    <p><small>User ID: {{ user_id }} | Tier: {{ tier }} | App ID: {{ app_id }}</small></p>
                    
                    <a href="/" class="back-link">← Back to Dashboard</a>
                </div>
            </body>
            </html>
            """,
            connect_url=connect_url,
            user_id=user_id,
            tier=Config.TELLER_ENVIRONMENT,
            app_id=Config.TELLER_APPLICATION_ID
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
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
    
    @app.route('/teller/callback')
    def teller_callback():
        """Handle Teller OAuth callback"""
        try:
            code = request.args.get('code')
            state = request.args.get('state', 'default_user')
            error = request.args.get('error')
            
            if error:
                return jsonify({"error": f"Authorization failed: {error}"}), 400
            
            if not code:
                return jsonify({"error": "Missing authorization code"}), 400
            
            # Store callback info
            if mongo_client.connected:
                callback_data = {
                    "user_id": state,
                    "code": code,
                    "received_at": datetime.utcnow()
                }
                mongo_client.db.teller_callbacks.insert_one(callback_data)
            
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Bank Connected!</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
                    .container { background: white; padding: 40px; border-radius: 20px; text-align: center; max-width: 500px; }
                    .success { font-size: 3rem; margin-bottom: 20px; }
                    .btn { background: #667eea; color: white; border: none; padding: 12px 24px; border-radius: 8px; text-decoration: none; display: inline-block; margin: 10px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success">🎉</div>
                    <h1>Bank Account Connected!</h1>
                    <p>Your bank authorization has been received successfully.</p>
                    <p><small>User ID: {{ user_id }}</small></p>
                    <a href="/" class="btn">🏠 Dashboard</a>
                </div>
            </body>
            </html>
            """, user_id=state)
            
        except Exception as e:
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
"""
Receipt Processor Flask Application
Main application factory and configuration
"""

import os
import secrets
from datetime import datetime
from typing import Dict, Optional

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from pymongo import MongoClient
import requests
from urllib.parse import urlencode
import logging
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import configuration
from .config import config

# Import services
from .services.mongo_service import SafeMongoClient
from .services.teller_service import SafeTellerClient
from .services.r2_service import SafeR2Client

# Import API blueprints
from .api import receipts, transactions, health, banking
from .api import dashboard

# Import utils
from .utils.security import setup_security

def create_app(config_name=None):
    """Create and configure Flask application"""
    
    # Determine configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, app.config['LOG_LEVEL']),
        format=app.config['LOG_FORMAT']
    )
    
    # Setup CORS
    CORS(app, 
         origins=app.config['CORS_ORIGINS'],
         supports_credentials=app.config['CORS_SUPPORTS_CREDENTIALS'])
    
    # Setup security middleware
    setup_security(app)
    
    # Initialize services
    with app.app_context():
        from .services.mongo_service import MongoService
        from .services.r2_service import R2Service
        from .services.teller_service import TellerService
        from .services.ai_service import AIService
        from .services.bank_service import BankService
        from .services.receipt_service import ReceiptService
        from .services.transaction_service import TransactionService
        
        mongo_service = MongoService()
        teller_service = TellerService()
        teller_client = teller_service.client  # Get the SafeTellerClient from TellerService
        bank_service = BankService(mongo_service, teller_client)
        transaction_service = TransactionService(mongo_service)
        app.mongo_service = mongo_service
        app.teller_service = teller_service
        app.bank_service = bank_service
        app.transaction_service = transaction_service
        app.r2_service = R2Service()
        app.ai_service = AIService()
        app.receipt_service = ReceiptService(app.mongo_service)
    
    # Register blueprints
    from .api.health import bp as health_bp
    from .api.receipts import bp as receipts_bp
    from .api.transactions import bp as transactions_bp
    from .api.banking import bp as banking_bp
    from .api.dashboard import bp as dashboard_bp
    from .api.auth import bp as auth_bp
    from .api.main import bp as main_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(receipts_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(banking_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
    
    @app.errorhandler(413)
    def too_large(error):
        return {'error': 'File too large'}, 413
    
    # Security error handlers
    @app.errorhandler(401)
    def unauthorized(error):
        return {'error': 'Unauthorized'}, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return {'error': 'Forbidden'}, 403
    
    @app.errorhandler(429)
    def too_many_requests(error):
        return {'error': 'Too many requests'}, 429
    
    logger.info(f"✅ App created - Environment: {config_name}")
    
    return app 
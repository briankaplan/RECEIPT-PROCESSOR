#!/usr/bin/env python3
"""
Receipt Processor - Health-First Minimal Version
Ensures health endpoint works immediately, then adds features
"""

import os
import logging
from datetime import datetime
from flask import Flask, jsonify
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Minimal Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')

@app.route('/health')
def health_check():
    """Health check endpoint - GUARANTEED to work"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": os.getenv('FLASK_ENV', 'production'),
        "message": "Health endpoint working!"
    })

@app.route('/')
def index():
    """Minimal homepage"""
    return """
    <h1>🏦 Receipt Processor</h1>
    <p>Health-first deployment test</p>
    <a href="/health">Health Check</a>
    """

@app.route('/teller/webhook', methods=['POST'])
def teller_webhook():
    """Minimal webhook handler"""
    logger.info("✅ Webhook received")
    return jsonify({"success": True, "message": "Webhook received"})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"🚀 Starting minimal health-first app on port {port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    ) 
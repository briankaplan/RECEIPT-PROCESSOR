#!/usr/bin/env python3
"""Ultra-minimal Flask test - no external dependencies"""

import os
from datetime import datetime
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/')
def index():
    return "<h1>Ultra-minimal test</h1><a href='/health'>Health</a>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting ultra-minimal app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 
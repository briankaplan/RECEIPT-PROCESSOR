#!/usr/bin/env python3

print("=== DEBUG APP STARTING ===")

import os
print(f"PORT env var: {os.getenv('PORT', 'NOT SET')}")
print(f"FLASK_ENV: {os.getenv('FLASK_ENV', 'NOT SET')}")

try:
    from flask import Flask
    print("✅ Flask imported successfully")
    
    app = Flask(__name__)
    print("✅ Flask app created")
    
    @app.route('/health')
    def health():
        return "HEALTHY"
    
    @app.route('/')
    def home():
        return "DEBUG APP WORKING"
    
    print("✅ Routes defined")
    
    if __name__ == '__main__':
        port = int(os.getenv('PORT', 5000))
        print(f"🚀 Starting on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    
    print("✅ App configured successfully")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc() 
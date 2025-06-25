#!/usr/bin/env python3
"""
Comprehensive API Endpoint Test
Tests all API endpoints for import issues, missing dependencies, and common problems
"""

import sys
import os
import importlib
import inspect
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all imports used in the app"""
    print("🔍 Testing All Imports")
    print("=" * 50)
    
    # Core imports that should always work
    core_imports = [
        'os', 'sys', 'json', 'logging', 'secrets', 'requests', 
        'hmac', 'hashlib', 'base64', 'tempfile', 'time',
        'urllib.parse', 'datetime', 'typing', 'werkzeug.middleware.proxy_fix',
        'flask', 'pymongo', 'bson'
    ]
    
    # Optional imports that might fail
    optional_imports = [
        ('gspread', 'Google Sheets integration'),
        ('google.oauth2.service_account', 'Google OAuth2'),
        ('pytesseract', 'OCR processing'),
        ('PIL', 'Image processing'),
        ('PyPDF2', 'PDF processing'),
        ('huggingface_receipt_processor', 'HuggingFace receipt processor'),
        ('persistent_memory', 'Persistent memory system'),
        ('enhanced_transaction_utils', 'Enhanced transaction utilities'),
        ('brian_financial_wizard', "Brian's Financial Wizard"),
        ('email_receipt_detector', 'Email receipt detector'),
        ('calendar_api', 'Calendar API integration'),
        ('mongo_client', 'MongoDB client'),
        ('sheets_client', 'Google Sheets client'),
        ('teller_client', 'Teller client'),
        ('r2_client', 'R2 storage client'),
        ('gmail_client', 'Gmail client'),
        ('google_photos_client', 'Google Photos client'),
        ('huggingface_client', 'HuggingFace client')
    ]
    
    # Test core imports
    print("📦 Core Imports:")
    for module in core_imports:
        try:
            importlib.import_module(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
    
    print("\n📦 Optional Imports:")
    for module, description in optional_imports:
        try:
            importlib.import_module(module)
            print(f"  ✅ {module} ({description})")
        except ImportError as e:
            print(f"  ⚠️ {module} ({description}): {e}")

def test_app_creation():
    """Test app creation and basic functionality"""
    print("\n🚀 Testing App Creation")
    print("=" * 50)
    
    try:
        from app import create_app, Config
        app = create_app()
        print("✅ App created successfully")
        
        # Test basic config
        print(f"✅ Config loaded - Environment: {Config.TELLER_ENVIRONMENT}")
        print(f"✅ MongoDB URI configured: {'Yes' if Config.MONGODB_URI else 'No'}")
        print(f"✅ Teller App ID: {Config.TELLER_APPLICATION_ID}")
        
        return app
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        return None

def test_api_endpoints(app):
    """Test all API endpoints for basic functionality"""
    if not app:
        return
    
    print("\n🌐 Testing API Endpoints")
    print("=" * 50)
    
    # Get all routes from the app
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': str(rule)
            })
    
    # Sort routes by endpoint name
    routes.sort(key=lambda x: x['endpoint'])
    
    print(f"📊 Found {len(routes)} API endpoints:")
    
    # Test each endpoint
    working_endpoints = 0
    problematic_endpoints = []
    
    for route in routes:
        endpoint = route['endpoint']
        methods = route['methods']
        rule = route['rule']
        
        try:
            # Try to get the view function
            view_func = app.view_functions.get(endpoint)
            if view_func:
                # Check if the function can be called (basic test)
                sig = inspect.signature(view_func)
                print(f"  ✅ {endpoint} ({', '.join(methods)}) - {rule}")
                working_endpoints += 1
            else:
                print(f"  ❌ {endpoint} - View function not found")
                problematic_endpoints.append(endpoint)
        except Exception as e:
            print(f"  ❌ {endpoint} - Error: {e}")
            problematic_endpoints.append(endpoint)
    
    print(f"\n📈 Summary:")
    print(f"  ✅ Working endpoints: {working_endpoints}")
    print(f"  ❌ Problematic endpoints: {len(problematic_endpoints)}")
    
    if problematic_endpoints:
        print(f"\n⚠️ Problematic endpoints:")
        for endpoint in problematic_endpoints:
            print(f"  - {endpoint}")

def test_dependencies():
    """Test if all required dependencies are available"""
    print("\n📋 Testing Dependencies")
    print("=" * 50)
    
    # Check requirements.txt
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        print("✅ requirements.txt found")
        
        with open(requirements_file, 'r') as f:
            requirements = f.read()
        
        # Check for common problematic packages
        problematic_packages = [
            'gspread', 'google-auth', 'pytesseract', 'Pillow', 'PyPDF2',
            'huggingface-hub', 'transformers', 'torch', 'pymongo', 'flask'
        ]
        
        for package in problematic_packages:
            if package in requirements:
                print(f"  ✅ {package} in requirements.txt")
            else:
                print(f"  ⚠️ {package} not in requirements.txt")
    else:
        print("❌ requirements.txt not found")

def test_environment_variables():
    """Test environment variable configuration"""
    print("\n🔧 Testing Environment Variables")
    print("=" * 50)
    
    from app import Config
    
    # Check critical environment variables
    critical_vars = [
        'MONGODB_URI', 'MONGO_URI', 'TELLER_APPLICATION_ID', 
        'TELLER_ENVIRONMENT', 'SECRET_KEY'
    ]
    
    for var in critical_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'SECRET' in var or 'KEY' in var or 'URI' in var:
                masked_value = value[:8] + "..." if len(value) > 8 else "***"
                print(f"  ✅ {var}: {masked_value}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚠️ {var}: Not set")

def test_file_structure():
    """Test if required files and directories exist"""
    print("\n📁 Testing File Structure")
    print("=" * 50)
    
    required_files = [
        'credentials/teller_certificate.b64',
        'credentials/teller_private_key.b64',
        'credentials/service_account.json',
        'templates/index_pwa.html',
        'static/style.css',
        'static/script.js'
    ]
    
    required_dirs = [
        'logs',
        'uploads',
        'templates',
        'static',
        'credentials'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - Missing")
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ❌ {dir_path}/ - Missing")

def main():
    """Run all tests"""
    print("🧪 COMPREHENSIVE API ENDPOINT TEST")
    print("=" * 60)
    
    # Run all tests
    test_imports()
    app = test_app_creation()
    test_api_endpoints(app)
    test_dependencies()
    test_environment_variables()
    test_file_structure()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("\n💡 Next steps:")
    print("  1. If any imports failed, install missing packages: pip install <package>")
    print("  2. If any endpoints failed, check the specific error messages")
    print("  3. If any files are missing, create them or update paths")
    print("  4. Start the app: python app.py")

if __name__ == "__main__":
    main() 
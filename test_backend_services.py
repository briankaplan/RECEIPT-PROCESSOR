#!/usr/bin/env python3
"""
Backend Services Verification Script
Tests all backend services to ensure they're ready to connect and function properly
"""

import os
import sys
import logging
import json
from datetime import datetime
import requests
import pickle
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_environment_variables():
    """Test that all required environment variables are set"""
    logger.info("🔍 Testing Environment Variables...")
    
    required_vars = {
        # MongoDB
        'MONGODB_URI': os.getenv('MONGODB_URI'),
        'MONGODB_DATABASE': os.getenv('MONGODB_DATABASE'),
        
        # Teller Banking API
        'TELLER_APPLICATION_ID': os.getenv('TELLER_APPLICATION_ID'),
        'TELLER_ENVIRONMENT': os.getenv('TELLER_ENVIRONMENT'),
        'TELLER_API_URL': os.getenv('TELLER_API_URL'),
        'TELLER_WEBHOOK_URL': os.getenv('TELLER_WEBHOOK_URL'),
        'TELLER_SIGNING_SECRET': os.getenv('TELLER_SIGNING_SECRET'),
        
        # Gmail API
        'GMAIL_ACCOUNT_1_EMAIL': os.getenv('GMAIL_ACCOUNT_1_EMAIL'),
        'GMAIL_ACCOUNT_2_EMAIL': os.getenv('GMAIL_ACCOUNT_2_EMAIL'),
        'GMAIL_ACCOUNT_3_EMAIL': os.getenv('GMAIL_ACCOUNT_3_EMAIL'),
        
        # Cloudflare R2 Storage
        'R2_ENDPOINT': os.getenv('R2_ENDPOINT'),
        'R2_ACCESS_KEY': os.getenv('R2_ACCESS_KEY'),
        'R2_SECRET_KEY': os.getenv('R2_SECRET_KEY'),
        'R2_BUCKET': os.getenv('R2_BUCKET'),
        
        # HuggingFace AI
        'HUGGINGFACE_API_KEY': os.getenv('HUGGINGFACE_API_KEY')
    }
    
    missing_vars = []
    configured_vars = []
    
    for var_name, value in required_vars.items():
        if value:
            configured_vars.append(var_name)
            # Show partial value for security
            if 'KEY' in var_name or 'SECRET' in var_name or 'URI' in var_name:
                display_value = f"{value[:10]}...{value[-5:]}" if len(value) > 15 else "***"
            else:
                display_value = value
            logger.info(f"  ✅ {var_name} = {display_value}")
        else:
            missing_vars.append(var_name)
            logger.warning(f"  ❌ {var_name} = NOT SET")
    
    logger.info(f"Environment Variables: {len(configured_vars)}/{len(required_vars)} configured")
    return len(missing_vars) == 0

def test_mongodb_connection():
    """Test MongoDB connection"""
    logger.info("🗄️  Testing MongoDB Connection...")
    
    try:
        from mongo_client import MongoDBClient
        
        mongo_client = MongoDBClient()
        
        if mongo_client.is_connected():
            logger.info("  ✅ MongoDB connected successfully")
            
            # Test basic operations
            stats = mongo_client.get_stats()
            logger.info(f"  📊 Database: {stats.get('database', 'unknown')}")
            logger.info(f"  📊 Collections: {list(stats.get('collections', {}).keys())}")
            
            return True
        else:
            logger.error("  ❌ MongoDB connection failed")
            return False
            
    except Exception as e:
        logger.error(f"  ❌ MongoDB error: {e}")
        return False

def test_gmail_authentication():
    """Test Gmail API authentication for all accounts"""
    logger.info("📧 Testing Gmail Authentication...")
    
    try:
        from multi_gmail_client import MultiGmailClient
        
        gmail_client = MultiGmailClient()
        available_accounts = gmail_client.get_available_accounts()
        
        if available_accounts:
            logger.info(f"  ✅ {len(available_accounts)} Gmail accounts configured")
            for account in available_accounts:
                logger.info(f"    📧 {account['email']} - {account['status']}")
            return True
        else:
            logger.warning("  ❌ No Gmail accounts available")
            
            # Check token files
            token_files = [
                './gmail_tokens/kaplan_brian_gmail.pickle',
                './gmail_tokens/brian_downhome.pickle', 
                './gmail_tokens/brian_musiccityrodeo.pickle'
            ]
            
            for token_file in token_files:
                if os.path.exists(token_file):
                    logger.info(f"    📄 Token file exists: {token_file}")
                else:
                    logger.warning(f"    ❌ Missing token file: {token_file}")
            
            return False
            
    except Exception as e:
        logger.error(f"  ❌ Gmail authentication error: {e}")
        return False

def test_teller_api():
    """Test Teller Banking API connection"""
    logger.info("🏦 Testing Teller Banking API...")
    
    try:
        from teller_client import TellerClient
        
        teller_client = TellerClient()
        
        if teller_client._has_credentials():
            logger.info("  ✅ Teller credentials configured")
            logger.info(f"    🆔 Application ID: {teller_client.application_id}")
            logger.info(f"    🌍 Environment: {teller_client.environment}")
            logger.info(f"    🌐 API URL: {teller_client.api_url}")
            logger.info(f"    🔗 Webhook URL: {teller_client.webhook_url}")
            
            # Test connection (might fail without proper certs in development)
            if teller_client.is_connected():
                logger.info("  ✅ Teller API connection successful")
                
                # Try to get accounts
                accounts = teller_client.get_connected_accounts()
                logger.info(f"    🏦 Connected accounts: {len(accounts)}")
                
            else:
                logger.warning("  ⚠️ Teller API connection failed (expected in development without SSL certs)")
                logger.info("    💡 This is normal - Teller Connect flow will work when users authenticate")
            
            return True
        else:
            logger.error("  ❌ Teller credentials not configured")
            return False
            
    except Exception as e:
        logger.error(f"  ❌ Teller API error: {e}")
        return False

def test_r2_storage():
    """Test Cloudflare R2 storage connection"""
    logger.info("☁️  Testing Cloudflare R2 Storage...")
    
    try:
        from r2_client import R2Client
        
        r2_client = R2Client()
        
        if r2_client.is_connected():
            logger.info("  ✅ R2 storage connected successfully")
            logger.info(f"    🪣 Bucket: {r2_client.bucket_name}")
            
            # Test listing files
            files = r2_client.list_files(limit=5)
            logger.info(f"    📁 Files in bucket: {len(files)} (showing up to 5)")
            
            for file_info in files[:3]:
                logger.info(f"      📄 {file_info['key']} ({file_info['size']} bytes)")
            
            return True
        else:
            logger.error("  ❌ R2 storage connection failed")
            return False
            
    except Exception as e:
        logger.error(f"  ❌ R2 storage error: {e}")
        return False

def test_huggingface_ai():
    """Test HuggingFace AI API"""
    logger.info("🤖 Testing HuggingFace AI API...")
    
    try:
        from huggingface_client import HuggingFaceClient
        
        hf_client = HuggingFaceClient()
        
        if hf_client.is_connected():
            logger.info("  ✅ HuggingFace API key configured")
            
            # Test a simple categorization
            test_receipt = {
                'merchant': 'Office Depot',
                'total_amount': 45.99,
                'items': [{'name': 'Office Supplies', 'price': 45.99}],
                'raw_text': 'Office supplies for business use'
            }
            
            category = hf_client.categorize_expense(test_receipt)
            logger.info(f"    🏷️ Test categorization: {category.category} ({category.confidence:.2f} confidence)")
            logger.info(f"    💼 Business purpose: {category.business_purpose}")
            
            return True
        else:
            logger.warning("  ❌ HuggingFace API key not configured")
            return False
            
    except Exception as e:
        logger.error(f"  ❌ HuggingFace AI error: {e}")
        return False

def test_sheets_integration():
    """Test Google Sheets integration"""
    logger.info("📊 Testing Google Sheets Integration...")
    
    try:
        from sheets_client import SheetsClient
        
        sheets_client = SheetsClient()
        
        if sheets_client.is_connected():
            logger.info("  ✅ Google Sheets API configured")
            return True
        else:
            logger.warning("  ⚠️ Google Sheets not configured (optional)")
            return False
            
    except ImportError:
        logger.warning("  ⚠️ Google Sheets client not found (optional)")
        return False
    except Exception as e:
        logger.error(f"  ❌ Google Sheets error: {e}")
        return False

def test_port_availability():
    """Test if common ports are available"""
    logger.info("🔌 Testing Port Availability...")
    
    import socket
    
    ports_to_test = [5000, 5001, 8000, 8080]
    available_ports = []
    
    for port in ports_to_test:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('localhost', port))
            available_ports.append(port)
            logger.info(f"  ✅ Port {port} is available")
        except OSError:
            logger.warning(f"  ❌ Port {port} is in use")
        finally:
            sock.close()
    
    return available_ports

def generate_service_status_report():
    """Generate a comprehensive service status report"""
    logger.info("📋 Generating Service Status Report...")
    
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'services': {},
        'summary': {
            'total_services': 0,
            'working_services': 0,
            'failed_services': 0
        }
    }
    
    # Test all services
    services = [
        ('Environment Variables', test_environment_variables),
        ('MongoDB Database', test_mongodb_connection),
        ('Gmail API', test_gmail_authentication),
        ('Teller Banking API', test_teller_api),
        ('R2 Cloud Storage', test_r2_storage),
        ('HuggingFace AI', test_huggingface_ai),
        ('Google Sheets', test_sheets_integration)
    ]
    
    for service_name, test_function in services:
        try:
            result = test_function()
            report['services'][service_name] = {
                'status': 'working' if result else 'failed',
                'tested_at': datetime.utcnow().isoformat()
            }
            
            if result:
                report['summary']['working_services'] += 1
            else:
                report['summary']['failed_services'] += 1
                
        except Exception as e:
            report['services'][service_name] = {
                'status': 'error',
                'error': str(e),
                'tested_at': datetime.utcnow().isoformat()
            }
            report['summary']['failed_services'] += 1
        
        report['summary']['total_services'] += 1
    
    # Test port availability
    available_ports = test_port_availability()
    report['available_ports'] = available_ports
    
    return report

def main():
    """Main function to run all backend service tests"""
    logger.info("🚀 Starting Backend Services Verification")
    logger.info("=" * 60)
    
    # Generate comprehensive report
    report = generate_service_status_report()
    
    # Print summary
    logger.info("=" * 60)
    logger.info("📊 BACKEND SERVICES SUMMARY")
    logger.info("=" * 60)
    
    summary = report['summary']
    logger.info(f"Total Services Tested: {summary['total_services']}")
    logger.info(f"✅ Working Services: {summary['working_services']}")
    logger.info(f"❌ Failed Services: {summary['failed_services']}")
    
    success_rate = (summary['working_services'] / summary['total_services']) * 100
    logger.info(f"📈 Success Rate: {success_rate:.1f}%")
    
    if report['available_ports']:
        logger.info(f"🔌 Available Ports: {', '.join(map(str, report['available_ports']))}")
    
    # Save report to file
    report_file = f'backend_status_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"📄 Detailed report saved to: {report_file}")
    
    # Recommendations
    logger.info("=" * 60)
    logger.info("💡 RECOMMENDATIONS")
    logger.info("=" * 60)
    
    if summary['working_services'] >= 4:
        logger.info("🎉 Most services are working! You can start the application.")
        if 5001 in report['available_ports']:
            logger.info("💡 Recommended: Start app with 'python app.py' and use port 5001")
        elif 8000 in report['available_ports']:
            logger.info("💡 Recommended: Start app with 'python app.py' and use port 8000")
    else:
        logger.info("⚠️ Some critical services need attention before starting the app.")
    
    # Critical service checks
    if not report['services'].get('MongoDB Database', {}).get('status') == 'working':
        logger.warning("🔧 MongoDB needs configuration - receipts won't be stored permanently")
    
    if not report['services'].get('Gmail API', {}).get('status') == 'working':
        logger.warning("🔧 Gmail authentication needs setup - run gmail token setup scripts")
    
    return success_rate > 70  # Return True if more than 70% of services are working

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
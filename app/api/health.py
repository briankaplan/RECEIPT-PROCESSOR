"""
Health check API endpoints
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, current_app
import sys
import os

logger = logging.getLogger(__name__)

bp = Blueprint('health', __name__, url_prefix='/api')

@bp.route('/health')
def health():
    """Basic health check"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@bp.route('/email/health')
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

@bp.route('/banking/health')
def banking_health():
    """Teller API Connection health check"""
    try:
        from ..config import Config
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

@bp.route('/ocr/health')
def ocr_health():
    """OCR & Document Processing health check"""
    try:
        from ..config import Config
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

@bp.route('/storage/health')
def storage_health():
    """Check R2 storage health"""
    try:
        from ..config import Config
        if not all([Config.R2_ACCOUNT_ID, Config.R2_ACCESS_KEY_ID, Config.R2_SECRET_ACCESS_KEY]):
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
            endpoint_url=f"https://{Config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=Config.R2_ACCESS_KEY_ID,
            aws_secret_access_key=Config.R2_SECRET_ACCESS_KEY
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

@bp.route('/sheets/health')
def sheets_health():
    """Check Google Sheets health"""
    try:
        from ..config import Config
        service_account_path = '/Users/briankaplan/Receipt_Matcher/RECEIPT-PROCESSOR/credentials/service_account.json'
        
        if not os.path.exists(service_account_path):
            return jsonify({
                "service": "Google Sheets",
                "status": "not_configured",
                "error": "Service account file not found",
                "timestamp": datetime.now().isoformat()
            })
        
        # Test sheets connection
        try:
            import sys
            sys.path.append('.')
            from sheets_client import SheetsClient
            
            sheets = SheetsClient(service_account_path)
            # Try to list spreadsheets
            spreadsheets = sheets.list_spreadsheets()
            return jsonify({
                "service": "Google Sheets",
                "status": "healthy",
                "spreadsheets": len(spreadsheets) if spreadsheets else 0,
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

@bp.route('/brian/health')
def brian_health():
    """Brian's Financial Wizard health check"""
    try:
        # Check if Brian's Financial Wizard is available
        try:
            from brian_financial_wizard import BrianFinancialWizard
            wizard = BrianFinancialWizard()
            return jsonify({
                "status": "ok",
                "service": "Brian's Financial Wizard",
                "version": "1.0",
                "capabilities": ["Receipt Analysis", "Expense Categorization", "Financial Insights"],
                "timestamp": datetime.utcnow().isoformat()
            }), 200
        except ImportError:
            return jsonify({
                "status": "not_available",
                "service": "Brian's Financial Wizard",
                "message": "Wizard module not available",
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "service": "Brian's Financial Wizard",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@bp.route('/health/detailed')
def health_detailed():
    """Detailed health check with all services"""
    try:
        # Get MongoDB stats
        mongo_stats = current_app.mongo_client.get_stats() if hasattr(current_app, 'mongo_client') else {"connected": False}
        
        # Get R2 stats
        r2_connected = current_app.r2_client.is_connected() if hasattr(current_app, 'r2_client') else False
        
        # Get Teller stats
        from ..config import Config
        teller_configured = bool(Config.TELLER_APPLICATION_ID)
        
        # Get HuggingFace stats
        hf_configured = bool(Config.HUGGINGFACE_API_KEY)
        
        return jsonify({
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "mongodb": mongo_stats,
                "r2_storage": {"connected": r2_connected},
                "teller_api": {"configured": teller_configured, "environment": Config.TELLER_ENVIRONMENT},
                "huggingface": {"configured": hf_configured},
                "google_sheets": {"configured": bool(Config.GOOGLE_SHEETS_CREDENTIALS)}
            },
            "system": {
                "python_version": "3.11.9",
                "flask_version": "2.3.3",
                "environment": Config.FLASK_ENV
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@bp.route('/health/comprehensive')
def comprehensive_health():
    """Comprehensive health check for all core services"""
    try:
        health_status = {
            "status": "checking",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }
        
        # 1. Database (MongoDB)
        try:
            mongo_stats = current_app.mongo_client.get_stats() if hasattr(current_app, 'mongo_client') else {"connected": False}
            health_status["services"]["database"] = {
                "name": "MongoDB",
                "status": "healthy" if mongo_stats.get("connected") else "unhealthy",
                "details": mongo_stats,
                "collections": mongo_stats.get("collections", {})
            }
        except Exception as e:
            health_status["services"]["database"] = {
                "name": "MongoDB", 
                "status": "error",
                "error": str(e)
            }
        
        # 2. Storage (R2)
        try:
            r2_connected = current_app.r2_client.is_connected() if hasattr(current_app, 'r2_client') else False
            health_status["services"]["storage"] = {
                "name": "Cloudflare R2",
                "status": "healthy" if r2_connected else "unhealthy",
                "connected": r2_connected
            }
        except Exception as e:
            health_status["services"]["storage"] = {
                "name": "Cloudflare R2",
                "status": "error", 
                "error": str(e)
            }
        
        # 3. Banks (Teller)
        try:
            from ..config import Config
            teller_configured = bool(Config.TELLER_APPLICATION_ID)
            teller_tokens = current_app.mongo_client.get_teller_tokens() if hasattr(current_app, 'mongo_client') else []
            
            health_status["services"]["banks"] = {
                "name": "Teller Banking",
                "status": "configured" if teller_configured else "not_configured",
                "environment": Config.TELLER_ENVIRONMENT,
                "connected_accounts": len(teller_tokens),
                "tokens": [{"user_id": t.get("user_id"), "institution": t.get("institution")} for t in teller_tokens]
            }
        except Exception as e:
            health_status["services"]["banks"] = {
                "name": "Teller Banking",
                "status": "error",
                "error": str(e)
            }
        
        # 4. AI (HuggingFace)
        try:
            from ..config import Config
            hf_configured = bool(Config.HUGGINGFACE_API_KEY)
            
            if hf_configured:
                # Test HuggingFace connection
                try:
                    from huggingface_client import HuggingFaceClient
                    hf_client = HuggingFaceClient()
                    test_result = hf_client.test_connection()
                    ai_status = "healthy" if test_result else "unhealthy"
                except Exception as e:
                    logger.warning(f"HuggingFace test failed: {e}")
                    ai_status = "configured_but_unreachable"
            else:
                ai_status = "not_configured"
            
            health_status["services"]["ai"] = {
                "name": "HuggingFace AI",
                "status": ai_status,
                "configured": hf_configured
            }
        except Exception as e:
            health_status["services"]["ai"] = {
                "name": "HuggingFace AI",
                "status": "error",
                "error": str(e)
            }
        
        # 5. Email (Gmail)
        try:
            import os
            gmail_tokens_dir = 'gmail_tokens'
            if os.path.exists(gmail_tokens_dir):
                token_files = [f for f in os.listdir(gmail_tokens_dir) if f.endswith('.pickle')]
                email_status = "healthy" if token_files else "not_connected"
                connected_accounts = len(token_files)
            else:
                email_status = "not_configured"
                connected_accounts = 0
            
            health_status["services"]["email"] = {
                "name": "Gmail Integration",
                "status": email_status,
                "connected_accounts": connected_accounts,
                "accounts": [f.replace('.pickle', '') for f in token_files] if 'token_files' in locals() else []
            }
        except Exception as e:
            health_status["services"]["email"] = {
                "name": "Gmail Integration",
                "status": "error",
                "error": str(e)
            }
        
        # 6. Calendar
        try:
            # Test calendar intelligence
            try:
                from calendar_intelligence import CalendarIntelligence
                calendar = CalendarIntelligence()
                calendar_status = "healthy"
            except ImportError:
                calendar_status = "not_available"
            except Exception:
                calendar_status = "error"
            
            health_status["services"]["calendar"] = {
                "name": "Calendar Intelligence",
                "status": calendar_status
            }
        except Exception as e:
            health_status["services"]["calendar"] = {
                "name": "Calendar Intelligence",
                "status": "error",
                "error": str(e)
            }
        
        # 7. Google Sheets
        try:
            from ..config import Config
            sheets_configured = bool(Config.GOOGLE_SHEETS_CREDENTIALS)
            
            if sheets_configured:
                try:
                    import json
                    from google.oauth2.service_account import Credentials
                    from googleapiclient.discovery import build
                    
                    credentials_info = json.loads(Config.GOOGLE_SHEETS_CREDENTIALS)
                    credentials = Credentials.from_service_account_info(
                        credentials_info,
                        scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
                    service = build('sheets', 'v4', credentials=credentials)
                    sheets_status = "healthy"
                except Exception:
                    sheets_status = "configured_but_unreachable"
            else:
                sheets_status = "not_configured"
            
            health_status["services"]["sheets"] = {
                "name": "Google Sheets",
                "status": sheets_status,
                "configured": sheets_configured
            }
        except Exception as e:
            health_status["services"]["sheets"] = {
                "name": "Google Sheets",
                "status": "error",
                "error": str(e)
            }
        
        # Calculate overall status
        healthy_services = sum(1 for service in health_status["services"].values() 
                             if service.get("status") in ["healthy", "configured"])
        total_services = len(health_status["services"])
        
        if healthy_services == total_services:
            overall_status = "healthy"
        elif healthy_services > total_services // 2:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        health_status["status"] = overall_status
        health_status["summary"] = {
            "total_services": total_services,
            "healthy_services": healthy_services,
            "unhealthy_services": total_services - healthy_services
        }
        
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"Comprehensive health check failed: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500 

@bp.route('/security', methods=['GET'])
def security_health():
    """Comprehensive security health check"""
    try:
        security_status = {
            "authentication": {
                "jwt_enabled": bool(current_app.config.get('JWT_SECRET_KEY')),
                "api_key_enabled": bool(current_app.config.get('API_KEY')),
                "session_secure": current_app.config.get('SESSION_COOKIE_SECURE', False),
                "max_login_attempts": current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
            },
            "headers": {
                "csp_enabled": 'Content-Security-Policy' in current_app.config.get('SECURITY_HEADERS', {}),
                "hsts_enabled": 'Strict-Transport-Security' in current_app.config.get('SECURITY_HEADERS', {}),
                "xss_protection": 'X-XSS-Protection' in current_app.config.get('SECURITY_HEADERS', {}),
                "frame_options": 'X-Frame-Options' in current_app.config.get('SECURITY_HEADERS', {})
            },
            "rate_limiting": {
                "enabled": bool(current_app.config.get('RATELIMIT_DEFAULT')),
                "storage": current_app.config.get('RATELIMIT_STORAGE_URL', 'memory://'),
                "headers_enabled": current_app.config.get('RATELIMIT_HEADERS_ENABLED', False)
            },
            "monitoring": {
                "audit_logging": current_app.config.get('AUDIT_LOG_ENABLED', False),
                "security_monitoring": current_app.config.get('SECURITY_MONITORING_ENABLED', False),
                "suspicious_threshold": current_app.config.get('SUSPICIOUS_ACTIVITY_THRESHOLD', 10)
            },
            "file_upload": {
                "max_size_mb": current_app.config.get('MAX_CONTENT_LENGTH', 0) / (1024*1024),
                "allowed_extensions": list(current_app.config.get('ALLOWED_EXTENSIONS', set())),
                "validation_enabled": True
            },
            "cors": {
                "enabled": bool(current_app.config.get('CORS_ORIGINS')),
                "origins": current_app.config.get('CORS_ORIGINS', []),
                "credentials": current_app.config.get('CORS_SUPPORTS_CREDENTIALS', False)
            }
        }
        
        # Check if security middleware is active
        security_middleware_active = hasattr(current_app, 'security_middleware')
        if security_middleware_active:
            security_status["middleware"] = {
                "active": True,
                "audit_logger": hasattr(current_app.security_middleware, 'audit_logger'),
                "security_monitor": hasattr(current_app.security_middleware, 'security_monitor'),
                "failed_attempts_tracking": hasattr(current_app.security_middleware, 'failed_attempts')
            }
        else:
            security_status["middleware"] = {"active": False}
        
        # Check environment security
        environment_security = {
            "debug_mode": current_app.config.get('DEBUG', False),
            "testing_mode": current_app.config.get('TESTING', False),
            "environment": current_app.config.get('ENVIRONMENT', 'development'),
            "secret_key_secure": len(current_app.config.get('SECRET_KEY', '')) >= 32,
            "jwt_secret_secure": len(current_app.config.get('JWT_SECRET_KEY', '')) >= 32
        }
        
        # Calculate overall security score
        security_score = 0
        total_checks = 0
        
        # Authentication checks
        if security_status["authentication"]["jwt_enabled"]: security_score += 1
        if security_status["authentication"]["api_key_enabled"]: security_score += 1
        if security_status["authentication"]["session_secure"]: security_score += 1
        total_checks += 3
        
        # Header checks
        if security_status["headers"]["csp_enabled"]: security_score += 1
        if security_status["headers"]["hsts_enabled"]: security_score += 1
        if security_status["headers"]["xss_protection"]: security_score += 1
        if security_status["headers"]["frame_options"]: security_score += 1
        total_checks += 4
        
        # Rate limiting checks
        if security_status["rate_limiting"]["enabled"]: security_score += 1
        total_checks += 1
        
        # Monitoring checks
        if security_status["monitoring"]["audit_logging"]: security_score += 1
        if security_status["monitoring"]["security_monitoring"]: security_score += 1
        total_checks += 2
        
        # File upload checks
        if security_status["file_upload"]["validation_enabled"]: security_score += 1
        if security_status["file_upload"]["max_size_mb"] <= 16: security_score += 1
        total_checks += 2
        
        # Environment checks
        if not environment_security["debug_mode"]: security_score += 1
        if environment_security["secret_key_secure"]: security_score += 1
        if environment_security["jwt_secret_secure"]: security_score += 1
        total_checks += 3
        
        security_percentage = (security_score / total_checks) * 100 if total_checks > 0 else 0
        
        return jsonify({
            "status": "healthy" if security_percentage >= 80 else "warning" if security_percentage >= 60 else "critical",
            "timestamp": datetime.utcnow().isoformat(),
            "security_score": round(security_percentage, 1),
            "security_status": security_status,
            "environment_security": environment_security,
            "recommendations": get_security_recommendations(security_status, environment_security)
        }), 200
        
    except Exception as e:
        logger.error(f"Security health check error: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

def get_security_recommendations(security_status: dict, environment_security: dict) -> list:
    """Generate security recommendations based on current status"""
    recommendations = []
    
    if environment_security["debug_mode"]:
        recommendations.append("Disable debug mode in production")
    
    if not environment_security["secret_key_secure"]:
        recommendations.append("Use a stronger SECRET_KEY (at least 32 characters)")
    
    if not environment_security["jwt_secret_secure"]:
        recommendations.append("Use a stronger JWT_SECRET_KEY (at least 32 characters)")
    
    if not security_status["headers"]["csp_enabled"]:
        recommendations.append("Enable Content Security Policy headers")
    
    if not security_status["headers"]["hsts_enabled"]:
        recommendations.append("Enable HTTP Strict Transport Security headers")
    
    if not security_status["monitoring"]["audit_logging"]:
        recommendations.append("Enable audit logging for security events")
    
    if not security_status["monitoring"]["security_monitoring"]:
        recommendations.append("Enable security monitoring and alerting")
    
    if not security_status["rate_limiting"]["enabled"]:
        recommendations.append("Enable rate limiting to prevent abuse")
    
    return recommendations 

@bp.route('/calendar/health')
def calendar_health():
    """Check Google Calendar health"""
    try:
        from ..config import Config
        if not all([Config.GOOGLE_CLIENT_ID, Config.GOOGLE_CLIENT_SECRET]):
            return jsonify({
                "service": "Google Calendar",
                "status": "not_configured",
                "timestamp": datetime.now().isoformat()
            })
        
        # Test calendar connection
        try:
            import os
            sys.path.append('.')
            from calendar_intelligence import CalendarIntelligence
            
            calendar = CalendarIntelligence()
            # Try to get primary calendar
            calendars = calendar.list_calendars()
            if calendars:
                return jsonify({
                    "service": "Google Calendar",
                    "status": "healthy",
                    "calendars": len(calendars),
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return jsonify({
                    "service": "Google Calendar",
                    "status": "no_calendars",
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            return jsonify({
                "service": "Google Calendar",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        return jsonify({
            "service": "Google Calendar",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }) 
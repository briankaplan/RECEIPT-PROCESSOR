"""
Security utilities and middleware for the Receipt Processor application
"""

import logging
import re
import secrets
import time
import hashlib
import hmac
from functools import wraps
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from flask import request, jsonify, current_app, g, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import jwt
from werkzeug.security import check_password_hash, generate_password_hash
from bson import ObjectId

logger = logging.getLogger(__name__)

class SecurityAuditLogger:
    """Audit logging for security events"""
    
    def __init__(self):
        self.audit_logger = logging.getLogger('security_audit')
        self.audit_logger.setLevel(logging.INFO)
        
        # Create file handler for audit logs
        import os
        os.makedirs('logs', exist_ok=True)
        audit_handler = logging.FileHandler('logs/security_audit.log')
        audit_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.audit_logger.addHandler(audit_handler)
    
    def log_auth_attempt(self, username: str, success: bool, ip: str, user_agent: str):
        """Log authentication attempts"""
        status = "SUCCESS" if success else "FAILED"
        self.audit_logger.warning(
            f"AUTH_ATTEMPT - User: {username} - Status: {status} - IP: {ip} - UA: {user_agent[:100]}"
        )
    
    def log_api_access(self, endpoint: str, method: str, user_id: str, ip: str, status_code: int):
        """Log API access"""
        self.audit_logger.info(
            f"API_ACCESS - Endpoint: {method} {endpoint} - User: {user_id} - IP: {ip} - Status: {status_code}"
        )
    
    def log_security_event(self, event_type: str, details: str, severity: str = "INFO"):
        """Log security events"""
        getattr(self.audit_logger, severity.lower())(
            f"SECURITY_EVENT - Type: {event_type} - Details: {details}"
        )

class SecurityMonitor:
    """Security monitoring and alerting system"""
    
    def __init__(self):
        self.event_counts = defaultdict(int)
        self.alert_thresholds = {
            'failed_logins': 10,
            'suspicious_requests': 5,
            'api_violations': 3,
            'file_uploads': 20
        }
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5 minutes between alerts
    
    def record_event(self, event_type: str, details: str = ""):
        """Record a security event"""
        now = datetime.utcnow()
        key = f"{event_type}_{now.strftime('%Y-%m-%d-%H')}"
        self.event_counts[key] += 1
        
        # Check if we should send an alert
        if self.should_alert(event_type, key):
            self.send_alert(event_type, details, self.event_counts[key])
    
    def should_alert(self, event_type: str, key: str) -> bool:
        """Check if we should send an alert"""
        threshold = self.alert_thresholds.get(event_type, 5)
        count = self.event_counts[key]
        
        # Check cooldown
        last_alert = self.last_alert_time.get(event_type)
        if last_alert and (datetime.utcnow() - last_alert).seconds < self.alert_cooldown:
            return False
        
        return count >= threshold
    
    def send_alert(self, event_type: str, details: str, count: int):
        """Send security alert"""
        now = datetime.utcnow()
        self.last_alert_time[event_type] = now
        
        alert_message = f"SECURITY_ALERT - Type: {event_type} - Count: {count} - Details: {details}"
        logger.warning(alert_message)
        
        # In production, you might want to send this to a monitoring service
        # like Sentry, PagerDuty, or email
        
        # For now, we'll just log it
        security_logger = logging.getLogger('security_alerts')
        security_logger.warning(alert_message)

class SecurityMiddleware:
    """Security middleware for request processing"""
    
    def __init__(self, app):
        self.app = app
        self.audit_logger = SecurityAuditLogger()
        self.security_monitor = SecurityMonitor()
        self.failed_attempts = defaultdict(list)  # Track failed login attempts
        self.setup_limiter(app)
        self.setup_security_headers(app)
        self.setup_request_validation(app)
    
    def setup_limiter(self, app):
        """Setup rate limiting"""
        self.limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=[app.config['RATELIMIT_DEFAULT']],
            storage_uri=app.config['RATELIMIT_STORAGE_URL'],
            headers_enabled=app.config['RATELIMIT_HEADERS_ENABLED']
        )
    
    def setup_security_headers(self, app):
        """Setup security headers"""
        @app.after_request
        def add_security_headers(response):
            headers = app.config['SECURITY_HEADERS']
            for header, value in headers.items():
                response.headers[header] = value
            
            # Add request ID for tracking
            if not response.headers.get('X-Request-ID'):
                response.headers['X-Request-ID'] = self.generate_request_id()
            
            return response
    
    def setup_request_validation(self, app):
        """Setup request validation middleware"""
        @app.before_request
        def validate_request():
            # Check for suspicious patterns
            if self.detect_suspicious_request(request):
                self.audit_logger.log_security_event(
                    "SUSPICIOUS_REQUEST", 
                    f"IP: {request.remote_addr} - Path: {request.path}",
                    "WARNING"
                )
                self.security_monitor.record_event('suspicious_requests', f"IP: {request.remote_addr}")
                return jsonify({'error': 'Request blocked'}), 403
            
            # Validate content length
            if request.content_length and request.content_length > app.config['MAX_CONTENT_LENGTH']:
                return jsonify({'error': 'Request too large'}), 413
    
    def detect_suspicious_request(self, request) -> bool:
        """Detect suspicious request patterns"""
        suspicious_patterns = [
            r'\.\./',  # Path traversal
            r'<script',  # XSS attempts
            r'javascript:',  # JavaScript injection
            r'union\s+select',  # SQL injection
            r'exec\s*\(',  # Command injection
            r'eval\s*\(',  # Code injection
        ]
        
        # Check URL path
        for pattern in suspicious_patterns:
            if re.search(pattern, request.path, re.IGNORECASE):
                return True
        
        # Check query parameters
        for key, value in request.args.items():
            for pattern in suspicious_patterns:
                if re.search(pattern, str(value), re.IGNORECASE):
                    return True
        
        # Check headers
        user_agent = request.headers.get('User-Agent', '')
        if not user_agent or len(user_agent) > 500:
            return True
        
        return False
    
    def generate_request_id(self) -> str:
        """Generate unique request ID"""
        return hashlib.sha256(f"{time.time()}{secrets.token_hex(8)}".encode()).hexdigest()[:16]
    
    def check_failed_attempts(self, username: str, ip: str) -> bool:
        """Check if user/IP is blocked due to failed attempts"""
        now = datetime.utcnow()
        key = f"{username}:{ip}"
        
        # Clean old attempts
        self.failed_attempts[key] = [
            attempt for attempt in self.failed_attempts[key]
            if now - attempt < timedelta(minutes=15)
        ]
        
        # Check if too many recent attempts
        if len(self.failed_attempts[key]) >= 5:
            return True
        
        return False
    
    def record_failed_attempt(self, username: str, ip: str):
        """Record a failed authentication attempt"""
        key = f"{username}:{ip}"
        self.failed_attempts[key].append(datetime.utcnow())
        self.security_monitor.record_event('failed_logins', f"User: {username} - IP: {ip}")
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key"""
        return api_key == current_app.config['API_KEY']
    
    def validate_jwt_token(self, token: str) -> Optional[Dict]:
        """Validate JWT token"""
        try:
            payload = jwt.decode(
                token, 
                current_app.config['JWT_SECRET_KEY'], 
                algorithms=['HS256']
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None
    
    def sanitize_input(self, data: Any) -> Any:
        """Sanitize input data"""
        if isinstance(data, str):
            # Remove potentially dangerous characters
            data = re.sub(r'[<>"\']', '', data)
            # Limit length
            if len(data) > 1000:
                data = data[:1000]
        elif isinstance(data, dict):
            return {k: self.sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_input(item) for item in data]
        return data
    
    def validate_file_upload(self, filename: str, content_type: str) -> bool:
        """Validate file upload"""
        if not filename:
            return False
        
        # Check file extension
        allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if file_ext not in allowed_extensions:
            return False
        
        # Check content type
        allowed_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'pdf': 'application/pdf',
            'tiff': 'image/tiff',
            'bmp': 'image/bmp'
        }
        
        expected_type = allowed_types.get(file_ext)
        if expected_type and content_type != expected_type:
            return False
        
        return True
    
    def validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token"""
        if not token:
            return False
        
        # In a real implementation, you'd validate against session token
        # For now, we'll do basic format validation
        return len(token) >= 32 and token.isalnum()

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get(current_app.config['API_KEY_HEADER'])
        if not api_key:
            current_app.security_middleware.audit_logger.log_security_event(
                "API_KEY_MISSING", f"IP: {request.remote_addr} - Endpoint: {request.endpoint}"
            )
            return jsonify({'error': 'API key required'}), 401
        
        if not current_app.security_middleware.validate_api_key(api_key):
            current_app.security_middleware.audit_logger.log_security_event(
                "API_KEY_INVALID", f"IP: {request.remote_addr} - Endpoint: {request.endpoint}"
            )
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def require_jwt_auth(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            current_app.security_middleware.audit_logger.log_security_event(
                "JWT_MISSING", f"IP: {request.remote_addr} - Endpoint: {request.endpoint}"
            )
            return jsonify({'error': 'Bearer token required'}), 401
        
        token = auth_header.split(' ')[1]
        payload = current_app.security_middleware.validate_jwt_token(token)
        
        if not payload:
            current_app.security_middleware.audit_logger.log_security_event(
                "JWT_INVALID", f"IP: {request.remote_addr} - Endpoint: {request.endpoint}"
            )
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        g.user_id = payload.get('user_id')
        g.user_role = payload.get('role', 'user')
        
        # Log API access
        current_app.security_middleware.audit_logger.log_api_access(
            request.endpoint, request.method, g.user_id, request.remote_addr, 200
        )
        
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_role') or g.user_role != 'admin':
            current_app.security_middleware.audit_logger.log_security_event(
                "ADMIN_ACCESS_DENIED", f"User: {getattr(g, 'user_id', 'unknown')} - IP: {request.remote_addr}"
            )
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def sanitize_request_data(f):
    """Decorator to sanitize request data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Sanitize JSON data
        if request.is_json:
            request.json = current_app.security_middleware.sanitize_input(request.json)
        
        # Sanitize form data
        if request.form:
            for key, value in request.form.items():
                request.form[key] = current_app.security_middleware.sanitize_input(value)
        
        # Sanitize query parameters
        if request.args:
            for key, value in request.args.items():
                request.args[key] = current_app.security_middleware.sanitize_input(value)
        
        return f(*args, **kwargs)
    return decorated_function

def validate_file_upload(f):
    """Decorator to validate file uploads"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not current_app.security_middleware.validate_file_upload(
            file.filename, file.content_type
        ):
            current_app.security_middleware.audit_logger.log_security_event(
                "INVALID_FILE_UPLOAD", f"File: {file.filename} - IP: {request.remote_addr}"
            )
            return jsonify({'error': 'Invalid file type'}), 400
        
        return f(*args, **kwargs)
    return decorated_function

def require_csrf(f):
    """Decorator to require CSRF token validation"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return f(*args, **kwargs)
        
        csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        if not current_app.security_middleware.validate_csrf_token(csrf_token):
            current_app.security_middleware.audit_logger.log_security_event(
                "CSRF_VIOLATION", f"IP: {request.remote_addr} - Endpoint: {request.endpoint}"
            )
            return jsonify({'error': 'CSRF token required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

class AuthenticationService:
    """Authentication service for user management"""
    
    def __init__(self, mongo_service):
        self.mongo_service = mongo_service
    
    def create_user(self, username: str, password: str, email: str, role: str = 'user') -> bool:
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user = self.mongo_service.client.db.users.find_one({'username': username})
            print(f"DEBUG: existing_user for username '{username}':", existing_user)
            if existing_user:
                return False
            
            # Create user document
            user_doc = {
                'username': username,
                'email': email,
                'password_hash': generate_password_hash(password),
                'role': role,
                'created_at': datetime.utcnow(),
                'last_login': None,
                'is_active': True
            }
            
            result = self.mongo_service.client.db.users.insert_one(user_doc)
            return bool(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data"""
        try:
            user = self.mongo_service.client.db.users.find_one({'username': username, 'is_active': True})
            if not user:
                return None
            
            if check_password_hash(user['password_hash'], password):
                # Update last login
                self.mongo_service.client.db.users.update_one(
                    {'_id': user['_id']},
                    {'$set': {'last_login': datetime.utcnow()}}
                )
                
                return {
                    'user_id': str(user['_id']),
                    'username': user['username'],
                    'email': user['email'],
                    'role': user['role']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None
    
    def generate_tokens(self, user_data: Dict) -> Dict:
        """Generate JWT access and refresh tokens"""
        access_token = jwt.encode(
            {
                'user_id': user_data['user_id'],
                'username': user_data['username'],
                'role': user_data['role'],
                'exp': datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
            },
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        
        refresh_token = jwt.encode(
            {
                'user_id': user_data['user_id'],
                'exp': datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
            },
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
        }

def setup_security(app):
    """Setup security middleware and services"""
    app.security_middleware = SecurityMiddleware(app)
    
    # Add security decorators to app
    app.require_api_key = require_api_key
    app.require_jwt_auth = require_jwt_auth
    app.require_admin = require_admin
    app.sanitize_request_data = sanitize_request_data
    app.validate_file_upload = validate_file_upload
    app.require_csrf = require_csrf
    
    logger.info("🔒 Security middleware initialized") 
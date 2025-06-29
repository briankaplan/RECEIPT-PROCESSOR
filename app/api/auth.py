"""
Authentication API endpoints
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, g
from flask_limiter.util import get_remote_address
from bson import ObjectId

from ..utils.security import AuthenticationService
from ..utils.validators import validate_email, validate_password

logger = logging.getLogger(__name__)

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    return jsonify({'error': 'Registration is closed'}), 403

@bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return tokens"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Check for failed attempts
        if current_app.security_middleware.check_failed_attempts(username, request.remote_addr):
            current_app.security_middleware.audit_logger.log_security_event(
                "ACCOUNT_LOCKED", f"User: {username} - IP: {request.remote_addr}"
            )
            return jsonify({'error': 'Account temporarily locked due to too many failed attempts'}), 429
        
        # Create authentication service
        auth_service = AuthenticationService(current_app.mongo_service)
        
        # Authenticate user
        user_data = auth_service.authenticate_user(username, password)
        
        if not user_data:
            # Record failed attempt
            current_app.security_middleware.record_failed_attempt(username, request.remote_addr)
            current_app.security_middleware.audit_logger.log_auth_attempt(
                username, False, request.remote_addr, request.headers.get('User-Agent', '')
            )
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate tokens
        tokens = auth_service.generate_tokens(user_data)
        
        # Log successful login
        current_app.security_middleware.audit_logger.log_auth_attempt(
            username, True, request.remote_addr, request.headers.get('User-Agent', '')
        )
        
        logger.info(f"User logged in: {username}")
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'user_id': user_data['user_id'],
                'username': user_data['username'],
                'email': user_data['email'],
                'role': user_data['role']
            },
            'tokens': tokens
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        current_app.security_middleware.audit_logger.log_security_event(
            "LOGIN_ERROR", f"Error: {str(e)} - IP: {request.remote_addr}"
        )
        return jsonify({'error': 'Authentication failed'}), 500

@bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        refresh_token = data.get('refresh_token')
        if not refresh_token:
            return jsonify({'error': 'Refresh token is required'}), 400
        
        # Validate refresh token
        try:
            payload = current_app.security_middleware.validate_jwt_token(refresh_token)
            if not payload:
                return jsonify({'error': 'Invalid refresh token'}), 401
            
            user_id = payload.get('user_id')
            
            # Get user data
            user = current_app.mongo_service.client.db.users.find_one({'_id': ObjectId(user_id), 'is_active': True})
            if not user:
                return jsonify({'error': 'User not found'}), 401
            
            user_data = {
                'user_id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'role': user['role']
            }
            
            # Generate new tokens
            auth_service = AuthenticationService(current_app.mongo_service)
            tokens = auth_service.generate_tokens(user_data)
            
            return jsonify({
                'message': 'Token refreshed successfully',
                'tokens': tokens
            }), 200
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return jsonify({'error': 'Invalid refresh token'}), 401
            
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/logout', methods=['POST'])
def logout():
    """Logout user (client should discard tokens)"""
    try:
        # Get user_id from request context or token
        user_id = getattr(g, 'user_id', None)
        if user_id:
            logger.info(f"User logged out: {user_id}")
        else:
            logger.info("Anonymous user logout attempt")
        
        return jsonify({'message': 'Logout successful'}), 200
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/profile', methods=['GET'])
def get_profile():
    """Get current user profile"""
    try:
        # Get user_id from request context
        user_id = getattr(g, 'user_id', None)
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        user = current_app.mongo_service.client.db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        profile = {
            'user_id': str(user['_id']),
            'username': user['username'],
            'email': user['email'],
            'role': user['role'],
            'created_at': user.get('created_at', datetime.utcnow()).isoformat(),
            'last_login': user.get('last_login', datetime.utcnow()).isoformat() if user.get('last_login') else None
        }
        
        return jsonify(profile), 200
        
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/profile', methods=['PUT'])
def update_profile():
    """Update current user profile"""
    try:
        # Get user_id from request context
        user_id = getattr(g, 'user_id', None)
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update user profile
        update_data = {}
        if 'email' in data:
            if not validate_email(data['email']):
                return jsonify({'error': 'Invalid email format'}), 400
            update_data['email'] = data['email']
        
        if update_data:
            current_app.mongo_service.client.db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            
            return jsonify({'message': 'Profile updated successfully'}), 200
        else:
            return jsonify({'error': 'No valid fields to update'}), 400
            
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/health', methods=['GET'])
def auth_health():
    """Health check for auth service"""
    return jsonify({
        'status': 'healthy',
        'service': 'auth',
        'timestamp': datetime.utcnow().isoformat()
    }), 200 
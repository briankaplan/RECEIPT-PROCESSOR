"""
Main dashboard routes (root level)
"""

from flask import Blueprint, render_template, redirect, url_for, request, jsonify, current_app
from functools import wraps
import jwt
import os
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

def require_auth(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth check in development mode for easier testing
        if current_app.config.get('FLASK_ENV') == 'development' and request.args.get('skip_auth'):
            return f(*args, **kwargs)
        
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return redirect('/login')
        
        token = auth_header.split(' ')[1]
        try:
            # Verify token
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = payload['user_id']
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return redirect('/login')
    
    return decorated_function

@bp.route('/')
def index():
    """Main dashboard - check for authentication"""
    # For now, allow access without auth for development
    # In production, you'd want to check for valid JWT token
    return render_template('index.html')

@bp.route('/login')
def login():
    """Login page"""
    return render_template('login.html')

@bp.route('/logout')
def logout():
    """Logout - redirect to login"""
    return redirect('/login')

@bp.route('/transactions')
def transactions():
    """Forward transactions requests to the API endpoint"""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Build query
        query = {}
        if date_from and date_to:
            try:
                from datetime import datetime
                query['date'] = {
                    '$gte': datetime.fromisoformat(date_from),
                    '$lte': datetime.fromisoformat(date_to)
                }
            except ValueError:
                pass
        
        # Get total count
        total = current_app.mongo_service.client.db.transactions.count_documents(query)
        
        # Get paginated results
        skip = (page - 1) * page_size
        transactions = list(current_app.mongo_service.client.db.transactions.find(query).skip(skip).limit(page_size))
        
        # Convert ObjectId to string
        for transaction in transactions:
            transaction['_id'] = str(transaction['_id'])
            if 'date' in transaction:
                transaction['date'] = transaction['date'].isoformat()
        
        return jsonify({
            'transactions': transactions,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'pages': (total + page_size - 1) // page_size
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get transactions error: {e}")
        return jsonify({'error': 'Failed to get transactions'}), 500 
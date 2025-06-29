"""
Transactions API endpoints
"""

from flask import Blueprint, request, jsonify, current_app
from bson.objectid import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('transactions', __name__, url_prefix='/api/transactions')

# TODO: Implement transaction endpoints
# - GET /api/transactions - Get all transactions
# - GET /api/transactions/<id> - Get specific transaction
# - POST /api/transactions/sync - Sync bank transactions
# - PUT /api/transactions/<id> - Update transaction

@bp.route('/')
def get_transactions():
    """Get transactions with pagination and filtering"""
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
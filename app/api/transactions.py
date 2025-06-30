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
        category = request.args.get('category')
        search = request.args.get('search')
        
        # Use transaction service
        result = current_app.transaction_service.get_transactions(
            page=page,
            page_size=page_size,
            date_from=date_from,
            date_to=date_to,
            category=category,
            search=search
        )
        
        # In the list transactions endpoint (not just get_transaction)
        # After fetching transactions from the database:
        for tx in result['transactions']:
            if '_id' in tx:
                tx['_id'] = str(tx['_id'])
            for date_field in ['transaction_date', 'date', 'created_at', 'updated_at', 'bank_synced_at']:
                if date_field in tx and tx[date_field]:
                    if isinstance(tx[date_field], datetime):
                        tx[date_field] = tx[date_field].isoformat()
            if 'raw_bank_data' in tx and tx['raw_bank_data']:
                raw_data = tx['raw_bank_data']
                if isinstance(raw_data, dict):
                    for key, value in raw_data.items():
                        if isinstance(value, datetime):
                            raw_data[key] = value.isoformat()
                        if key == '_id' and hasattr(value, '__str__'):
                            raw_data[key] = str(value)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Get transactions error: {e}")
        return jsonify({'error': 'Failed to get transactions'}), 500

@bp.route('/<transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """Get a specific transaction"""
    try:
        transaction = current_app.mongo_service.client.db.transactions.find_one({'_id': ObjectId(transaction_id)})
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        if '_id' in transaction:
            transaction['_id'] = str(transaction['_id'])
        if transaction.get('receipt_id'):
            transaction['receipt_id'] = str(transaction['receipt_id'])
        if 'date' in transaction:
            if isinstance(transaction['date'], datetime):
                transaction['date'] = transaction['date'].isoformat()
        
        return jsonify(transaction), 200
        
    except Exception as e:
        logger.error(f"Get transaction error: {e}")
        return jsonify({'error': 'Failed to get transaction'}), 500

@bp.route('/<transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """Update a transaction"""
    try:
        updates = request.get_json()
        if not updates:
            return jsonify({'error': 'No update data provided'}), 400
        
        result = current_app.transaction_service.update_transaction(transaction_id, updates)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Update transaction error: {e}")
        return jsonify({'error': 'Failed to update transaction'}), 500

@bp.route('/<transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    """Delete a transaction"""
    try:
        result = current_app.transaction_service.delete_transaction(transaction_id)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Delete transaction error: {e}")
        return jsonify({'error': 'Failed to delete transaction'}), 500

@bp.route('/categories')
def get_categories():
    """Get unique categories from transactions"""
    try:
        categories = current_app.transaction_service.get_categories()
        return jsonify({'categories': categories}), 200
        
    except Exception as e:
        logger.error(f"Get categories error: {e}")
        return jsonify({'error': 'Failed to get categories'}), 500

@bp.route('/sync', methods=['POST'])
def sync_transactions():
    """Sync transactions from bank_transactions"""
    try:
        result = current_app.transaction_service.sync_from_bank_transactions()
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Sync transactions error: {e}")
        return jsonify({'error': 'Failed to sync transactions'}), 500 
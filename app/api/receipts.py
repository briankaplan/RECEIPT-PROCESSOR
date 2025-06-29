"""
Receipts API endpoints
"""

from flask import Blueprint

bp = Blueprint('receipts', __name__, url_prefix='/api/receipts')

# TODO: Implement receipt endpoints
# - GET /api/receipts - List receipts
# - POST /api/receipts - Upload receipt
# - GET /api/receipts/<id> - Get specific receipt
# - PUT /api/receipts/<id> - Update receipt
# - DELETE /api/receipts/<id> - Delete receipt 
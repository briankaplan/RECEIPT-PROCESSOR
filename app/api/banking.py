"""
Banking API endpoints
"""

from flask import Blueprint

bp = Blueprint('banking', __name__, url_prefix='/api/banking')

# TODO: Implement banking endpoints
# - POST /api/banking/connect - Connect bank account
# - GET /api/banking/accounts - List connected accounts
# - POST /api/banking/sync - Sync transactions
# - DELETE /api/banking/disconnect - Disconnect bank account 
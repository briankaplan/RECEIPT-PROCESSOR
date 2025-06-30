"""
Banking API endpoints
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import logging
import requests
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

bp = Blueprint('banking', __name__, url_prefix='/api/banking')

@bp.route('/sync', methods=['POST'])
def sync_transactions():
    """Sync bank transactions from Teller and update the database only"""
    try:
        # Get date range from request or default to last 30 days
        request_data = request.json or {}
        
        # Support custom date ranges
        if 'date_from' in request_data and 'date_to' in request_data:
            start_date = request_data['date_from']
            end_date = request_data['date_to']
        elif 'force_full_sync' in request_data and request_data['force_full_sync']:
            # Force full sync from July 1, 2024 to today
            start_date = "2024-07-01"
            end_date = datetime.now().strftime("%Y-%m-%d")
        else:
            # Default to last 30 days
            days_back = request_data.get('days_back', 30)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            start_date = start_date.strftime("%Y-%m-%d")
            end_date = end_date.strftime("%Y-%m-%d")

        logger.info(f"Syncing transactions from {start_date} to {end_date}")

        # Use BankService to sync transactions (handles Teller and DB)
        result = current_app.bank_service.sync_transactions(
            start_date=start_date,
            end_date=end_date
        )
        
        if result.get('success'):
            # After successful bank sync, trigger transaction sync
            sync_result = current_app.transaction_service.sync_from_bank_transactions()
            if sync_result.get('success'):
                result['transactions_synced'] = sync_result.get('synced', 0)
                result['transactions_updated'] = sync_result.get('updated', 0)
            
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error syncing transactions: {e}")
        return jsonify({'error': f'Failed to sync transactions: {str(e)}'}), 500

@bp.route('/accounts', methods=['GET'])
def get_accounts():
    """Get connected bank accounts"""
    try:
        # Get all Teller tokens
        tokens = list(current_app.mongo_service.client.db.teller_tokens.find({}))
        
        accounts = []
        for token in tokens:
            accounts.append({
                'id': str(token['_id']),
                'account_name': token.get('account_name', 'Unknown Account'),
                'active': token.get('active', False),
                'created_at': token.get('created_at', token.get('_id').generation_time).isoformat() if token.get('created_at') or token.get('_id') else None
            })
        
        return jsonify({'accounts': accounts}), 200
        
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        return jsonify({'error': f'Failed to get accounts: {str(e)}'}), 500

@bp.route('/connect', methods=['POST'])
def connect_account():
    """Connect a new bank account via Teller"""
    try:
        from urllib.parse import urlencode
        
        # Get user ID from request or use default
        user_id = request.json.get('user_id', 'default_user') if request.json else 'default_user'
        
        # Use ngrok URL for local development
        redirect_uri = 'https://9295-69-130-149-204.ngrok-free.app/api/banking/callback'
        
        # Generate Teller Connect URL
        params = {
            'application_id': current_app.config.get('TELLER_APPLICATION_ID'),
            'redirect_uri': redirect_uri,
            'state': user_id,
            'scope': 'transactions:read accounts:read identity:read'
        }
        
        connect_url = f"https://connect.teller.io/connect?{urlencode(params)}"
        
        logger.info(f"Generated Teller Connect URL for user {user_id}")
        
        return jsonify({
            'connect_url': connect_url,
            'message': 'Teller Connect URL generated successfully',
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating Teller Connect URL: {str(e)}")
        return jsonify({'error': 'Failed to generate connect URL'}), 500

@bp.route('/disconnect/<account_id>', methods=['DELETE'])
def disconnect_account(account_id):
    """Disconnect a bank account"""
    try:
        from bson.objectid import ObjectId
        
        # Deactivate the token
        result = current_app.mongo_service.client.db.teller_tokens.update_one(
            {'_id': ObjectId(account_id)},
            {'$set': {'status': 'inactive'}}
        )
        
        if result.modified_count > 0:
            return jsonify({'message': 'Account disconnected successfully'}), 200
        else:
            return jsonify({'error': 'Account not found'}), 404
            
    except Exception as e:
        logger.error(f"Error disconnecting account: {e}")
        return jsonify({'error': f'Failed to disconnect account: {str(e)}'}), 500

@bp.route('/webhook', methods=['POST'])
def teller_webhook():
    """Handle Teller webhooks and store in the correct database"""
    try:
        from flask import request
        import hmac
        import hashlib
        from datetime import datetime
        
        signature = request.headers.get('Teller-Signature', '')
        payload = request.get_data()
        
        # Verify signature if signing secret is configured
        if current_app.config.get('TELLER_SIGNING_SECRET'):
            expected = hmac.new(
                current_app.config['TELLER_SIGNING_SECRET'].encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected):
                logger.warning("Invalid webhook signature")
                return jsonify({"error": "Invalid signature"}), 401
        
        data = request.get_json() or {}
        webhook_type = data.get('type', 'unknown')
        
        logger.info(f"✅ Received Teller webhook: {webhook_type}")
        
        # Store webhook in the correct database
        if current_app.mongo_service and current_app.mongo_service.client.connected:
            webhook_record = {
                "type": webhook_type,
                "data": data,
                "received_at": datetime.utcnow(),
                "signature": signature
            }
            current_app.mongo_service.client.db.teller_webhooks.insert_one(webhook_record)
            
            # If this is a transaction webhook, also store in bank_transactions
            if webhook_type.startswith('transaction.'):
                transaction_data = data.get('data', {})
                if transaction_data.get('id') and transaction_data.get('amount'):
                    # Map Teller transaction to our bank_transactions format
                    bank_transaction = {
                        "transaction_id": transaction_data.get('id'),
                        "account_id": transaction_data.get('account_id'),
                        "amount": transaction_data.get('amount'),
                        "date": transaction_data.get('date'),
                        "description": transaction_data.get('description'),
                        "merchant": transaction_data.get('merchant', {}).get('name') if transaction_data.get('merchant') else None,
                        "category": transaction_data.get('details', {}).get('category'),
                        "type": transaction_data.get('type'),
                        "status": transaction_data.get('status'),
                        "currency": transaction_data.get('currency', 'USD'),
                        "webhook_received_at": datetime.utcnow(),
                        "source": "teller_webhook"
                    }
                    
                    # Insert or update bank_transactions
                    current_app.mongo_service.client.db.bank_transactions.update_one(
                        {"transaction_id": bank_transaction["transaction_id"]},
                        {"$set": bank_transaction},
                        upsert=True
                    )
                    
                    logger.info(f"✅ Stored transaction {bank_transaction['transaction_id']} from webhook")
        
        return jsonify({"success": True, "type": webhook_type}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": "Webhook processing failed"}), 500

@bp.route('/callback')
def teller_callback():
    """Handle Teller OAuth callback"""
    try:
        from flask import request, redirect
        import requests
        from datetime import datetime
        
        # Get query parameters
        state = request.args.get('state', 'default_user')
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            logger.warning(f"Teller callback error: {error}")
            return redirect(f"/?error={error}")
        
        if code:
            logger.info(f"✅ Teller callback success for state: {state}")
            
            # Exchange code for access token
            try:
                token_response = requests.post(
                    'https://api.teller.io/auth/token',
                    headers={
                        'Authorization': f'Basic {current_app.config.get("TELLER_SECRET_KEY", "")}',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    data={
                        'grant_type': 'authorization_code',
                        'code': code,
                        'redirect_uri': current_app.config.get('TELLER_WEBHOOK_URL', '').replace('/webhook', '/callback')
                    },
                    timeout=10
                )
                
                if token_response.status_code == 200:
                    token_data = token_response.json()
                    access_token = token_data.get('access_token')
                    
                    if access_token:
                        # Store the new token in database
                        token_record = {
                            'access_token': access_token,
                            'user_id': state,
                            'status': 'active',
                            'created_at': datetime.utcnow(),
                            'token_type': 'real',
                            'expires_in': token_data.get('expires_in'),
                            'scope': token_data.get('scope')
                        }
                        
                        # Insert new token
                        result = current_app.mongo_service.client.db.teller_tokens.insert_one(token_record)
                        
                        if result.inserted_id:
                            logger.info(f"✅ Stored new Teller token: {result.inserted_id}")
                            
                            # Deactivate old test tokens
                            current_app.mongo_service.client.db.teller_tokens.update_many(
                                {'token_type': 'test'},
                                {'$set': {'status': 'inactive'}}
                            )
                            
                            return redirect("/?success=bank_connected")
                        else:
                            logger.error("Failed to store Teller token")
                            return redirect("/?error=token_storage_failed")
                    else:
                        logger.error("No access token in response")
                        return redirect("/?error=no_access_token")
                else:
                    logger.error(f"Token exchange failed: {token_response.status_code} - {token_response.text}")
                    return redirect("/?error=token_exchange_failed")
                    
            except Exception as e:
                logger.error(f"Token exchange error: {e}")
                return redirect("/?error=token_exchange_error")
        
        return redirect("/")
        
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return redirect(f"/?error=callback_failed") 
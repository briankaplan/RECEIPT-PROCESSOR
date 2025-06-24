# COMPREHENSIVE FIXES FOR RECEIPT PROCESSOR ISSUES
# 1. Bank sync taking 2 seconds - Fix account retrieval
# 2. Receipt processing 'errors' KeyError - Already fixed in main code  
# 3. Camera scanner blur - Fixed in template
# 4. Google Sheets creation failure

import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def fix_bank_sync_in_app_py():
    """
    FIX 1: Bank Sync Issue - Need to get ALL accounts for each token, not specific account_id
    
    The issue is in the bank sync logic. Teller tokens don't store account_id, 
    they store user_id. We need to:
    1. Get all accounts for the token first 
    2. Then get transactions for each discovered account
    """
    
    # This should replace the bank sync logic in app.py lines 1270-1410
    bank_sync_fix = '''
    # Fixed bank sync - get ALL accounts for each token
    for account in connected_accounts:
        try:
            access_token = account.get('access_token')
            user_id = account.get('user_id', 'unknown')
            
            if not access_token:
                sync_results.append({
                    'user_id': user_id,
                    'status': 'error',
                    'error': 'Missing access token'
                })
                continue
            
            logger.info(f"🏦 Syncing for Teller user: {user_id}")
            
            # Real Teller API call
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # FIRST: Get ALL accounts for this token
            accounts_response = requests.get(
                f"{Config.TELLER_API_URL}/accounts",  # Get ALL accounts
                headers=headers,
                timeout=30
            )
            
            if accounts_response.status_code == 200:
                user_accounts = accounts_response.json()
                logger.info(f"✅ Found {len(user_accounts)} accounts for user {user_id}")
                
                # Process each account
                for account_info in user_accounts:
                    account_id = account_info.get('id')
                    
                    # Get transactions for THIS specific account
                    from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')
                    
                    transactions_response = requests.get(
                        f"{Config.TELLER_API_URL}/accounts/{account_id}/transactions",
                        headers=headers,
                        params={'from_date': from_date, 'count': 1000},
                        timeout=30
                    )
                    
                    if transactions_response.status_code == 200:
                        transactions = transactions_response.json()
                        
                        # Store transactions in MongoDB
                        account_transactions = 0
                        for txn in transactions:
                            # Enhanced transaction record
                            transaction_record = {
                                'account_id': account_id,
                                'user_id': user_id,
                                'transaction_id': txn.get('id'),
                                'amount': float(txn.get('amount', 0)),
                                'date': parse_teller_date(txn.get('date')),
                                'description': txn.get('description', ''),
                                'counterparty': txn.get('counterparty', {}),
                                'type': txn.get('type', ''),
                                'status': txn.get('status', ''),
                                'bank_name': account_info.get('institution', {}).get('name', 'Unknown'),
                                'account_name': account_info.get('name', 'Unknown Account'),
                                'account_type': account_info.get('type', 'checking'),
                                'synced_at': datetime.utcnow(),
                                'teller_user_id': user_id,
                                'raw_data': txn
                            }
                            
                            # Upsert to avoid duplicates
                            mongo_client.db.bank_transactions.update_one(
                                {'transaction_id': txn.get('id')},
                                {'$set': transaction_record},
                                upsert=True
                            )
                            account_transactions += 1
                        
                        total_transactions += account_transactions
                        sync_results.append({
                            'account_id': account_id,
                            'user_id': user_id,
                            'account_name': account_info.get('name'),
                            'bank_name': account_info.get('institution', {}).get('name'),
                            'account_type': account_info.get('type'),
                            'transactions_synced': account_transactions,
                            'date_range': f"{from_date} to {datetime.utcnow().strftime('%Y-%m-%d')}",
                            'status': 'success'
                        })
                        
                        logger.info(f"✅ Synced {account_transactions} transactions for {account_id} ({account_info.get('name')})")
                    
                    else:
                        error_msg = f"Failed to fetch transactions for {account_id}: {transactions_response.status_code} - {transactions_response.text[:200]}"
                        sync_results.append({
                            'account_id': account_id,
                            'user_id': user_id,
                            'status': 'error',
                            'error': error_msg,
                            'http_status': transactions_response.status_code
                        })
                        logger.error(f"❌ {error_msg}")
            
            elif accounts_response.status_code == 401:
                error_msg = f"Invalid or expired access token for user {user_id}"
                sync_results.append({
                    'user_id': user_id,
                    'status': 'error',
                    'error': error_msg,
                    'action_required': 'reconnect_teller'
                })
                logger.error(f"❌ {error_msg}")
            
            else:
                error_msg = f"Failed to fetch accounts for {user_id}: {accounts_response.status_code} - {accounts_response.text[:200]}"
                sync_results.append({
                    'user_id': user_id,
                    'status': 'error',
                    'error': error_msg,
                    'http_status': accounts_response.status_code
                })
                logger.error(f"❌ {error_msg}")
        
        except Exception as e:
            sync_results.append({
                'user_id': account.get('user_id', 'unknown'),
                'status': 'error',
                'error': str(e)
            })
            logger.error(f"❌ Error syncing user {account.get('user_id')}: {e}")
    '''
    
    return bank_sync_fix

def fix_google_sheets_error():
    """
    FIX 4: Google Sheets Error - Enhanced error handling
    """
    
    sheets_fix = '''
    # Enhanced Google Sheets error handling
    try:
        # Create new spreadsheet with better error handling
        if not sheets_client or not sheets_client.connected:
            return jsonify({
                "success": False,
                "error": "Google Sheets service not connected. Check service account credentials.",
                "details": "Verify GOOGLE_CREDENTIALS_JSON is set and valid"
            }), 500
        
        spreadsheet_id = sheets_client.create_spreadsheet(spreadsheet_title)
        if not spreadsheet_id:
            return jsonify({
                "success": False,
                "error": "Failed to create Google Spreadsheet - spreadsheet_id is None",
                "details": "Check service account has Google Drive and Sheets API permissions"
            }), 500
            
    except Exception as create_error:
        error_details = str(create_error)
        logger.error(f"Spreadsheet creation failed: {error_details}")
        
        # Provide specific error guidance
        if "403" in error_details or "forbidden" in error_details.lower():
            error_msg = "Permission denied: Service account lacks Google Sheets/Drive permissions"
        elif "401" in error_details or "unauthorized" in error_details.lower():
            error_msg = "Authentication failed: Invalid service account credentials"
        elif "quota" in error_details.lower():
            error_msg = "API quota exceeded: Too many requests to Google Sheets"
        else:
            error_msg = f"Google Sheets API error: {error_details}"
        
        return jsonify({
            "success": False,
            "error": error_msg,
            "technical_details": error_details,
            "troubleshooting": {
                "check_credentials": "Verify GOOGLE_CREDENTIALS_JSON environment variable",
                "check_permissions": "Ensure service account has Sheets/Drive API access",
                "check_sharing": "Service account email may need access to Drive folder"
            }
        }), 500
    '''
    
    return sheets_fix

if __name__ == "__main__":
    print("🔧 Receipt Processor Fixes")
    print("=" * 50)
    print("1. ✅ Camera scanner blur - FIXED (removed backdrop-filter: blur)")
    print("2. ✅ Receipt processing 'errors' - FIXED (errors list already exists)")
    print("3. 🔧 Bank sync taking 2 seconds - Need to fix account retrieval logic")
    print("4. 🔧 Google Sheets creation failure - Need enhanced error handling")
    print("\nTo apply these fixes, update the corresponding sections in app.py") 
from flask import Flask, request, render_template, jsonify, send_file
from pymongo import MongoClient
from datetime import datetime
import os
import logging
import csv
from dotenv import load_dotenv
from io import StringIO

from multi_gmail_client import MultiGmailClient
from receipt_downloader import ReceiptDownloader
from huggingface_client import HuggingFaceClient
from bank_matcher import BankMatcher
from mongo_client import MongoDBClient
from teller_client import TellerClient
from expense_categorizer import ExpenseCategorizer
from r2_client import R2Client
from config import Config
from environment_manager import EnvironmentManager

# Load env
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask setup
app = Flask(__name__)
app.config.from_object(Config)

# Initialize clients lazily to avoid startup hanging
gmail_client = None
huggingface_client = None
bank_matcher = None
expense_categorizer = None
r2_client = None
environment_manager = None

def get_gmail_client():
    global gmail_client
    if gmail_client is None:
        try:
            gmail_client = MultiGmailClient()
        except Exception as e:
            logger.error(f"Failed to initialize Gmail client: {e}")
            gmail_client = False
    return gmail_client

def get_huggingface_client():
    global huggingface_client
    if huggingface_client is None:
        try:
            huggingface_client = HuggingFaceClient()
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFace client: {e}")
            huggingface_client = False
    return huggingface_client

def get_r2_client():
    global r2_client
    if r2_client is None:
        try:
            r2_client = R2Client()
        except Exception as e:
            logger.error(f"Failed to initialize R2 client: {e}")
            r2_client = False
    return r2_client

def get_environment_manager():
    global environment_manager
    if environment_manager is None:
        try:
            environment_manager = EnvironmentManager()
        except Exception as e:
            logger.error(f"Failed to initialize Environment manager: {e}")
            environment_manager = False
    return environment_manager

# Initialize MongoDB clients with error handling
try:
    mongo_client = MongoDBClient()
    mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
    if mongo_uri:
        mongo = MongoClient(mongo_uri)
        # Extract database name or use default
        db_name = os.getenv('MONGODB_DATABASE', 'gmail_receipt_processor')
        if '/' in mongo_uri:
            try:
                uri_db = mongo_uri.split('/')[-1].split('?')[0]
                if uri_db and uri_db != mongo_uri:
                    db_name = uri_db
            except:
                pass
        db = mongo.get_database(db_name)
        logger.info("✅ MongoDB clients initialized")
    else:
        logger.warning("⚠️ No MongoDB URI found, using fallback database")
        mongo = None
        db = None
except Exception as e:
    logger.error(f"❌ MongoDB initialization failed: {e}")
    mongo_client = None
    mongo = None
    db = None

@app.route("/")
def index():
    """Amazing dashboard with real-time stats"""
    try:
        # Gather real-time statistics for the dashboard
        stats = {
            # Gmail stats
            'authenticated_accounts': 0,
            'total_accounts': 3,
            
            # Service status
            'mongo_connected': False,
            'r2_connected': False,
            'sheets_connected': False,
            'ai_connected': False,
            'teller_connected': False,
            
            # Counters
            'processed_count': 0,
            'receipts_count': 0,
            'bank_accounts': 0,
            'matched_receipts': 0,
            'total_amount': 0.0,
            'last_update': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Gmail Status
        try:
            client = get_gmail_client()
            if client and client is not False:
                gmail_stats = client.get_stats()
                stats['authenticated_accounts'] = gmail_stats.get('connected_accounts', 0)
                stats['total_accounts'] = gmail_stats.get('total_accounts', 3)
        except:
            pass
        
        # MongoDB Status
        try:
            if mongo_client and mongo_client.is_connected():
                stats['mongo_connected'] = True
                mongo_stats = mongo_client.get_stats()
                stats['processed_count'] = mongo_stats.get('processed_emails_count', 0)
                stats['receipts_count'] = mongo_stats.get('receipts_count', 0)
        except:
            pass
        
        # HuggingFace AI Status
        try:
            client = get_huggingface_client()
            if client and client is not False:
                hf_stats = client.get_stats()
                stats['ai_connected'] = hf_stats.get('connected', False)
        except:
            pass
        
        # Teller Status
        try:
            if db:
                teller_tokens = db.teller_tokens.count_documents({})
                stats['teller_connected'] = teller_tokens > 0
                stats['bank_accounts'] = teller_tokens
        except:
            pass
        
        # R2 Storage Status
        try:
            client = get_r2_client()
            if client and client is not False:
                r2_stats = client.get_stats()
                stats['r2_connected'] = r2_stats.get('connected', False)
            else:
                stats['r2_connected'] = False
        except:
            stats['r2_connected'] = False
        
        # Additional calculations
        stats['sheets_connected'] = bool(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
        
        return render_template("index.html", config=app.config, stats=stats)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        # Fallback stats if there's an error
        fallback_stats = {
            'authenticated_accounts': 0, 'total_accounts': 3,
            'mongo_connected': False, 'r2_connected': False, 
            'sheets_connected': False, 'ai_connected': False, 'teller_connected': False,
            'processed_count': 0, 'receipts_count': 0, 'bank_accounts': 0,
            'matched_receipts': 0, 'total_amount': 0.0,
            'last_update': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
        return render_template("index.html", config=app.config, stats=fallback_stats)

@app.route("/connect")
def connect_page():
    return render_template("connect.html", config=app.config)

@app.route("/status", methods=["GET"])
def get_system_status():
    """Check the health and status of all integrated services"""
    try:
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "services": {}
        }
        
        # Gmail Status
        try:
            client = get_gmail_client()
            if client and client is not False:
                gmail_stats = client.get_stats()
                status["services"]["gmail"] = {
                    "status": "connected" if gmail_stats["connected_accounts"] > 0 else "disconnected",
                    "details": gmail_stats
                }
            else:
                status["services"]["gmail"] = {"status": "not_configured", "error": "Gmail client not available"}
        except Exception as e:
            status["services"]["gmail"] = {"status": "error", "error": str(e)}
        
        # MongoDB Status
        try:
            if mongo_client and mongo_client.is_connected():
                mongo_stats = mongo_client.get_stats()
                status["services"]["mongodb"] = {
                    "status": "connected",
                    "details": mongo_stats
                }
            elif mongo_client:
                status["services"]["mongodb"] = {
                    "status": "disconnected", 
                    "details": {"message": "MongoDB client exists but not connected"}
                }
            else:
                status["services"]["mongodb"] = {
                    "status": "not_configured",
                    "details": {"message": "MongoDB not configured"}
                }
        except Exception as e:
            status["services"]["mongodb"] = {"status": "error", "error": str(e)}
        
        # HuggingFace Status
        try:
            client = get_huggingface_client()
            if client and client is not False:
                hf_stats = client.get_stats()
                status["services"]["huggingface"] = {
                    "status": "connected" if hf_stats["connected"] else "disconnected",
                    "details": hf_stats
                }
            else:
                status["services"]["huggingface"] = {"status": "not_configured", "error": "HuggingFace client not available"}
        except Exception as e:
            status["services"]["huggingface"] = {"status": "error", "error": str(e)}
        
        # R2 Storage Status
        try:
            r2_stats = r2_client.get_stats()
            status["services"]["r2"] = {
                "status": "connected" if r2_stats["connected"] else "disconnected",
                "details": r2_stats
            }
        except Exception as e:
            status["services"]["r2"] = {"status": "error", "error": str(e)}
        
        # Teller Status (check if any users have tokens)
        try:
            if db is not None:
                teller_tokens = db.teller_tokens.count_documents({})
                status["services"]["teller"] = {
                    "status": "configured" if teller_tokens > 0 else "not_configured",
                    "details": {"connected_users": teller_tokens}
                }
            else:
                status["services"]["teller"] = {
                    "status": "not_configured",
                    "details": {"message": "Database not available for Teller tokens"}
                }
        except Exception as e:
            status["services"]["teller"] = {"status": "error", "error": str(e)}
        
        # Overall status check
        service_statuses = [service["status"] for service in status["services"].values()]
        if "error" in service_statuses:
            status["overall_status"] = "degraded"
        elif all(s in ["connected", "configured"] for s in service_statuses):
            status["overall_status"] = "healthy"
        else:
            status["overall_status"] = "partial"
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "error",
            "error": str(e)
        }), 500

@app.route("/teller/save-token", methods=["POST"])
def save_token():
    if db is None:
        return jsonify({"error": "Database not available"}), 503
        
    data = request.get_json()
    token = data.get("accessToken")
    user_id = data.get("userId")
    enrollment_id = data.get("enrollmentId")
    if not token or not user_id:
        return jsonify({"error": "Missing fields"}), 400
        
    try:
        db.teller_tokens.update_one(
            {"userId": user_id},
            {"$set": {
                "accessToken": token,
                "enrollmentId": enrollment_id,
                "updatedAt": datetime.utcnow()
            }},
            upsert=True
        )
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error saving Teller token: {e}")
        return jsonify({"error": "Failed to save token"}), 500

@app.route("/teller/accounts", methods=["GET"])
def get_accounts():
    if db is None:
        return jsonify({"error": "Database not available"}), 503
        
    user_id = request.args.get("userId")
    if not user_id:
        return jsonify({"error": "userId parameter required"}), 400
        
    try:
        rec = db.teller_tokens.find_one({"userId": user_id})
        if not rec:
            return jsonify({"error": "No access token found"}), 404
            
        tc = TellerClient(access_token=rec["accessToken"])
        accounts = tc.get_accounts()
        return jsonify({"accounts": accounts})
        
    except Exception as e:
        logger.error(f"Error fetching Teller accounts: {e}")
        return jsonify({"error": "Failed to fetch accounts"}), 500

@app.route("/teller/transactions", methods=["GET"])
def get_transactions():
    if db is None:
        return jsonify({"error": "Database not available"}), 503
        
    user_id = request.args.get("userId")
    if not user_id:
        return jsonify({"error": "userId parameter required"}), 400
        
    try:
        rec = db.teller_tokens.find_one({"userId": user_id})
        if not rec:
            return jsonify({"error": "No token found"}), 404
            
        tc = TellerClient(access_token=rec["accessToken"])
        all_tx = []
        for acct in tc.get_accounts():
            tx = tc.get_transactions(account_id=acct["id"])
            all_tx.extend(tx)
        return jsonify({"transactions": all_tx})
        
    except Exception as e:
        logger.error(f"Error fetching Teller transactions: {e}")
        return jsonify({"error": "Failed to fetch transactions"}), 500

@app.route("/match-all", methods=["GET"])
def match_all_receipts_to_teller():
    """OPTIMIZED: Full receipt processing workflow with parallel processing"""
    try:
        # Get processing parameters
        days = int(request.args.get("days", 30))
        max_receipts = int(request.args.get("max_receipts", 50))
        user_id = request.args.get("userId", "default")
        
        logger.info(f"🚀 Starting receipt matching workflow for user {user_id}")
        
        # Step 1: Fetch receipt metadata from all Gmail accounts (OPTIMIZED)
        logger.info(f"📧 Fetching receipt metadata from last {days} days...")
        messages = gmail_client.fetch_receipt_metadata_parallel(days=days, max_per_account=max_receipts)
        
        if not messages:
            return jsonify({"error": "No receipt messages found"}), 404
        
        # Limit total messages to process
        if len(messages) > max_receipts:
            messages = messages[:max_receipts]
            logger.info(f"📊 Limited to {max_receipts} most recent receipts")
        
        # Step 2: Get available Gmail service (from any connected account)
        available_accounts = gmail_client.get_available_accounts()
        connected_accounts = [acc for acc in available_accounts if acc['status'] == 'connected']
        
        if not connected_accounts:
            return jsonify({"error": "No Gmail accounts connected"}), 500
        
        # Use the first connected account's service
        first_account_email = connected_accounts[0]['email']
        service = gmail_client.accounts[first_account_email]['service']
        
        # Step 3: Download and process receipts (OPTIMIZED)
        logger.info(f"📎 Processing {len(messages)} receipt attachments...")
        downloader = ReceiptDownloader(ocr_processor=huggingface_client, r2_client=r2_client)
        parsed_receipts = downloader.download_and_process_attachments_parallel(
            service=service, 
            messages=messages,
            max_workers=15  # Increased for better performance
        )
        
        if not parsed_receipts:
            return jsonify({"error": "No receipts could be processed"}), 404
        
        # Step 4: Get Teller banking data
        logger.info(f"🏦 Fetching banking transactions for user {user_id}...")
        rec = db.teller_tokens.find_one({"userId": user_id})
        if not rec:
            return jsonify({"error": "No Teller token found - please connect your bank first"}), 404

        tc = TellerClient(access_token=rec["accessToken"])
        transactions = []
        
        try:
            accounts = tc.get_accounts()
            for acct in accounts:
                account_transactions = tc.get_transactions(account_id=acct["id"])
                transactions.extend(account_transactions)
            
            logger.info(f"💳 Retrieved {len(transactions)} bank transactions")
            
        except Exception as teller_error:
            logger.error(f"Teller API error: {teller_error}")
            return jsonify({"error": f"Failed to fetch bank data: {str(teller_error)}"}), 500

        # Step 5: Match receipts to transactions (OPTIMIZED)
        logger.info(f"🔍 Matching {len(parsed_receipts)} receipts to {len(transactions)} transactions...")
        results = []
        
        for i, receipt in enumerate(parsed_receipts):
            try:
                # Find matches for this receipt
                matches = bank_matcher.find_matches(receipt, transactions)
                summary = bank_matcher.generate_summary_report(matches)
                
                # STEP 5.5: INTELLIGENT EXPENSE CATEGORIZATION
                logger.info(f"🤖 Categorizing expense #{i+1}...")
                
                # Prepare expense data for categorization
                expense_data = {
                    'description': receipt.get('merchant', ''),
                    'memo': receipt.get('description', ''),
                    'merchant': receipt.get('merchant', ''),
                    'amount': receipt.get('total_amount', 0),
                    'email_account': receipt.get('email_account', ''),
                    'date': receipt.get('date', ''),
                    'id': f"receipt_{i+1}"
                }
                
                # Get intelligent categorization
                category_result = expense_categorizer.categorize_expense(expense_data)
                
                # Create comprehensive record with categorization
                record = {
                    "receipt": receipt,
                    "matches": matches,
                    "summary": summary,
                    "processing_order": i + 1,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                    # Enhanced categorization data
                    "expense_category": category_result.category,
                    "category_details": category_result.details,
                    "category_confidence": category_result.confidence,
                    "needs_review": category_result.needs_review,
                    "extracted_location": category_result.location,
                    "client_name": category_result.client_name,
                    "business_type": category_result.business_type
                }
                
                # Save to MongoDB if connected
                if mongo_client.is_connected():
                    try:
                        mongo_client.save_match_result(record)
                    except Exception as mongo_error:
                        logger.warning(f"MongoDB save failed: {mongo_error}")
                
                results.append(record)
                
                # Log progress with categorization info
                if (i + 1) % 10 == 0:
                    logger.info(f"✅ Processed {i + 1}/{len(parsed_receipts)} receipts")
                elif category_result.confidence > 0.8:
                    logger.info(f"🎯 High confidence categorization: {category_result.category}")
                    
            except Exception as match_error:
                logger.error(f"Failed to match receipt {i + 1}: {match_error}")
                continue

        # Step 6: Generate comprehensive response with categorization insights
        successful_matches = len([r for r in results if r.get('matches')])
        high_confidence_categories = len([r for r in results if r.get('category_confidence', 0) > 0.8])
        needs_review_count = len([r for r in results if r.get('needs_review', 0)])
        
        # Extract expenses for statistics
        categorized_expenses = []
        for result in results:
            if 'expense_category' in result:
                categorized_expenses.append({
                    'category': result['expense_category'],
                    'confidence': result['category_confidence'],
                    'needs_review': result['needs_review'],
                    'business_type': result['business_type']
                })
        
        # Get categorization statistics
        category_stats = expense_categorizer.get_category_statistics(categorized_expenses) if categorized_expenses else {}
        
        response_data = {
            "success": True,
            "summary": {
                "total_messages_found": len(messages),
                "receipts_processed": len(parsed_receipts),
                "bank_transactions": len(transactions),
                "successful_matches": successful_matches,
                "match_rate": f"{(successful_matches/len(parsed_receipts)*100):.1f}%" if parsed_receipts else "0%"
            },
            "categorization_summary": {
                "total_categorized": len(categorized_expenses),
                "high_confidence_categories": high_confidence_categories,
                "needs_manual_review": needs_review_count,
                "category_breakdown": category_stats.get('categories', {}),
                "business_type_breakdown": category_stats.get('business_types', {}),
                "confidence_distribution": {
                    "high": category_stats.get('high_confidence', 0),
                    "medium": category_stats.get('medium_confidence', 0),
                    "low": category_stats.get('low_confidence', 0)
                }
            },
            "processing_info": {
                "days_searched": days,
                "accounts_used": len(connected_accounts),
                "processing_time": datetime.utcnow().isoformat(),
                "user_id": user_id
            },
            "matched_results": results
        }
        
        logger.info(f"🎉 Workflow completed! {successful_matches}/{len(parsed_receipts)} receipts matched")
        logger.info(f"🤖 Categorization completed! {high_confidence_categories}/{len(categorized_expenses)} high-confidence categories")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ /match-all workflow error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route("/match-all-precision", methods=["GET"])
def match_all_receipts_precision_mode():
    """REVOLUTIONARY: Teller-guided Gmail search for PERFECT precision and speed"""
    try:
        # Get processing parameters
        days = int(request.args.get("days", 30))
        max_receipts = int(request.args.get("max_receipts", 50))
        user_id = request.args.get("userId", "default")
        
        logger.info(f"🎯 PRECISION MODE: Starting Teller-guided receipt workflow for user {user_id}")
        
        # Step 1: Get Teller banking data FIRST
        logger.info(f"🏦 Fetching banking transactions for user {user_id}...")
        rec = db.teller_tokens.find_one({"userId": user_id})
        
        # If no token for specific user, try to find any available token
        if not rec:
            rec = db.teller_tokens.find_one()
            if rec:
                logger.info(f"🔄 Using available Teller token for user {rec.get('userId', 'unknown')}")
        
        if not rec:
            return jsonify({"error": "No Teller token found - please connect your bank first"}), 404

        tc = TellerClient(access_token=rec["accessToken"])
        transactions = []
        
        try:
            accounts = tc.get_connected_accounts()
            for acct in accounts:
                account_transactions = tc.get_transactions(account_id=acct.id)
                transactions.extend(account_transactions)
            
            logger.info(f"💳 Retrieved {len(transactions)} bank transactions")
            
        except Exception as teller_error:
            logger.error(f"Teller API error: {teller_error}")
            return jsonify({"error": f"Failed to fetch bank data: {str(teller_error)}"}), 500

        if not transactions:
            return jsonify({"error": "No bank transactions found"}), 404
        
        # Step 2: REVOLUTIONARY - Use Teller data to guide Gmail searches
        logger.info(f"🎯 Using {len(transactions)} transactions to guide Gmail searches...")
        messages = gmail_client.fetch_receipt_metadata_teller_guided(
            teller_transactions=transactions, 
            days=days, 
            max_per_account=max_receipts
        )
        
        if not messages:
            return jsonify({"error": "No targeted receipt messages found"}), 404
        
        # Step 3: Get available Gmail service
        available_accounts = gmail_client.get_available_accounts()
        connected_accounts = [acc for acc in available_accounts if acc['status'] == 'connected']
        
        if not connected_accounts:
            return jsonify({"error": "No Gmail accounts connected"}), 500
        
        # Use the first connected account's service
        first_account_email = connected_accounts[0]['email']
        service = gmail_client.accounts[first_account_email]['service']
        
        # Step 4: Process targeted receipts (ENHANCED)
        logger.info(f"📎 Processing {len(messages)} targeted receipt attachments...")
        downloader = ReceiptDownloader(ocr_processor=huggingface_client, r2_client=r2_client)
        parsed_receipts = downloader.download_and_process_attachments_parallel(
            service=service, 
            messages=messages,
            max_workers=10  # Optimized for precision
        )
        
        if not parsed_receipts:
            return jsonify({"error": "No receipts could be processed"}), 404
        
        # Step 5: Enhanced matching with pre-calculated probabilities
        logger.info(f"🔍 Precision matching {len(parsed_receipts)} receipts to {len(transactions)} transactions...")
        results = []
        
        for i, receipt in enumerate(parsed_receipts):
            try:
                # Enhanced matching with transaction target info
                target_transaction_id = receipt.get('target_transaction')
                target_amount = receipt.get('target_amount')
                match_probability = receipt.get('match_probability', 0)
                
                # Find matches with enhanced confidence
                matches = bank_matcher.find_matches(receipt, transactions)
                
                # Boost confidence for pre-targeted matches
                if target_transaction_id and matches:
                    for match in matches:
                        if match['transaction'].get('id') == target_transaction_id:
                            match['confidence'] = min(match['confidence'] + match_probability, 1.0)
                            match['enhanced_confidence'] = True
                
                summary = bank_matcher.generate_summary_report(matches)
                
                # Enhanced expense categorization
                expense_data = {
                    'description': receipt.get('merchant', ''),
                    'memo': receipt.get('description', ''),
                    'merchant': receipt.get('merchant', ''),
                    'amount': receipt.get('total_amount', 0),
                    'email_account': receipt.get('email_account', ''),
                    'date': receipt.get('date', ''),
                    'id': f"precision_receipt_{i+1}"
                }
                
                category_result = expense_categorizer.categorize_expense(expense_data)
                
                # Create enhanced record with precision data
                record = {
                    "receipt": receipt,
                    "matches": matches,
                    "summary": summary,
                    "processing_order": i + 1,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                    "precision_mode": True,
                    "target_transaction_id": target_transaction_id,
                    "pre_match_probability": match_probability,
                    # Enhanced categorization data
                    "expense_category": category_result.category,
                    "category_details": category_result.details,
                    "category_confidence": category_result.confidence,
                    "needs_review": category_result.needs_review,
                    "extracted_location": category_result.location,
                    "client_name": category_result.client_name,
                    "business_type": category_result.business_type
                }
                
                # Save to MongoDB if connected
                if mongo_client.is_connected():
                    try:
                        mongo_client.save_match_result(record)
                    except Exception as mongo_error:
                        logger.warning(f"MongoDB save failed: {mongo_error}")
                
                results.append(record)
                
                # Enhanced progress logging
                if (i + 1) % 5 == 0:
                    logger.info(f"🎯 Processed {i + 1}/{len(parsed_receipts)} precision receipts")
                    
            except Exception as match_error:
                logger.error(f"Failed to match precision receipt {i + 1}: {match_error}")
                continue

        # Step 6: Enhanced analytics for precision mode
        successful_matches = len([r for r in results if r.get('matches')])
        high_confidence_matches = len([r for r in results if r.get('matches') and r['matches'][0]['confidence'] > 0.8])
        precision_matches = len([r for r in results if r.get('pre_match_probability', 0) > 0.5])
        
        # Extract expenses for statistics
        categorized_expenses = []
        for result in results:
            if 'expense_category' in result:
                categorized_expenses.append({
                    'category': result['expense_category'],
                    'confidence': result['category_confidence'],
                    'needs_review': result['needs_review'],
                    'business_type': result['business_type']
                })
        
        category_stats = expense_categorizer.get_category_statistics(categorized_expenses) if categorized_expenses else {}
        
        response_data = {
            "success": True,
            "precision_mode": True,
            "summary": {
                "bank_transactions_analyzed": len(transactions),
                "targeted_messages_found": len(messages),
                "receipts_processed": len(parsed_receipts),
                "successful_matches": successful_matches,
                "high_confidence_matches": high_confidence_matches,
                "precision_guided_matches": precision_matches,
                "match_rate": f"{(successful_matches/len(parsed_receipts)*100):.1f}%" if parsed_receipts else "0%",
                "precision_rate": f"{(precision_matches/len(parsed_receipts)*100):.1f}%" if parsed_receipts else "0%"
            },
            "categorization_summary": {
                "total_categorized": len(categorized_expenses),
                "category_breakdown": category_stats.get('categories', {}),
                "business_type_breakdown": category_stats.get('business_types', {}),
                "confidence_distribution": {
                    "high": category_stats.get('high_confidence', 0),
                    "medium": category_stats.get('medium_confidence', 0),
                    "low": category_stats.get('low_confidence', 0)
                }
            },
            "processing_info": {
                "days_searched": days,
                "accounts_used": len(connected_accounts),
                "processing_time": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "mode": "teller_guided_precision"
            },
            "matched_results": results
        }
        
        logger.info(f"🎯 PRECISION MODE completed! {successful_matches}/{len(parsed_receipts)} receipts matched with {precision_matches} precision-guided")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ /match-all-precision workflow error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route("/categorization-stats", methods=["GET"])
def get_categorization_stats():
    """Get detailed categorization statistics from stored data"""
    try:
        if not mongo_client.is_connected():
            return jsonify({"error": "MongoDB not connected"}), 500

        # Get all match results with categorization
        match_data = mongo_client.get_all_match_results()
        if not match_data:
            return jsonify({"error": "No categorized data found"}), 404

        # Extract expenses for statistics
        categorized_expenses = []
        for record in match_data:
            if 'expense_category' in record:
                categorized_expenses.append({
                    'category': record['expense_category'],
                    'confidence': record['category_confidence'],
                    'needs_review': record['needs_review'],
                    'business_type': record['business_type'],
                    'amount': record.get('receipt', {}).get('total_amount', 0)
                })
        
        if not categorized_expenses:
            return jsonify({"error": "No categorized expenses found"}), 404

        # Get detailed statistics
        stats = expense_categorizer.get_category_statistics(categorized_expenses)
        
        # Calculate financial totals by category
        category_totals = {}
        business_type_totals = {}
        
        for expense in categorized_expenses:
            category = expense['category']
            business_type = expense['business_type']
            amount = float(expense.get('amount', 0))
            
            if category not in category_totals:
                category_totals[category] = 0
            category_totals[category] += amount
            
            if business_type not in business_type_totals:
                business_type_totals[business_type] = 0
            business_type_totals[business_type] += amount
        
        return jsonify({
            "success": True,
            "statistics": stats,
            "financial_totals": {
                "by_category": category_totals,
                "by_business_type": business_type_totals,
                "grand_total": sum(category_totals.values())
            },
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"/categorization-stats error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/netsuite-categories", methods=["GET"])
def get_netsuite_categories():
    """Get all available NetSuite expense categories"""
    try:
        # Get all categories from the categorizer
        all_categories = {}
        
        for category_key, config in expense_categorizer.categories.items():
            category_group = category_key.split('_')[0]  # BD, DH, SCC, etc.
            
            if category_group not in all_categories:
                all_categories[category_group] = []
            
            all_categories[category_group].append({
                'key': category_key,
                'category': config.category,
                'details': config.details,
                'keywords': config.keywords,
                'confidence_boost': config.confidence_boost
            })
        
        return jsonify({
            "success": True,
            "categories": all_categories,
            "total_categories": len(expense_categorizer.categories),
            "ai_enabled": hasattr(expense_categorizer, 'get_ai_category_suggestion'),
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"/netsuite-categories error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/export-csv", methods=["GET"])
def export_csv():
    try:
        if not mongo_client.is_connected():
            return jsonify({"error": "MongoDB not connected"}), 500

        match_data = mongo_client.get_all_match_results()
        if not match_data:
            return jsonify({"error": "No data found"}), 404

        si = StringIO()
        writer = csv.writer(si)
        writer.writerow([
            "Merchant", "Date", "Amount", "Match Confidence", "Match Summary", 
            "Expense Category", "Category Details", "Category Confidence", 
            "Business Type", "Client Name", "Location", "Needs Review",
            "Receipt URL", "Email Account", "Gmail Link", "File Size"
        ])

        for record in match_data:
            r = record.get("receipt", {})
            summary = record.get("summary", "")
            amount = r.get("total_amount", "")
            merchant = r.get("merchant", "")
            date = r.get("date", "")
            best_conf = record["matches"][0]["confidence"] if record["matches"] else ""
            
            # Enhanced categorization fields
            expense_category = record.get("expense_category", "")
            category_details = record.get("category_details", "")
            category_confidence = record.get("category_confidence", "")
            business_type = record.get("business_type", "")
            client_name = record.get("client_name", "")
            location = record.get("extracted_location", "")
            needs_review = "Yes" if record.get("needs_review", 0) else "No"
            
            # Extract additional receipt info
            r2_url = r.get("r2_url", "")
            email_account = r.get("email_account", "")
            email_id = r.get("email_id", "")
            gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{email_id}" if email_id else ""
            file_size = r.get("file_size", "")
            
            writer.writerow([
                merchant, date, amount, best_conf, summary.replace("\n", " "),
                expense_category, category_details, category_confidence,
                business_type, client_name, location, needs_review,
                r2_url, email_account, gmail_link, file_size
            ])

        si.seek(0)
        filename = f"receipt_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(si.getvalue())

        return send_file(filename, as_attachment=True)

    except Exception as e:
        logger.error(f"/export-csv error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/scanner")
def scanner_page():
    """Camera scanner page for mobile receipt capture"""
    return render_template("receipt_scanner.html", config=app.config)

@app.route("/socket.io/")
def socket_io_not_implemented():
    """Handle socket.io requests with proper error response"""
    return jsonify({
        "error": "Socket.io not implemented",
        "message": "This application uses HTTP polling instead of WebSocket",
        "status": "disabled"
    }), 404

@app.route("/api/process-receipts", methods=["POST"])
def api_process_receipts():
    """API endpoint for processing receipts from the dashboard"""
    try:
        data = request.get_json() or {}
        days = data.get('days', 30)
        max_receipts = data.get('max_receipts', 25)
        user_id = data.get('userId', 'default')
        
        logger.info(f"🚀 Starting receipt processing via API: days={days}, max_receipts={max_receipts}, user={user_id}")
        
        # Call the existing match-all function directly
        # Set up fake request args for the function
        from unittest.mock import Mock
        original_request = request
        
        mock_request = Mock()
        mock_request.args = {
            'days': str(days),
            'max_receipts': str(max_receipts),
            'userId': user_id
        }
        
        # Temporarily replace request object
        import sys
        current_module = sys.modules[__name__]
        setattr(current_module, 'request', mock_request)
        
        try:
            # Use precision mode that searches Gmail based on bank transactions
            result = match_all_receipts_precision_mode()
            
            # Restore original request
            setattr(current_module, 'request', original_request)
            
            # Handle Flask Response objects
            if hasattr(result, 'get_json'):
                result_data = result.get_json()
                return jsonify({
                    "success": True,
                    "message": "Receipt processing completed",
                    "data": result_data
                })
            else:
                # If it's already a Response object, return it directly
                return result
            
        except Exception as process_error:
            # Restore original request even on error
            setattr(current_module, 'request', original_request)
            raise process_error
            
    except Exception as e:
        logger.error(f"/api/process-receipts error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/export-csv", methods=["GET"])
def api_export_csv():
    """API endpoint for CSV export from the dashboard"""
    return export_csv()

@app.route("/api/camera-capture", methods=["POST"])
def api_camera_capture():
    """Handle camera captured receipt images"""
    try:
        data = request.get_json()
        image_data = data.get('image_data')
        
        if not image_data:
            return jsonify({"error": "No image data provided"}), 400
        
        # Process the base64 image with HuggingFace
        # Remove the data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64 image
        import base64
        image_bytes = base64.b64decode(image_data)
        
        # Save to R2 if connected
        r2_key = None
        if r2_client.is_connected():
            try:
                timestamp = datetime.utcnow().strftime('%Y/%m/%d/%H%M%S')
                r2_key = f"camera_captures/{timestamp}_receipt.jpg"
                
                # Save to temporary file first
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    temp_file.write(image_bytes)
                    temp_path = temp_file.name
                
                # Upload to R2
                upload_success = r2_client.upload_file(
                    temp_path, 
                    r2_key, 
                    metadata={
                        "source": "camera_capture",
                        "timestamp": datetime.utcnow().isoformat(),
                        "content_type": "image/jpeg"
                    }
                )
                
                # Clean up temp file
                os.unlink(temp_path)
                
                if not upload_success:
                    r2_key = None
                    
            except Exception as e:
                logger.warning(f"Failed to upload to R2: {e}")
                r2_key = None
        
        # Process with HuggingFace OCR
        result = huggingface_client.process_image(image_bytes)
        
        if result:
            # Add R2 URL if uploaded
            if r2_key:
                result['r2_key'] = r2_key
                result['r2_url'] = f"{os.getenv('R2_PUBLIC_URL')}/{r2_key}"
            
            # Store in MongoDB if connected
            if mongo_client and mongo_client.is_connected():
                camera_record = {
                    "source": "camera_capture",
                    "timestamp": datetime.utcnow().isoformat(),
                    "processed_data": result,
                    "image_size": len(image_bytes),
                    "r2_key": r2_key
                }
                mongo_client.save_camera_capture(camera_record)
            
            return jsonify({
                "success": True,
                "data": result,
                "message": "Receipt processed successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to process receipt image"
            }), 500
            
    except Exception as e:
        logger.error(f"/api/camera-capture error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/batch-upload", methods=["POST"])
def api_batch_upload():
    """Handle batch file upload from scanner"""
    try:
        files = request.files.getlist('files')
        
        if not files:
            return jsonify({"error": "No files provided"}), 400
        
        processed_count = 0
        results = []
        
        for file in files:
            if file and file.filename:
                try:
                    # Read file data
                    file_data = file.read()
                    
                    # Process with HuggingFace
                    result = huggingface_client.process_image(file_data)
                    
                    if result:
                        processed_count += 1
                        results.append({
                            "filename": file.filename,
                            "data": result
                        })
                        
                        # Store in MongoDB if connected
                        if mongo_client and mongo_client.is_connected():
                            batch_record = {
                                "source": "batch_upload",
                                "filename": file.filename,
                                "timestamp": datetime.utcnow().isoformat(),
                                "processed_data": result,
                                "file_size": len(file_data)
                            }
                            mongo_client.save_batch_upload(batch_record)
                            
                except Exception as file_error:
                    logger.error(f"Failed to process {file.filename}: {file_error}")
                    continue
        
        return jsonify({
            "success": True,
            "data": {
                "processed_count": processed_count,
                "total_files": len(files),
                "results": results
            },
            "message": f"Successfully processed {processed_count}/{len(files)} files"
        })
        
    except Exception as e:
        logger.error(f"/api/batch-upload error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/validate-image", methods=["POST"])
def api_validate_image():
    """Validate image quality for receipt scanning"""
    try:
        data = request.get_json()
        image_data = data.get('image_data')
        
        if not image_data:
            return jsonify({"error": "No image data provided"}), 400
        
        # Basic validation (you can enhance this)
        feedback = []
        valid = True
        
        # Check image size (basic validation)
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        import base64
        try:
            image_bytes = base64.b64decode(image_data)
            size_mb = len(image_bytes) / (1024 * 1024)
            
            if size_mb > 10:
                valid = False
                feedback.append("Image too large (>10MB)")
            elif size_mb < 0.1:
                valid = False
                feedback.append("Image too small (<100KB)")
            else:
                feedback.append("Image size looks good")
                
        except Exception:
            valid = False
            feedback.append("Invalid image format")
        
        return jsonify({
            "valid": valid,
            "feedback": feedback,
            "message": "Image validation complete"
        })
        
    except Exception as e:
        logger.error(f"/api/validate-image error: {str(e)}")
        return jsonify({
            "error": str(e),
            "valid": False
        }), 500

@app.route("/oauth2callback")
def oauth2callback():
    """Handle Google OAuth2 callback for render.com"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        logger.error(f"OAuth error: {error}")
        return jsonify({"error": f"OAuth authentication failed: {error}"}), 400
    
    if not code:
        return jsonify({"error": "Missing authorization code"}), 400
    
    try:
        # Handle the OAuth callback - this would integrate with your Gmail client
        return jsonify({
            "success": True,
            "message": "OAuth callback received",
            "code": code[:20] + "...",  # Truncated for security
            "state": state
        })
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return jsonify({"error": "OAuth callback processing failed"}), 500

@app.route("/gmail/oauth/callback")
def gmail_oauth_callback():
    """Handle Gmail OAuth callback for render.com"""
    return oauth2callback()

@app.route("/auth/google/callback")
def google_auth_callback():
    """Handle Google auth callback for render.com"""
    return oauth2callback()

@app.route("/teller/callback")
def teller_callback():
    """Handle Teller OAuth callback for render.com"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        logger.error(f"Teller OAuth error: {error}")
        return jsonify({"error": f"Teller authentication failed: {error}"}), 400
    
    if not code:
        return jsonify({"error": "Missing Teller authorization code"}), 400
    
    try:
        # In production, exchange this code with Teller's token endpoint
        logger.info(f"Received Teller authorization code: {code[:20]}...")
        
        # This is where you'd exchange the code for an access token
        # For now, return success response
        return jsonify({
            "success": True,
            "message": "Teller authorization successful",
            "next_step": "Exchange authorization code for access token"
        })
        
    except Exception as e:
        logger.error(f"Teller callback error: {e}")
        return jsonify({"error": "Teller callback processing failed"}), 500

@app.route("/teller/webhook", methods=["POST"])
def teller_webhook():
    """Handle Teller webhook notifications"""
    try:
        data = request.get_json()
        signature = request.headers.get('Teller-Signature')
        
        # Verify webhook signature using TELLER_SIGNING_SECRET
        # This is a security requirement for production
        
        logger.info(f"Received Teller webhook: {data.get('type', 'unknown')}")
        
        # Process webhook data based on type
        webhook_type = data.get('type')
        
        if webhook_type == 'account.connected':
            # Handle new account connection
            logger.info("New account connected via Teller")
        elif webhook_type == 'transaction.created':
            # Handle new transaction
            logger.info("New transaction received via Teller")
        
        return jsonify({"success": True}), 200
        
    except Exception as e:
        logger.error(f"Teller webhook error: {e}")
        return jsonify({"error": "Webhook processing failed"}), 500

@app.route("/gmail/auth")
def gmail_auth():
    """Initiate Gmail authentication for render.com"""
    try:
        # This would initiate the Gmail OAuth flow
        auth_url = f"https://accounts.google.com/o/oauth2/auth"
        params = {
            'client_id': 'YOUR_CLIENT_ID',  # This should come from your credentials
            'redirect_uri': f"{request.host_url}oauth2callback",
            'scope': 'https://www.googleapis.com/auth/gmail.readonly',
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        # Build auth URL
        from urllib.parse import urlencode
        full_auth_url = f"{auth_url}?{urlencode(params)}"
        
        return jsonify({
            "auth_url": full_auth_url,
            "message": "Redirect user to this URL for authentication"
        })
        
    except Exception as e:
        logger.error(f"Gmail auth initiation error: {e}")
        return jsonify({"error": "Failed to initiate Gmail authentication"}), 500

@app.route("/settings")
def settings_page():
    """Settings page for environment configuration"""
    current_config = environment_manager.get_current_environment()
    return render_template("settings.html", config=current_config)

@app.route("/api/update-environment", methods=["POST"])
def update_environment():
    """Update Teller environment configuration"""
    try:
        data = request.get_json()
        environment = data.get('environment', 'sandbox')
        webhook_url = data.get('webhook_url')
        
        # Use the environment manager to switch environments
        result = environment_manager.switch_environment(environment, webhook_url)
        
        if result['success']:
            return jsonify({
                'success': True,
                'environment': result['environment'],
                'webhook_url': result['webhook_url'],
                'message': 'Configuration updated successfully. Push to GitHub to deploy to Render.'
            })
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        logger.error(f"Environment update error: {str(e)}")
        return jsonify({'error': str(e)}), 500



@app.route("/api/get-environment", methods=["GET"])
def get_current_environment():
    """Get current environment configuration"""
    try:
        config = environment_manager.get_current_environment()
        return jsonify(config)
        
    except Exception as e:
        logger.error(f"Get environment error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/deploy-environment", methods=["POST"])
def deploy_environment():
    """Deploy current configuration to Render"""
    try:
        data = request.get_json() or {}
        commit_message = data.get('message', 'Deploy environment configuration changes')
        
        success = environment_manager.deploy_to_render(commit_message)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Successfully deployed to Render. Check the deployment status in your Render dashboard.'
            })
        else:
            return jsonify({'error': 'Deployment failed'}), 500
            
    except Exception as e:
        logger.error(f"Deploy error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    # Use PORT environment variable for deployment, fallback to 5002 for local development (5001 is in use)
    port = int(os.getenv('PORT', 5002))
    debug_mode = os.getenv('FLASK_ENV', 'development') == 'development'
    app.run(host="0.0.0.0", port=port, debug=debug_mode) 
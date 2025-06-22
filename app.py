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
from config import Config

# Load env
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask setup
app = Flask(__name__)
app.config.from_object(Config)

# Clients
gmail_client = MultiGmailClient()
mongo_client = MongoDBClient()
huggingface_client = HuggingFaceClient()
bank_matcher = BankMatcher()
mongo = MongoClient(os.getenv("MONGO_URI"))
db = mongo.get_database()

@app.route("/connect")
def connect_page():
    return render_template("connect.html")

@app.route("/teller/save-token", methods=["POST"])
def save_token():
    data = request.get_json()
    token = data.get("accessToken")
    user_id = data.get("userId")
    enrollment_id = data.get("enrollmentId")
    if not token or not user_id:
        return jsonify({"error": "Missing fields"}), 400
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

@app.route("/teller/accounts", methods=["GET"])
def get_accounts():
    user_id = request.args.get("userId")
    rec = db.teller_tokens.find_one({"userId": user_id})
    if not rec:
        return jsonify({"error": "No access token found"}), 404
    tc = TellerClient(access_token=rec["accessToken"])
    return jsonify({"accounts": tc.get_accounts()})

@app.route("/teller/transactions", methods=["GET"])
def get_transactions():
    user_id = request.args.get("userId")
    rec = db.teller_tokens.find_one({"userId": user_id})
    if not rec:
        return jsonify({"error": "No token found"}), 404
    tc = TellerClient(access_token=rec["accessToken"])
    all_tx = []
    for acct in tc.get_accounts():
        tx = tc.get_transactions(account_id=acct["id"])
        all_tx.extend(tx)
    return jsonify({"transactions": all_tx})

@app.route("/match-all", methods=["GET"])
def match_all_receipts_to_teller():
    try:
        messages = gmail_client.fetch_receipt_metadata_parallel(days=30)
        service = gmail_client.accounts['brian@downhome.com']["service"]
        downloader = ReceiptDownloader(ocr_processor=huggingface_client)
        parsed_receipts = downloader.download_and_process_attachments_parallel(
            service=service, messages=messages[:15]
        )

        user_id = request.args.get("userId", "default")
        rec = db.teller_tokens.find_one({"userId": user_id})
        if not rec:
            return jsonify({"error": "No Teller token found"}), 404

        tc = TellerClient(access_token=rec["accessToken"])
        transactions = []
        for acct in tc.get_accounts():
            transactions += tc.get_transactions(account_id=acct["id"])

        results = []
        for receipt in parsed_receipts:
            matches = bank_matcher.find_matches(receipt, transactions)
            summary = bank_matcher.generate_summary_report(matches)
            record = {"receipt": receipt, "matches": matches, "summary": summary}
            if mongo_client.is_connected():
                mongo_client.save_match_result(record)
            results.append(record)

        return jsonify({
            "total_receipts": len(parsed_receipts),
            "matched_results": results
        })

    except Exception as e:
        logger.error(f"/match-all error: {str(e)}")
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
        writer.writerow(["Merchant", "Date", "Amount", "Match Confidence", "Match Summary"])

        for record in match_data:
            r = record.get("receipt", {})
            summary = record.get("summary", "")
            amount = r.get("total_amount", "")
            merchant = r.get("merchant", "")
            date = r.get("date", "")
            best_conf = record["matches"][0]["confidence"] if record["matches"] else ""
            writer.writerow([merchant, date, amount, best_conf, summary.replace("\n", " ")])

        si.seek(0)
        filename = f"receipt_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(si.getvalue())

        return send_file(filename, as_attachment=True)

    except Exception as e:
        logger.error(f"/export-csv error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True) 
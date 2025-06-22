from flask import Flask, redirect, request, render_template_string, jsonify
import os
import logging

# Flask App
app = Flask(__name__)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Teller Configuration
TELLER_CONNECT_URL = "https://connect.teller.io/connect"
TELLER_APPLICATION_ID = os.getenv("TELLER_APPLICATION_ID")
TELLER_REDIRECT_URI = os.getenv("TELLER_REDIRECT_URI", "http://localhost:5000/teller/callback")

# 🔐 UI Route to Begin Teller Auth
@app.route("/auth/teller")
def auth_teller():
    if not TELLER_APPLICATION_ID:
        return "Missing TELLER_APPLICATION_ID in env", 500

    auth_url = f"{TELLER_CONNECT_URL}?application_id={TELLER_APPLICATION_ID}&redirect_uri={TELLER_REDIRECT_URI}&scope=transactions:read accounts:read"
    return render_template_string("""
        <html>
        <head><title>Connect Teller</title></head>
        <body>
            <h2>Connect Your Bank</h2>
            <a href="{{ auth_url }}">
                <button style='padding: 12px 20px; font-size: 16px;'>Connect with Teller</button>
            </a>
        </body>
        </html>
    """, auth_url=auth_url)

# 🔁 Callback Route to Handle Teller Token Exchange
@app.route("/teller/callback")
def teller_callback():
    code = request.args.get("code")
    if not code:
        return "Missing Teller code", 400

    # In production, exchange this code with Teller's token endpoint
    return jsonify({
        "code": code,
        "message": "Exchange this code server-side to obtain a live access token."
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)
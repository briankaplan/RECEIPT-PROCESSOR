# 🛠️ Development Mode Setup Guide

## Local Development vs Production

### **Production (render.com)**
- Environment: `TELLER_ENVIRONMENT=sandbox` (for now)
- Webhook URL: `https://receipt-processor.onrender.com/teller/webhook`
- OAuth Redirects: `https://receipt-processor.onrender.com/teller/callback`

### **Local Development**
- Environment: `TELLER_ENVIRONMENT=sandbox` (same sandbox, different URLs)
- Webhook URL: `http://localhost:5000/teller/webhook` (with ngrok tunnel)
- OAuth Redirects: `http://localhost:5000/teller/callback`

## 🚀 Local Development Setup

### 1. Create .env for Local Development
```bash
cp env.example .env
```

Edit `.env` with these development-specific values:
```env
# Flask Development
FLASK_ENV=development
FLASK_DEBUG=true
DEBUG=true

# Teller Development Configuration
TELLER_APPLICATION_ID=app_pbvpiocruhfnvkhf1k000
TELLER_ENVIRONMENT=sandbox
TELLER_WEBHOOK_URL=https://your-ngrok-url.ngrok.io/teller/webhook
TELLER_SIGNING_SECRET=q7xdfvnwf6nbajjghgzbnzaut4tm4sck

# Local file paths
GMAIL_ACCOUNT_1_PICKLE_FILE=./gmail_tokens/kaplan_brian_gmail.pickle
GOOGLE_CREDENTIALS_PATH=./credentials/gmail_credentials.json
TELLER_CERT_PATH=./credentials/teller_certificate.pem
TELLER_KEY_PATH=./credentials/teller_private_key.pem
```

### 2. Set Up ngrok for Webhook Testing
```bash
# Install ngrok
brew install ngrok  # or download from ngrok.com

# Start your Flask app
python app.py

# In another terminal, expose port 5000
ngrok http 5000
```

Copy the ngrok URL (e.g., `https://abc123.ngrok.io`) and update:
- `.env`: `TELLER_WEBHOOK_URL=https://abc123.ngrok.io/teller/webhook`

### 3. Update Teller Dashboard for Development
Go to your Teller dashboard and **temporarily** update:
- **Webhook URL**: `https://abc123.ngrok.io/teller/webhook`

### 4. Test Local Development
```bash
# Start the app
python app.py

# Test endpoints:
# http://localhost:5000/status
# http://localhost:5000/connect
# http://localhost:5000/teller/webhook (via ngrok)
```

## 🔧 Development Workflow

### For Testing Webhooks Locally:
1. Start Flask app: `python app.py`
2. Start ngrok: `ngrok http 5000`
3. Update Teller webhook URL with ngrok URL
4. Test webhook in Teller dashboard
5. Check your local Flask logs for webhook events

### For Testing OAuth Locally:
1. Update Google Cloud Console redirect URIs:
   - Add: `http://localhost:5000/oauth2callback`
   - Add: `http://localhost:5000/teller/callback`
2. Test authentication flows locally

### Switching Between Environments:

**Development Mode:**
```bash
export FLASK_ENV=development
python app.py
```

**Production Mode (local test):**
```bash
export FLASK_ENV=production
export FLASK_DEBUG=false
gunicorn app:app --bind 0.0.0.0:5000
```

## 📋 Development Checklist

### Local Development Setup:
- [ ] `.env` file created with development values
- [ ] ngrok installed and running
- [ ] Teller webhook URL updated to ngrok URL
- [ ] Google OAuth redirect URIs include localhost
- [ ] All credential files in place locally

### Testing Checklist:
- [ ] Flask app starts without errors
- [ ] `/status` endpoint returns healthy status
- [ ] Teller Connect button works
- [ ] Webhook test from Teller dashboard succeeds
- [ ] Gmail authentication works locally

### Before Production Deploy:
- [ ] Revert Teller webhook URL to render.com URL
- [ ] Verify all secret files uploaded to Render
- [ ] Verify production environment variables
- [ ] Test production OAuth flows

## 🔄 Environment Switching Commands

```bash
# Switch to development
cp .env.development .env
python app.py

# Switch to production testing
cp .env.production .env
gunicorn app:app --bind 0.0.0.0:5000

# Deploy to production
git add . && git commit -m "deploy" && git push
```

## 🚨 Important Notes

1. **Same Teller App ID**: Use the same `app_pbvpiocruhfnvkhf1k000` for both dev and prod
2. **Sandbox Limitations**: 100 test connections total across all environments
3. **Webhook URLs**: Remember to switch webhook URLs when testing locally
4. **ngrok Stability**: ngrok URLs change each restart - update webhook URL accordingly
5. **Security**: Never commit `.env` files with real credentials

## 🎯 Quick Development Commands

```bash
# Start development environment
python render_deploy_setup.py  # Setup files
ngrok http 5000                 # Expose webhook
python app.py                   # Start Flask

# Test local webhook
curl -X POST http://localhost:5000/teller/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"test","data":{}}'
``` 
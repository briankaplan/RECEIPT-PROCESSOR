# 🔐 Teller Certificate Configuration Guide

## 🎯 **Current Problem**
Your bank connections work perfectly, but **transaction sync fails** with this error:
```
"Missing certificate: Retry request using your Teller client certificate."
```

## 📊 **Current Status**
- ✅ **3 Bank Connections Active** (stored in persistent memory)
- ✅ **Webhook System Working** (real-time notifications)
- ❌ **Transaction API Blocked** (requires SSL certificates)
- ⚠️ **Certificate Files**: Placeholder files created, need real certificates

## 🛠️ **Configuration Options**

### **Option 1: Use Real Banking Data (Recommended for Production)**

#### Step 1: Obtain Teller Client Certificates
```bash
# 📧 Contact Teller Support
Email: support@teller.io
Subject: SSL Client Certificate Request for Development Tier

Dear Teller Support,

I need SSL client certificates for my application to access the transaction API in development mode.

Application Details:
- Application ID: app_pbvpiocruhfnvkhf1k000
- Environment: Development (real banking data)
- Use Case: Receipt matching and expense tracking

Please provide:
1. Client certificate (.pem file)
2. Private key (.pem file)

Thank you!
```

#### Step 2: Replace Placeholder Certificates
```bash
# Replace these files with real certificates from Teller:
./credentials/teller_certificate.pem
./credentials/teller_private_key.pem
```

#### Step 3: Upload to Render.com
```bash
# In Render Dashboard:
1. Go to your service settings
2. Navigate to "Secret Files" 
3. Upload:
   - teller_certificate.pem → /etc/secrets/teller_certificate.pem
   - teller_private_key.pem → /etc/secrets/teller_private_key.pem
```

#### Step 4: Deploy with Development Mode
Your `render.yaml` is already configured for development mode:
```yaml
- key: TELLER_ENVIRONMENT
  value: development  # ✅ Already set correctly
- key: TELLER_CERT_PATH
  value: /etc/secrets/teller_certificate.pem  # ✅ Correct path
- key: TELLER_KEY_PATH
  value: /etc/secrets/teller_private_key.pem  # ✅ Correct path
```

---

### **Option 2: Use Sandbox Mode (Immediate Testing)**

#### Pros:
- ✅ **No certificates needed**
- ✅ **Immediate transaction testing**
- ✅ **Full API functionality**

#### Cons:
- ❌ **Fake transaction data only**
- ❌ **No real bank connections**

#### Implementation:
```bash
# Change render.yaml:
- key: TELLER_ENVIRONMENT
  value: sandbox  # Change from 'development'
```

---

### **Option 3: Webhook-Only Approach (Real-Time)**

#### How it Works:
- Real bank connections remain active
- Transactions arrive via webhook notifications
- No certificate polling needed

#### Implementation:
Your webhook is already configured:
```
URL: https://receipt-processor.onrender.com/teller/webhook
Status: ✅ Active
```

---

## 🚀 **Recommended Action Plan**

### **Immediate (Today):**
1. **Request certificates** from Teller support (email above)
2. **Test webhook system** - it should already be receiving real transactions
3. **Monitor persistent memory** - connections are safely stored

### **Once Certificates Arrive:**
1. **Replace placeholder files** with real certificates
2. **Upload to Render.com** secret files
3. **Redeploy application**
4. **Test transaction sync** - should work immediately

### **Alternative Quick Test:**
1. **Switch to sandbox mode** temporarily
2. **Test transaction sync functionality**
3. **Switch back when certificates arrive**

---

## 🔍 **Testing Your Configuration**

### Test Current Status:
```bash
# Run the certificate checker:
python setup_teller_certificates.py

# Test the app:
python app.py
# Visit: http://localhost:5000/status
```

### Test API Endpoints:
```bash
# Check bank connections:
curl https://receipt-processor.onrender.com/api/memory/connections

# Test transaction sync:
curl -X POST https://receipt-processor.onrender.com/api/sync-bank-transactions
```

---

## 📝 **Environment Variables Summary**

Your Render configuration is **perfectly set up** for development mode:

```yaml
✅ TELLER_APPLICATION_ID: app_pbvpiocruhfnvkhf1k000
✅ TELLER_ENVIRONMENT: development
✅ TELLER_API_URL: https://api.teller.io
✅ TELLER_WEBHOOK_URL: https://receipt-processor.onrender.com/teller/webhook
✅ TELLER_CERT_PATH: /etc/secrets/teller_certificate.pem
✅ TELLER_KEY_PATH: /etc/secrets/teller_private_key.pem
```

**Only missing**: Real certificate files uploaded to Render secret files.

---

## 🎉 **Expected Results**

### After Certificate Configuration:
- ✅ **Bank sync works perfectly** (2-30 seconds real sync time)
- ✅ **Real transaction data** from your connected banks
- ✅ **Intelligent receipt matching** with real expenses
- ✅ **Persistent memory** maintains all connections
- ✅ **Real-time webhooks** + **API polling** both working

### Current Workaround:
- ✅ **Webhook system active** - transactions arrive in real-time
- ✅ **Bank connections persistent** - no need to reconnect
- ⏳ **API polling waits** for certificates

---

## 📞 **Support Contacts**

- **Teller Support**: support@teller.io
- **Teller Docs**: https://teller.io/docs
- **Certificate Guide**: https://teller.io/docs/development-certificates

---

## 🚨 **Troubleshooting**

### Certificate Upload Issues:
1. Ensure `.pem` format (not `.crt` or `.key`)
2. Check file permissions (600)
3. Verify paths match environment variables

### Transaction Sync Still Fails:
1. Check Render logs for certificate errors
2. Verify certificate files are valid PEM format
3. Ensure development environment is selected

### Real-Time Alternative:
Your webhook system at `/teller/webhook` should already be receiving transactions in real-time, even without certificates! 

# 🚀 Render.com Deployment Instructions

## 1. Upload Secret Files

In your Render dashboard, go to your service and upload these files to "Secret Files":

- `kaplan_brian_gmail.pickle` (from ./render_secrets/kaplan_brian_gmail.pickle)
- `brian_downhome.pickle` (from ./render_secrets/brian_downhome.pickle)
- `brian_musiccityrodeo.pickle` (from ./render_secrets/brian_musiccityrodeo.pickle)
- `gmail_credentials.json` (from ./render_secrets/gmail_credentials.json)
- `service_account.json` (from ./render_secrets/service_account.json)
- `teller_certificate.pem` (from ./render_secrets/teller_certificate.pem)
- `teller_private_key.pem` (from ./render_secrets/teller_private_key.pem)


## 2. Environment Variables

All environment variables are already configured in render.yaml.

## 3. OAuth Configuration

### Google Cloud Console:
1. Go to https://console.cloud.google.com/apis/credentials
2. Edit your OAuth 2.0 Client ID  
3. Add these Authorized redirect URIs:
   - https://receipt-processor.onrender.com/oauth2callback
   - https://receipt-processor.onrender.com/gmail/oauth/callback
   - https://receipt-processor.onrender.com/auth/google/callback

### Teller Configuration:
1. Go to your Teller dashboard
2. Update redirect URI to: https://receipt-processor.onrender.com/teller/callback
3. Update webhook URL to: https://receipt-processor.onrender.com/teller/webhook

## 4. Deploy

1. Commit and push changes to GitHub
2. Render will auto-deploy from main branch
3. Check logs for any issues

## 5. Post-Deployment

1. Visit https://receipt-processor.onrender.com/status to check service health
2. Test Gmail authentication at https://receipt-processor.onrender.com/gmail/auth
3. Test Teller connection at https://receipt-processor.onrender.com/connect

## 🔧 Troubleshooting

### Gmail Issues:
- Verify redirect URIs in Google Cloud Console
- Check that secret files are uploaded correctly
- Ensure GOOGLE_APPLICATION_CREDENTIALS points to /etc/secrets/service_account.json

### Teller Issues:
- Verify SSL certificates are uploaded as secret files
- Check TELLER_CERT_PATH and TELLER_KEY_PATH point to /etc/secrets/
- Ensure redirect URI matches exactly in Teller dashboard

### General Issues:
- Check Render logs for detailed error messages
- Verify all environment variables are set correctly
- Test with /status endpoint first

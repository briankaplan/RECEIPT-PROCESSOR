# Security Configuration Guide

## Environment Variables Setup

### 1. Create Your Environment File

Copy the example environment file and customize it with your credentials:

```bash
cp env.example .env
```

### 2. Required Environment Variables

#### Gmail API Configuration
```env
GMAIL_ACCOUNT_1_EMAIL=your_email1@gmail.com
GMAIL_ACCOUNT_1_PICKLE_FILE=./gmail_tokens/account1.pickle
GMAIL_ACCOUNT_1_DISPLAY_NAME=Personal Gmail
GMAIL_ACCOUNT_1_ENABLED=true
GMAIL_ACCOUNT_1_PORT=8080

GMAIL_ACCOUNT_2_EMAIL=your_email2@domain.com
GMAIL_ACCOUNT_2_PICKLE_FILE=./gmail_tokens/account2.pickle
GMAIL_ACCOUNT_2_DISPLAY_NAME=Business Account
GMAIL_ACCOUNT_2_ENABLED=true
GMAIL_ACCOUNT_2_PORT=8081

GMAIL_ACCOUNT_3_EMAIL=your_email3@domain.com
GMAIL_ACCOUNT_3_PICKLE_FILE=./gmail_tokens/account3.pickle
GMAIL_ACCOUNT_3_DISPLAY_NAME=Second Business
GMAIL_ACCOUNT_3_ENABLED=true
GMAIL_ACCOUNT_3_PORT=8082
```

#### Database & Storage
```env
# MongoDB
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database_name
MONGODB_DATABASE=expense
MONGODB_COLLECTION=receipts

# Cloudflare R2 Storage
R2_ENDPOINT=https://your_account_id.r2.cloudflarestorage.com
R2_ACCESS_KEY=your_r2_access_key
R2_SECRET_KEY=your_r2_secret_key
R2_BUCKET=your_bucket_name
R2_PUBLIC_URL=https://your_public_url.r2.dev
```

#### API Keys
```env
# Google Services
GOOGLE_VISION_API_KEY=your_google_vision_api_key
GOOGLE_SHEETS_ID=your_google_sheets_id

# AI Processing
HUGGINGFACE_API_KEY=your_huggingface_api_key

# Banking Integration
TELLER_APPLICATION_ID=your_teller_app_id
TELLER_ENVIRONMENT=sandbox  # or production
TELLER_SIGNING_SECRET=your_signing_secret
```

### 3. Credential Files Setup

Create a `credentials/` directory structure:

```
credentials/
├── gmail_credentials.json      # Gmail OAuth credentials
├── google_credentials.json     # Google API credentials  
├── service_account.json        # Service account for server-to-server auth
├── teller_cert.pem            # Teller SSL certificate
└── teller_key.pem             # Teller SSL private key
```

### 4. Gmail Token Files

Create a `gmail_tokens/` directory for pickle files:

```
gmail_tokens/
├── account1.pickle
├── account2.pickle
└── account3.pickle
```

## Security Best Practices

### ✅ DO

1. **Use environment variables** for all sensitive data
2. **Store credentials in separate files** outside the code directory
3. **Use relative paths** starting with `./` 
4. **Rotate API keys regularly**
5. **Use least privilege access** for service accounts
6. **Enable 2FA** on all accounts
7. **Use different environments** (dev/staging/prod) with separate credentials

### ❌ DON'T

1. **Never commit `.env` files** to version control
2. **Never hardcode credentials** in source code
3. **Don't share credential files** via email or chat
4. **Don't use production credentials** in development
5. **Don't store credentials** in public repositories
6. **Don't use weak passwords** or API keys

## File Permissions

Set appropriate permissions for sensitive files:

```bash
# Environment file
chmod 600 .env

# Credential files
chmod 600 credentials/*.json
chmod 600 credentials/*.pem

# Token files
chmod 600 gmail_tokens/*.pickle
```

## Production Deployment

### Environment Variables in Production

For production deployments, set environment variables through your hosting platform:

#### Heroku
```bash
heroku config:set MONGODB_URI="mongodb+srv://..."
heroku config:set HUGGINGFACE_API_KEY="hf_..."
```

#### Docker
```bash
# Use docker-compose with env_file
docker-compose --env-file .env.production up
```

#### AWS/GCP/Azure
Use their respective secret management services:
- AWS Secrets Manager
- Google Secret Manager  
- Azure Key Vault

### SSL/TLS Configuration

For Teller API integration, ensure:

1. **Valid SSL certificates** are properly configured
2. **Certificate paths** are correct in environment variables
3. **Private keys** have proper permissions (600)

## Monitoring & Logging

1. **Monitor failed authentication attempts**
2. **Log API key usage** (without exposing keys)
3. **Set up alerts** for unusual access patterns
4. **Audit credential access** regularly

## Backup & Recovery

1. **Backup encryption keys** securely
2. **Store recovery codes** for 2FA accounts
3. **Document credential rotation procedures**
4. **Test backup restoration** regularly

## Compliance

Ensure compliance with:

- **PCI DSS** for payment card data
- **SOX** for financial data
- **GDPR/CCPA** for personal data
- **Bank regulations** for financial integrations

## Emergency Response

In case of credential compromise:

1. **Immediately rotate** all affected credentials
2. **Revoke access tokens** in all services
3. **Audit logs** for unauthorized access
4. **Update all deployment environments**
5. **Notify relevant stakeholders**

## Support

For security questions or incident reporting:
- Review this documentation first
- Check environment variable configuration
- Verify file permissions
- Test with minimal credentials first 
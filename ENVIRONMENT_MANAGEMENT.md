# Environment Management System

## Overview

The Receipt Processor now includes a comprehensive environment management system that allows you to easily switch between Teller environments (sandbox, development, production) directly from the web interface, with automatic Render.com deployment.

## Features

### 🎛️ Web-Based Settings Interface
- Access via `/settings` or the Settings button in the dashboard
- View current environment configuration
- Switch environments with a single click
- Deploy changes automatically to Render.com

### 🔄 Environment Modes

#### 🧪 Sandbox Environment
- **Purpose**: Testing with fake bank data
- **Webhook URL**: `https://receipt-processor.onrender.com/teller/webhook`
- **Features**:
  - ✅ Test transactions and fake data
  - ✅ No real bank connections
  - ✅ Unlimited testing
  - ✅ Perfect for development and QA

#### 🛠️ Development Environment  
- **Purpose**: Local development with ngrok tunneling
- **Webhook URL**: Custom ngrok URL (user-provided)
- **Features**:
  - ✅ Local Flask server testing
  - ✅ ngrok tunnel for webhook testing
  - ✅ Live webhook event testing
  - ✅ Debug mode enabled

#### 🚀 Production Environment
- **Purpose**: Live banking with real transactions
- **Webhook URL**: `https://receipt-processor.onrender.com/teller/webhook`
- **Features**:
  - ✅ Real bank account connections
  - ✅ Live transaction processing
  - ✅ Production security settings
  - ✅ Optimized performance

## How to Use

### 1. Web Interface (Recommended)

1. **Access Settings**:
   ```
   https://receipt-processor.onrender.com/settings
   ```

2. **Switch Environment**:
   - Select desired environment from dropdown
   - For development: Enter your ngrok URL
   - Click "Update Configuration"
   - Click "Deploy to Render" to apply changes

3. **Monitor Deployment**:
   - Check Render dashboard for deployment status
   - Changes are live within 2-3 minutes

### 2. Command Line Interface

```bash
# View current environment
python environment_manager.py info

# Switch to sandbox
python environment_manager.py switch --environment sandbox

# Switch to development with custom webhook
python environment_manager.py switch --environment development --webhook-url https://abc123.ngrok.io/teller/webhook

# Switch to production and auto-deploy
python environment_manager.py switch --environment production --deploy

# Deploy current configuration
python environment_manager.py deploy --message "Switch to production environment"
```

## No More Manual URL Changes! 🎉

### Before (Manual Process)
1. ❌ Manually edit `render.yaml`
2. ❌ Update Teller dashboard webhook URL
3. ❌ Manually commit and push changes
4. ❌ Wait for deployment
5. ❌ Verify configuration

### After (Automated Process)
1. ✅ Click environment in settings
2. ✅ Click "Deploy to Render"
3. ✅ Done! 🚀

## Technical Details

### Automatic Configuration Updates

When you switch environments, the system automatically updates:

- **render.yaml**: Environment variables for Render deployment
- **.env**: Local environment variables (if file exists)
- **Flask Environment**: Debug/production mode settings
- **Webhook URLs**: Automatically set based on environment

### Environment Variables Updated

| Variable | Sandbox | Development | Production |
|----------|---------|-------------|------------|
| `TELLER_ENVIRONMENT` | `sandbox` | `development` | `production` |
| `TELLER_WEBHOOK_URL` | render.com URL | ngrok URL | render.com URL |
| `FLASK_ENV` | `production` | `development` | `production` |
| `FLASK_DEBUG` | `false` | `true` | `false` |
| `DEBUG` | `false` | `true` | `false` |

### Git Integration

The system integrates with git for deployment:

```bash
# Automatic process when using "Deploy to Render"
git add render.yaml
git commit -m "Update environment configuration - sandbox"
git push origin main
```

## Teller Dashboard Configuration

### One-Time Setup Required

You still need to configure redirect URIs in your Teller dashboard:

1. **Production/Sandbox**: `https://receipt-processor.onrender.com/teller/callback`
2. **Development**: `http://localhost:5000/teller/callback` (or your ngrok URL)

### Webhook URLs (Automatic)

✅ **Webhook URLs are now automatically managed** - no manual updates needed!

- The system updates the webhook URL in `render.yaml`
- Render deployment applies the new webhook URL
- Your Teller app receives webhooks at the correct URL

## Development Workflow

### Local Development Setup

1. **Start ngrok tunnel**:
   ```bash
   ngrok http 5000
   ```

2. **Switch to development environment**:
   - Go to `/settings`
   - Select "Development (Local)"
   - Enter your ngrok URL: `https://abc123.ngrok.io/teller/webhook`
   - Click "Update Configuration"

3. **Start local server**:
   ```bash
   python app.py
   ```

4. **Test webhook events**:
   - Your local Flask app receives webhook events via ngrok
   - Debug and test in real-time

### Production Deployment

1. **Switch to production**:
   - Go to `/settings`
   - Select "Production (Live)"
   - Click "Update Configuration"
   - Click "Deploy to Render"

2. **Verify deployment**:
   - Check Render dashboard
   - Test `/status` endpoint
   - Verify Teller connection

## Troubleshooting

### Common Issues

**Environment not switching**:
- Check Render deployment logs
- Verify git push was successful
- Check render.yaml was updated

**Webhook not working**:
- Verify webhook URL in Render environment variables
- Check Teller dashboard webhook configuration
- Test webhook endpoint directly

**Local development issues**:
- Ensure ngrok is running
- Verify .env file was updated
- Check Flask debug mode is enabled

### Support Commands

```bash
# Check current configuration
curl https://receipt-processor.onrender.com/api/get-environment

# Test webhook endpoint
curl https://receipt-processor.onrender.com/teller/webhook

# View environment info
python environment_manager.py info
```

## Security Notes

### Credentials Management
- Environment switching only updates configuration, not credentials
- All API keys and secrets remain secure
- Webhook URLs are the only changing endpoints

### Best Practices
- Use sandbox for testing
- Use development for local debugging
- Use production only for live operations
- Always test in sandbox before production deployment

## Benefits

### For Developers
- 🚀 **Faster Development**: Switch environments in seconds
- 🔧 **Easy Testing**: No manual configuration needed
- 🎯 **Less Errors**: Automated configuration prevents mistakes
- 📱 **Better UX**: Web interface for non-technical users

### For Operations
- ⚡ **Quick Deployments**: Automated git integration
- 🛡️ **Consistent Configuration**: Standardized environment settings
- 📊 **Better Monitoring**: Clear environment status in dashboard
- 🔄 **Easy Rollbacks**: Simple environment switching

---

**Need help?** Check the settings page at `/settings` or run `python environment_manager.py --help` for more options. 
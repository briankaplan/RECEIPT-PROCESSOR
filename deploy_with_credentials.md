# 🚀 Credential Files Deployment Guide

## 📋 Base64 Files Ready for Upload

All credential files have been encoded to base64 format to prevent corruption during Render's secret file upload.

### 🔐 Files to Upload to Render Secret Files

**Delete these corrupted files from Render first:**
- `kaplan_brian_gmail.pickle` 
- `brian_downhome.pickle`
- `brian_musiccityrodeo.pickle`

**Upload these new base64 files to Render:**

| Local File | Upload as (Render Path) | Purpose |
|------------|-------------------------|---------|
| `kaplan_brian_gmail.b64` | `kaplan_brian_gmail.b64` | Gmail auth for kaplan.brian@gmail.com |
| `brian_downhome.b64` | `brian_downhome.b64` | Gmail auth for brian@downhome.com |
| `brian_musiccityrodeo.b64` | `brian_musiccityrodeo.b64` | Gmail auth for brian@musiccityrodeo.com |
| `teller_certificate.b64` | `teller_certificate.b64` | Teller SSL client certificate |
| `teller_private_key.b64` | `teller_private_key.b64` | Teller SSL private key |
| `service_account.b64` | `service_account.b64` | Google Sheets service account |
| `gmail_credentials.b64` | `gmail_credentials.b64` | Gmail API credentials |
| `google_credentials.b64` | `google_credentials.b64` | Google API credentials |

## ✅ Configuration Updated

The application now:
- ✅ **Supports base64 files**: Automatically detects and decodes base64 credential files
- ✅ **Backward compatible**: Still works with regular JSON/PEM files  
- ✅ **Git protected**: All .b64 files are in .gitignore
- ✅ **Render optimized**: Paths updated in render.yaml

## 🎯 Next Steps

1. **Delete old corrupted files** from Render Secret Files
2. **Upload the 8 base64 files** listed above
3. **Deploy** - the app will automatically handle decoding
4. **Test Gmail and Teller functionality** 

## 🔧 How It Works

The app now includes `load_credential_file()` function that:
- Detects if a file contains base64 content
- Automatically decodes base64 to original format
- Falls back to regular file loading if not base64
- Creates temporary files for SSL certificates as needed

## 🚨 Security Notes

- Base64 files are **NOT encrypted**, just encoded for safe upload
- All .b64 files are git-ignored to prevent accidental commits
- Temporary certificate files are automatically cleaned up
- Original credential files remain untouched in local development

This ensures your Gmail authentication and Teller bank connections will work properly! 
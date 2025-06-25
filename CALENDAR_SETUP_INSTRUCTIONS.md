# 📅 Calendar Integration Setup Guide

## Overview
The system uses Google Calendar API with OAuth2 service account authentication to access brian@downhome.com calendar for intelligent expense context matching.

## Current Status
- ✅ OAuth2 service account credentials loaded
- ✅ Calendar service connected successfully  
- ⚠️ Calendar access: 0 calendars found (sharing not configured)
- 🔧 Setup required: Calendar sharing with service account

## Service Account Details
- **Service Account Email**: `exp2-757@expenses-52877.iam.gserviceaccount.com`
- **Credentials File**: `credentials/service-acct-dh.json`
- **Scopes**: `https://www.googleapis.com/auth/calendar.readonly`

## Required Setup Steps

### Step 1: Share Calendar with Service Account
1. **Go to Google Calendar**: https://calendar.google.com
2. **Login as brian@downhome.com**
3. **Navigate to Settings**:
   - Click the gear icon (⚙️) in top right
   - Select "Settings"
4. **Find Calendar Settings**:
   - In left sidebar, click "Settings for my calendars"
   - Click on "brian@downhome.com" calendar
5. **Share Calendar**:
   - Scroll to "Share with specific people or groups"
   - Click "Add people and groups"
   - Enter: `exp2-757@expenses-52877.iam.gserviceaccount.com`
   - Set permission: **"See all event details"**
   - Click "Send"

### Step 2: Verify Calendar Access
After sharing the calendar, restart the application and check:

```bash
# Check calendar health
curl http://localhost:10000/api/calendar/health

# Test calendar sync
curl -X POST -H "Content-Type: application/json" \
     -d '{}' \
     http://localhost:10000/api/calendar/sync-events
```

### Step 3: Monitor Logs
Watch the application logs for confirmation:
```bash
# Should see messages like:
# "✅ Google Calendar service initialized with OAuth2"
# "📧 Service account email: exp2-757@expenses-52877.iam.gserviceaccount.com"
# "📅 Found 1 accessible calendars"
```

## Alternative Setup Options

### Option A: OAuth2 User Authentication
If service account sharing doesn't work, we can switch to OAuth2 user authentication:
1. Setup OAuth2 consent screen in Google Cloud Console
2. Create OAuth2 client credentials
3. Implement user authentication flow

### Option B: Make Calendar Public
If comfortable with public access:
1. In calendar settings, make calendar public
2. Use "Make available to public" option
3. Service account will be able to access without sharing

## Expected Benefits Once Configured

### Intelligent Expense Context
- **Travel Detection**: Automatically identify business trips and conferences
- **Meeting Context**: Match restaurant expenses with business meetings
- **Location Intelligence**: Correlate expenses with calendar locations
- **Time-Based Analysis**: Understand spending patterns around events

### Smart Categorization
The system will analyze calendar events to:
- Identify business vs personal expenses
- Detect travel-related costs
- Match client meetings with meal expenses
- Provide context for expense reports

## Troubleshooting

### Common Issues
1. **"No calendars accessible"**: Calendar not shared with service account
2. **"Permission denied"**: Insufficient sharing permissions
3. **"Not Found"**: Wrong service account email or calendar ID

### Debug Commands
```bash
# Test basic calendar connectivity
curl http://localhost:10000/api/calendar/health

# Check calendar sync with debug info
curl -X POST -H "Content-Type: application/json" \
     -d '{"days_back": 7}' \
     http://localhost:10000/api/calendar/sync-events
```

## Next Steps
1. Complete the calendar sharing setup above
2. Restart the application to test access
3. Verify calendar events are being synced
4. Test expense categorization with calendar context

Once configured, the system will provide significantly more intelligent expense analysis by correlating financial transactions with calendar events and business context.

## Support Commands

### Check Calendar Status
```bash
curl http://localhost:10000/api/calendar/health
```

### Test Calendar Sync
```bash
curl -X POST http://localhost:10000/api/calendar/sync-events
```

### View Service Account Email
```bash
cat credentials/service-acct-dh.json | grep client_email
``` 
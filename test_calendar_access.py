#!/usr/bin/env python3
"""
Test Calendar Access
Verifies that the calendar integration is working after access was granted
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_calendar_access():
    """Test calendar access and integration"""
    print("📅 Testing Calendar Access")
    print("=" * 50)
    
    try:
        from app import create_app
        app = create_app()
        
        # Test calendar health endpoint
        with app.test_client() as client:
            response = client.get('/api/calendar/health')
            if response.status_code == 200:
                data = response.get_json()
                print("✅ Calendar health endpoint working")
                print(f"   Status: {data.get('status', 'Unknown')}")
                print(f"   Calendars found: {data.get('calendars_count', 0)}")
                print(f"   Service account: {data.get('service_account_email', 'Unknown')}")
                
                if data.get('calendars_count', 0) > 0:
                    print("🎉 Calendar access is working!")
                    return True
                else:
                    print("⚠️ No calendars accessible - may need to share calendar")
                    return False
            else:
                print(f"❌ Calendar health endpoint failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Calendar test failed: {e}")
        return False

def test_calendar_debug():
    """Test calendar debug endpoint for more details"""
    print("\n🔍 Calendar Debug Information")
    print("=" * 50)
    
    try:
        from app import create_app
        app = create_app()
        
        with app.test_client() as client:
            response = client.get('/api/calendar/debug')
            if response.status_code == 200:
                data = response.get_json()
                print("✅ Calendar debug endpoint working")
                print(f"   Service account: {data.get('service_account_email', 'Unknown')}")
                print(f"   Calendars accessible: {len(data.get('accessible_calendars', []))}")
                
                calendars = data.get('accessible_calendars', [])
                if calendars:
                    print("📋 Accessible calendars:")
                    for cal in calendars:
                        print(f"   - {cal.get('summary', 'Unknown')} ({cal.get('id', 'Unknown')})")
                else:
                    print("⚠️ No calendars accessible")
                    
                return len(calendars) > 0
            else:
                print(f"❌ Calendar debug endpoint failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Calendar debug test failed: {e}")
        return False

def main():
    """Run calendar tests"""
    print("🧪 CALENDAR ACCESS TEST")
    print("=" * 60)
    
    # Test basic calendar access
    health_ok = test_calendar_access()
    
    # Test detailed calendar information
    debug_ok = test_calendar_debug()
    
    print("\n" + "=" * 60)
    if health_ok and debug_ok:
        print("✅ Calendar access is fully working!")
        print("🎉 You can now use calendar context for expense analysis")
    elif health_ok:
        print("⚠️ Calendar access partially working - check debug info")
    else:
        print("❌ Calendar access needs attention")
        print("\n💡 To fix calendar access:")
        print("   1. Go to https://calendar.google.com")
        print("   2. Open Settings > Calendars > brian@downhome.com")
        print("   3. Share with: expense-86@music-city-rodeo.iam.gserviceaccount.com")
        print("   4. Grant 'See all event details' permission")

if __name__ == "__main__":
    main() 
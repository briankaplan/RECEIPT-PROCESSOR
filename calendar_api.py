"""
Calendar Context API - Flask Blueprint
Integration endpoints for calendar-based expense context analysis
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import Blueprint, request, jsonify

# Import calendar analyzer
try:
    from calendar_context_analyzer import CalendarContextAnalyzer, CalendarEvent, TravelEvent, ContextMatch
    CALENDAR_ANALYZER_AVAILABLE = True
except ImportError:
    CALENDAR_ANALYZER_AVAILABLE = False
    logging.warning("Calendar Context Analyzer not available")

logger = logging.getLogger(__name__)

# Create Flask Blueprint
calendar_bp = Blueprint('calendar', __name__, url_prefix='/api/calendar')

# Global analyzer instance
calendar_analyzer = None

def init_calendar_analyzer():
    """Initialize calendar analyzer"""
    global calendar_analyzer
    if CALENDAR_ANALYZER_AVAILABLE and calendar_analyzer is None:
        try:
            calendar_analyzer = CalendarContextAnalyzer()
            logger.info("📅 Calendar analyzer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize calendar analyzer: {e}")

@calendar_bp.route('/health', methods=['GET'])
def calendar_health():
    """Check calendar service health"""
    try:
        init_calendar_analyzer()
        
        status = {
            "calendar_analyzer_available": CALENDAR_ANALYZER_AVAILABLE,
            "calendar_service_connected": False,
            "credentials_found": False
        }
        
        if calendar_analyzer:
            # Check if credentials exist
            credentials_path = calendar_analyzer.credentials_path
            status["credentials_found"] = os.path.exists(credentials_path)
            status["calendar_service_connected"] = calendar_analyzer.calendar_service is not None
        
        return jsonify({
            "status": "healthy" if status["calendar_analyzer_available"] else "limited",
            "details": status,
            "message": "Calendar context analysis ready" if status["calendar_analyzer_available"] else "Calendar features limited"
        })
        
    except Exception as e:
        logger.error(f"Calendar health check failed: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@calendar_bp.route('/debug', methods=['GET'])
def calendar_debug():
    """Debug calendar access with comprehensive testing"""
    try:
        init_calendar_analyzer()
        
        if not calendar_analyzer or not calendar_analyzer.calendar_service:
            return jsonify({
                "error": "Calendar service not available",
                "details": "Calendar analyzer or service not initialized"
            }), 500
        
        debug_info = {
            "service_account_email": getattr(calendar_analyzer, 'service_account_email', 'Unknown'),
            "credentials_path": calendar_analyzer.credentials_path,
            "primary_calendar_id": calendar_analyzer.primary_calendar_id,
            "calendar_tests": [],
            "accessible_calendars": [],
            "alternative_access_results": []
        }
        
        # Test 1: List all accessible calendars
        try:
            calendar_list = calendar_analyzer.calendar_service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            debug_info["accessible_calendars"] = []
            
            for calendar in calendars:
                debug_info["accessible_calendars"].append({
                    "id": calendar.get('id', 'Unknown'),
                    "summary": calendar.get('summary', 'No summary'),
                    "accessRole": calendar.get('accessRole', 'Unknown'),
                    "selected": calendar.get('selected', False),
                    "primary": calendar.get('primary', False)
                })
                
        except Exception as e:
            debug_info["calendar_list_error"] = str(e)
        
        # Test 2: Try direct calendar access
        calendar_ids_to_test = [
            calendar_analyzer.primary_calendar_id,
            'primary',
            'brian@downhome.com',
            'YnJpYW5AZG93bmhvbWUuY29t'  # Base64 encoded version
        ]
        
        for calendar_id in calendar_ids_to_test:
            test_result = {
                "calendar_id": calendar_id,
                "calendar_info": None,
                "events_sample": None,
                "error": None,
                "access_role": None
            }
            
            try:
                # Test calendar metadata
                calendar_info = calendar_analyzer.calendar_service.calendars().get(
                    calendarId=calendar_id
                ).execute()
                test_result["calendar_info"] = {
                    "summary": calendar_info.get('summary', 'No summary'),
                    "description": calendar_info.get('description', 'No description'),
                    "timeZone": calendar_info.get('timeZone', 'Unknown'),
                    "accessRole": calendar_info.get('accessRole', 'Unknown'),
                    "id": calendar_info.get('id', 'Unknown')
                }
                
                # Test event access
                from datetime import datetime, timedelta
                now = datetime.utcnow()
                time_min = (now - timedelta(days=30)).isoformat() + 'Z'
                time_max = (now + timedelta(days=7)).isoformat() + 'Z'
                
                events_result = calendar_analyzer.calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=5,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                test_result["events_sample"] = {
                    "count": len(events),
                    "events": []
                }
                
                for event in events[:3]:
                    event_info = {
                        "summary": event.get('summary', 'No title'),
                        "start": event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'No time')),
                        "end": event.get('end', {}).get('dateTime', event.get('end', {}).get('date', 'No time'))
                    }
                    test_result["events_sample"]["events"].append(event_info)
                
            except Exception as e:
                test_result["error"] = str(e)
            
            debug_info["calendar_tests"].append(test_result)
        
        # Test 3: Try alternative access methods
        try:
            # Try calendar list with different parameters
            alt_calendar_list = calendar_analyzer.calendar_service.calendarList().list(
                showDeleted=False,
                showHidden=False
            ).execute()
            alt_calendars = alt_calendar_list.get('items', [])
            debug_info["alternative_access_results"] = {
                "method": "calendarList with showDeleted=False",
                "calendars_found": len(alt_calendars),
                "calendar_ids": [cal.get('id') for cal in alt_calendars]
            }
        except Exception as e:
            debug_info["alternative_access_error"] = str(e)
        
        return jsonify({
            "success": True,
            "debug_info": debug_info,
            "summary": {
                "accessible_calendars_count": len(debug_info["accessible_calendars"]),
                "successful_calendar_tests": len([t for t in debug_info["calendar_tests"] if not t["error"]]),
                "service_account": debug_info["service_account_email"]
            }
        })
        
    except Exception as e:
        logger.error(f"Calendar debug failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@calendar_bp.route('/sync-events', methods=['POST'])
def sync_calendar_events():
    """Sync calendar events and analyze business context"""
    try:
        init_calendar_analyzer()
        
        if not calendar_analyzer:
            return jsonify({
                "error": "Calendar analyzer not available",
                "synced_events": 0
            }), 400
        
        # Handle both JSON and form data to prevent 415 errors
        if request.is_json and request.get_json():
            data = request.get_json()
        elif request.form:
            data = request.form.to_dict()
        else:
            data = {}
        
        days_back = int(data.get('days_back', 30))
        days_forward = int(data.get('days_forward', 30))
        
        # Sync events
        events = calendar_analyzer.sync_calendar_events(days_back, days_forward)
        
        # Convert events to JSON serializable format
        events_data = []
        for event in events:
            events_data.append({
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
                "location": event.location,
                "attendees": event.attendees,
                "event_type": event.event_type,
                "business_context": event.business_context,
                "confidence": event.confidence,
                "related_expenses": event.related_expenses
            })
        
        # Identify travel events
        travel_events = calendar_analyzer.identify_travel_events(events)
        travel_data = []
        for travel in travel_events:
            travel_data.append({
                "id": travel.id,
                "destination": travel.destination,
                "departure_date": travel.departure_date.isoformat(),
                "return_date": travel.return_date.isoformat(),
                "purpose": travel.purpose,
                "business_type": travel.business_type,
                "transportation_mode": travel.transportation_mode,
                "accommodation": travel.accommodation,
                "related_meetings": travel.related_meetings,
                "expected_expenses": travel.expected_expenses
            })
        
        return jsonify({
            "synced_events": len(events),
            "business_events": len([e for e in events if e.business_context in ["down_home", "mcr", "mixed"]]),
            "travel_events": len(travel_events),
            "events": events_data,
            "travel": travel_data,
            "message": f"Successfully synced {len(events)} calendar events"
        })
        
    except Exception as e:
        logger.error(f"Calendar sync failed: {e}")
        return jsonify({
            "error": f"Calendar sync failed: {str(e)}",
            "synced_events": 0
        }), 500

@calendar_bp.route('/match-expenses', methods=['POST'])
def match_expenses_to_calendar():
    """Match expenses to calendar events for contextual analysis"""
    try:
        init_calendar_analyzer()
        
        if not calendar_analyzer:
            return jsonify({
                "error": "Calendar analyzer not available",
                "matches": []
            }), 400
        
        data = request.get_json()
        if not data or 'expenses' not in data:
            return jsonify({
                "error": "No expenses provided",
                "matches": []
            }), 400
        
        expenses = data['expenses']
        
        # Get calendar events (sync if needed)
        days_back = data.get('days_back', 7)
        days_forward = data.get('days_forward', 7)
        
        calendar_events = calendar_analyzer.sync_calendar_events(days_back, days_forward)
        
        # Match expenses to calendar events
        matches = calendar_analyzer.match_expenses_to_calendar(expenses, calendar_events)
        
        # Convert matches to JSON format
        matches_data = []
        for match in matches:
            matches_data.append({
                "expense_id": match.expense_id,
                "event_id": match.event_id,
                "match_type": match.match_type,
                "confidence": match.confidence,
                "context_explanation": match.context_explanation,
                "business_justification": match.business_justification
            })
        
        # Generate insights
        insights = calendar_analyzer.generate_calendar_insights(calendar_events, matches)
        
        return jsonify({
            "total_expenses": len(expenses),
            "matched_expenses": len(matches),
            "high_confidence_matches": len([m for m in matches if m.confidence > 0.7]),
            "matches": matches_data,
            "insights": insights,
            "message": f"Found {len(matches)} expense-calendar matches"
        })
        
    except Exception as e:
        logger.error(f"Expense matching failed: {e}")
        return jsonify({
            "error": f"Expense matching failed: {str(e)}",
            "matches": []
        }), 500

@calendar_bp.route('/analyze-expense', methods=['POST'])
def analyze_expense_with_calendar():
    """Analyze a single expense with calendar context"""
    try:
        init_calendar_analyzer()
        
        if not calendar_analyzer:
            return jsonify({
                "error": "Calendar analyzer not available",
                "analysis": None
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                "error": "No expense data provided",
                "analysis": None
            }), 400
        
        # Get expense details
        expense = {
            "id": data.get('id', ''),
            "merchant": data.get('merchant', ''),
            "amount": data.get('amount', 0),
            "date": data.get('date', ''),
            "description": data.get('description', '')
        }
        
        # Get calendar events around expense date
        try:
            expense_date = datetime.fromisoformat(expense['date'].replace('Z', '+00:00'))
        except:
            expense_date = datetime.now()
        
        # Sync events around expense date
        calendar_events = calendar_analyzer.sync_calendar_events(days_back=2, days_forward=2)
        
        # Find relevant events
        relevant_events = [
            event for event in calendar_events
            if abs((event.start_time.date() - expense_date.date()).days) <= 1
        ]
        
        # Calculate matches
        matches = calendar_analyzer.match_expenses_to_calendar([expense], relevant_events)
        
        # Prepare response
        analysis = {
            "expense": expense,
            "expense_date": expense_date.isoformat(),
            "relevant_events": len(relevant_events),
            "matches": len(matches),
            "best_match": None,
            "business_context": "unknown",
            "confidence": 0.0,
            "recommendations": []
        }
        
        if matches:
            best_match = max(matches, key=lambda m: m.confidence)
            analysis["best_match"] = {
                "event_id": best_match.event_id,
                "match_type": best_match.match_type,
                "confidence": best_match.confidence,
                "explanation": best_match.context_explanation,
                "justification": best_match.business_justification
            }
            
            # Find the matching event
            matching_event = next((e for e in relevant_events if e.id == best_match.event_id), None)
            if matching_event:
                analysis["business_context"] = matching_event.business_context
                analysis["confidence"] = best_match.confidence
        
        # Generate recommendations
        if analysis["confidence"] > 0.7:
            analysis["recommendations"].append("High confidence calendar match - expense likely business related")
        elif analysis["confidence"] > 0.3:
            analysis["recommendations"].append("Possible calendar correlation - review for business context")
        else:
            analysis["recommendations"].append("No strong calendar correlation - check if personal expense")
        
        return jsonify({
            "analysis": analysis,
            "message": f"Analyzed expense with {len(relevant_events)} calendar events"
        })
        
    except Exception as e:
        logger.error(f"Expense analysis failed: {e}")
        return jsonify({
            "error": f"Expense analysis failed: {str(e)}",
            "analysis": None
        }), 500

@calendar_bp.route('/business-context/<context_type>', methods=['GET'])
def get_business_context_events(context_type):
    """Get calendar events by business context"""
    try:
        init_calendar_analyzer()
        
        if not calendar_analyzer:
            return jsonify({
                "error": "Calendar analyzer not available",
                "events": []
            }), 400
        
        # Validate context type
        valid_contexts = ["down_home", "mcr", "personal", "mixed", "all"]
        if context_type not in valid_contexts:
            return jsonify({
                "error": f"Invalid context type. Must be one of: {valid_contexts}",
                "events": []
            }), 400
        
        # Get date range from query params
        days_back = request.args.get('days_back', 30, type=int)
        days_forward = request.args.get('days_forward', 30, type=int)
        
        # Sync events
        all_events = calendar_analyzer.sync_calendar_events(days_back, days_forward)
        
        # Filter by business context
        if context_type == "all":
            filtered_events = all_events
        else:
            filtered_events = [e for e in all_events if e.business_context == context_type]
        
        # Convert to JSON format
        events_data = []
        for event in filtered_events:
            events_data.append({
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
                "location": event.location,
                "attendees": event.attendees,
                "event_type": event.event_type,
                "business_context": event.business_context,
                "confidence": event.confidence
            })
        
        return jsonify({
            "context_type": context_type,
            "total_events": len(events_data),
            "date_range": {
                "days_back": days_back,
                "days_forward": days_forward
            },
            "events": events_data,
            "message": f"Found {len(events_data)} events for {context_type} context"
        })
        
    except Exception as e:
        logger.error(f"Business context query failed: {e}")
        return jsonify({
            "error": f"Business context query failed: {str(e)}",
            "events": []
        }), 500

@calendar_bp.route('/travel-analysis', methods=['GET'])
def get_travel_analysis():
    """Get comprehensive travel analysis"""
    try:
        init_calendar_analyzer()
        
        if not calendar_analyzer:
            return jsonify({
                "error": "Calendar analyzer not available",
                "travel_analysis": {}
            }), 400
        
        # Get date range from query params
        days_back = request.args.get('days_back', 60, type=int)
        days_forward = request.args.get('days_forward', 60, type=int)
        
        # Sync events
        calendar_events = calendar_analyzer.sync_calendar_events(days_back, days_forward)
        
        # Identify travel events
        travel_events = calendar_analyzer.identify_travel_events(calendar_events)
        
        # Analyze travel patterns
        travel_analysis = {
            "total_travel_events": len(travel_events),
            "business_travel": len([t for t in travel_events if t.purpose == "business"]),
            "personal_travel": len([t for t in travel_events if t.purpose == "personal"]),
            "destinations": {},
            "transportation_modes": {},
            "business_type_breakdown": {},
            "upcoming_travel": [],
            "recent_travel": [],
            "expected_expenses_summary": []
        }
        
        now = datetime.now()
        
        for travel in travel_events:
            # Destination tracking
            dest = travel.destination
            if dest not in travel_analysis["destinations"]:
                travel_analysis["destinations"][dest] = 0
            travel_analysis["destinations"][dest] += 1
            
            # Transportation mode tracking
            mode = travel.transportation_mode
            if mode not in travel_analysis["transportation_modes"]:
                travel_analysis["transportation_modes"][mode] = 0
            travel_analysis["transportation_modes"][mode] += 1
            
            # Business type breakdown
            btype = travel.business_type
            if btype not in travel_analysis["business_type_breakdown"]:
                travel_analysis["business_type_breakdown"][btype] = 0
            travel_analysis["business_type_breakdown"][btype] += 1
            
            # Upcoming vs recent travel
            travel_data = {
                "id": travel.id,
                "destination": travel.destination,
                "departure_date": travel.departure_date.isoformat(),
                "return_date": travel.return_date.isoformat(),
                "purpose": travel.purpose,
                "business_type": travel.business_type,
                "transportation_mode": travel.transportation_mode,
                "expected_expenses": travel.expected_expenses
            }
            
            if travel.departure_date > now:
                travel_analysis["upcoming_travel"].append(travel_data)
            else:
                travel_analysis["recent_travel"].append(travel_data)
            
            # Collect unique expected expenses
            for expense_type in travel.expected_expenses:
                if expense_type not in travel_analysis["expected_expenses_summary"]:
                    travel_analysis["expected_expenses_summary"].append(expense_type)
        
        # Sort travel by date
        travel_analysis["upcoming_travel"].sort(key=lambda x: x["departure_date"])
        travel_analysis["recent_travel"].sort(key=lambda x: x["departure_date"], reverse=True)
        
        return jsonify({
            "travel_analysis": travel_analysis,
            "message": f"Analyzed {len(travel_events)} travel events"
        })
        
    except Exception as e:
        logger.error(f"Travel analysis failed: {e}")
        return jsonify({
            "error": f"Travel analysis failed: {str(e)}",
            "travel_analysis": {}
        }), 500

@calendar_bp.route('/insights', methods=['GET'])
def get_calendar_insights():
    """Get comprehensive calendar and expense insights"""
    try:
        init_calendar_analyzer()
        
        if not calendar_analyzer:
            return jsonify({
                "error": "Calendar analyzer not available",
                "insights": {}
            }), 400
        
        # Get date range from query params
        days_back = request.args.get('days_back', 30, type=int)
        days_forward = request.args.get('days_forward', 30, type=int)
        
        # Sync events
        calendar_events = calendar_analyzer.sync_calendar_events(days_back, days_forward)
        
        # For demonstration, create empty matches (would normally come from expense matching)
        matches = []
        
        # Generate insights
        insights = calendar_analyzer.generate_calendar_insights(calendar_events, matches)
        
        # Add additional insights
        insights["date_range"] = {
            "days_back": days_back,
            "days_forward": days_forward,
            "start_date": (datetime.now() - timedelta(days=days_back)).isoformat(),
            "end_date": (datetime.now() + timedelta(days=days_forward)).isoformat()
        }
        
        # Event type breakdown
        event_types = {}
        for event in calendar_events:
            etype = event.event_type
            if etype not in event_types:
                event_types[etype] = 0
            event_types[etype] += 1
        insights["event_type_breakdown"] = event_types
        
        # Business productivity insights
        business_events = [e for e in calendar_events if e.business_context in ["down_home", "mcr", "mixed"]]
        insights["business_productivity"] = {
            "total_business_events": len(business_events),
            "business_percentage": (len(business_events) / len(calendar_events) * 100) if calendar_events else 0,
            "avg_events_per_day": len(calendar_events) / max(days_back + days_forward, 1),
            "most_active_business": max(insights["business_context_breakdown"].items(), key=lambda x: x[1])[0] if insights["business_context_breakdown"] else "none"
        }
        
        return jsonify({
            "insights": insights,
            "message": f"Generated insights from {len(calendar_events)} calendar events"
        })
        
    except Exception as e:
        logger.error(f"Insights generation failed: {e}")
        return jsonify({
            "error": f"Insights generation failed: {str(e)}",
            "insights": {}
        }), 500

def register_calendar_blueprint(app):
    """Register calendar blueprint with Flask app"""
    app.register_blueprint(calendar_bp)
    logger.info("📅 Calendar API blueprint registered")

# Initialize when imported
if CALENDAR_ANALYZER_AVAILABLE:
    init_calendar_analyzer() 
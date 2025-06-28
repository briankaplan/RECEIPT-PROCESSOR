#!/usr/bin/env python3
"""
Calendar Intelligence Module
Advanced calendar integration for business context analysis
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import base64
import pickle

# Google Calendar API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class CalendarEvent:
    """Calendar event with business context"""
    event_id: str
    title: str
    start_time: datetime
    end_time: datetime
    location: str
    attendees: List[str]
    description: str
    business_type: str
    event_type: str
    travel_expected: bool
    expense_context: Dict

@dataclass
class BusinessContext:
    """Business context derived from calendar"""
    is_business_day: bool
    active_projects: List[str]
    meeting_context: str
    travel_status: str
    business_type: str
    expense_justification: str

class CalendarIntelligence:
    """
    Advanced calendar intelligence for expense context
    """
    
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        self.service = None
        self.connected = False
        self.calendars = []
        self.business_patterns = self._load_business_patterns()
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Calendar service"""
        try:
            if not GOOGLE_CALENDAR_AVAILABLE:
                logger.warning("⚠️ Google Calendar API not available")
                return
            
            creds = self._load_credentials()
            if creds:
                self.service = build('calendar', 'v3', credentials=creds)
                self.connected = True
                self._load_calendars()
                logger.info("📅 Calendar Intelligence initialized successfully")
            else:
                logger.warning("⚠️ Calendar credentials not found")
                
        except Exception as e:
            logger.error(f"❌ Calendar initialization failed: {e}")
            self.connected = False
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load Google Calendar credentials using existing OAuth tokens"""
        # Use the same OAuth credentials as Gmail for brian@downhome.com
        token_paths = [
            '/etc/secrets/brian_downhome.b64',  # Render deployment
            'gmail_tokens/brian_downhome.pickle',  # Local development
            os.getenv('GMAIL_ACCOUNT_2_PICKLE_FILE', '/etc/secrets/brian_downhome.b64')  # Environment variable
        ]
        
        for token_path in token_paths:
            if token_path and os.path.exists(token_path):
                try:
                    logger.info(f"🔄 Loading calendar credentials from: {token_path}")
                    
                    # Handle base64-encoded pickle files (Render deployment)
                    if token_path.endswith('.b64'):
                        with open(token_path, 'r') as f:
                            base64_data = f.read().strip()
                            decoded_data = base64.b64decode(base64_data)
                            creds = pickle.loads(decoded_data)
                        logger.info(f"✅ Loaded base64-encoded credentials from {token_path}")
                    else:
                        # Handle regular pickle files (local development)
                        with open(token_path, 'rb') as f:
                            creds = pickle.load(f)
                        logger.info(f"✅ Loaded regular pickle credentials from {token_path}")
                    
                    # Refresh expired credentials first
                    if creds and creds.expired and creds.refresh_token:
                        try:
                            creds.refresh(Request())
                            logger.info(f"✅ Refreshed expired credentials from {token_path}")
                        except Exception as refresh_error:
                            logger.error(f"❌ Failed to refresh credentials: {refresh_error}")
                            continue
                    
                    # Add calendar scope to existing credentials
                    if creds and creds.valid:
                        # Get existing scopes
                        existing_scopes = getattr(creds, 'scopes', [])
                        logger.info(f"📋 Existing scopes: {existing_scopes}")
                        
                        # Add calendar scopes if not present
                        calendar_scopes = self.scopes
                        all_scopes = list(set(existing_scopes + calendar_scopes))
                        
                        if calendar_scopes[0] not in existing_scopes:
                            logger.info(f"➕ Adding calendar scopes: {calendar_scopes}")
                            # Create new credentials with extended scopes
                            creds = Credentials(
                                token=creds.token,
                                refresh_token=creds.refresh_token,
                                token_uri=creds.token_uri,
                                client_id=creds.client_id,
                                client_secret=creds.client_secret,
                                scopes=all_scopes
                            )
                            logger.info(f"✅ Created credentials with calendar access")
                        else:
                            logger.info(f"✅ Calendar scopes already present")
                        
                        logger.info(f"✅ Calendar credentials ready for {token_path}")
                        return creds
                        
                except Exception as e:
                    logger.warning(f"Failed to load credentials from {token_path}: {e}")
                    continue
        
        logger.warning("⚠️ No valid calendar credentials found")
        return None
    
    def _load_calendars(self):
        """Load available calendars"""
        try:
            if not self.service:
                return
            
            calendars_result = self.service.calendarList().list().execute()
            calendars = calendars_result.get('items', [])
            
            for calendar in calendars:
                self.calendars.append({
                    'id': calendar['id'],
                    'name': calendar['summary'],
                    'primary': calendar.get('primary', False),
                    'business_type': self._classify_calendar_business_type(calendar['summary'])
                })
            
            logger.info(f"📅 Loaded {len(self.calendars)} calendars")
            
        except Exception as e:
            logger.error(f"❌ Failed to load calendars: {e}")
    
    def _classify_calendar_business_type(self, calendar_name: str) -> str:
        """Classify calendar by business type"""
        name_lower = calendar_name.lower()
        
        if any(keyword in name_lower for keyword in ['down home', 'video', 'production']):
            return 'Down Home'
        elif any(keyword in name_lower for keyword in ['music city', 'rodeo', 'mcr', 'music']):
            return 'Music City Rodeo'
        elif any(keyword in name_lower for keyword in ['personal', 'private', 'family']):
            return 'Personal'
        else:
            return 'Business'
    
    def _load_business_patterns(self) -> Dict:
        """Load business patterns for context analysis"""
        return {
            'down_home_keywords': [
                'client', 'video', 'production', 'shoot', 'edit', 'meeting',
                'proposal', 'project', 'delivery', 'review', 'consultation'
            ],
            'mcr_keywords': [
                'rodeo', 'event', 'venue', 'artist', 'performance', 'sound check',
                'rehearsal', 'booking', 'contract', 'music', 'stage'
            ],
            'travel_indicators': [
                'flight', 'hotel', 'airport', 'travel', 'trip', 'visit',
                'location', 'drive to', 'meeting at', 'conference'
            ],
            'meal_contexts': [
                'lunch', 'dinner', 'breakfast', 'coffee', 'meeting',
                'client', 'business', 'discussion', 'proposal'
            ]
        }
    
    def get_business_context(self, date: datetime, time_window_hours: int = 6) -> BusinessContext:
        """Get business context for a specific date and time"""
        try:
            if not self.connected:
                return self._fallback_business_context(date)
            
            # Get events around the specified time
            start_time = date - timedelta(hours=time_window_hours)
            end_time = date + timedelta(hours=time_window_hours)
            
            events = self._get_events_in_range(start_time, end_time)
            
            if not events:
                return BusinessContext(
                    is_business_day=self._is_business_day(date),
                    active_projects=[],
                    meeting_context="No meetings found",
                    travel_status="No travel",
                    business_type="Unknown",
                    expense_justification="General business expense"
                )
            
            # Analyze events for business context
            return self._analyze_events_for_context(events, date)
            
        except Exception as e:
            logger.error(f"❌ Failed to get business context: {e}")
            return self._fallback_business_context(date)
    
    def _get_events_in_range(self, start_time: datetime, end_time: datetime) -> List[CalendarEvent]:
        """Get calendar events in specified time range"""
        try:
            events = []
            
            for calendar in self.calendars:
                calendar_id = calendar['id']
                
                events_result = self.service.events().list(
                    calendarId=calendar_id,
                    timeMin=start_time.isoformat() + 'Z',
                    timeMax=end_time.isoformat() + 'Z',
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                calendar_events = events_result.get('items', [])
                
                for event in calendar_events:
                    parsed_event = self._parse_calendar_event(event, calendar)
                    if parsed_event:
                        events.append(parsed_event)
            
            return events
            
        except Exception as e:
            logger.error(f"❌ Failed to get events: {e}")
            return []
    
    def _parse_calendar_event(self, event: Dict, calendar: Dict) -> Optional[CalendarEvent]:
        """Parse calendar event into CalendarEvent object"""
        try:
            start = event.get('start', {})
            end = event.get('end', {})
            
            # Handle all-day events
            start_time = start.get('dateTime', start.get('date'))
            end_time = end.get('dateTime', end.get('date'))
            
            if not start_time or not end_time:
                return None
            
            # Parse datetime strings
            if 'T' in start_time:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            else:
                start_dt = datetime.fromisoformat(start_time)
                end_dt = datetime.fromisoformat(end_time)
            
            title = event.get('summary', 'Untitled Event')
            description = event.get('description', '')
            location = event.get('location', '')
            
            # Extract attendees
            attendees = []
            for attendee in event.get('attendees', []):
                if attendee.get('email'):
                    attendees.append(attendee['email'])
            
            # Analyze event for business context
            business_type = self._analyze_event_business_type(title, description, location, calendar)
            event_type = self._classify_event_type(title, description, location)
            travel_expected = self._analyze_travel_expectation(title, description, location)
            expense_context = self._generate_expense_context(title, description, location, business_type)
            
            return CalendarEvent(
                event_id=event['id'],
                title=title,
                start_time=start_dt,
                end_time=end_dt,
                location=location,
                attendees=attendees,
                description=description,
                business_type=business_type,
                event_type=event_type,
                travel_expected=travel_expected,
                expense_context=expense_context
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to parse event: {e}")
            return None
    
    def _analyze_event_business_type(self, title: str, description: str, location: str, calendar: Dict) -> str:
        """Analyze event to determine business type"""
        text = f"{title} {description} {location}".lower()
        
        # Check calendar business type first
        calendar_business_type = calendar.get('business_type', 'Business')
        
        # Check for specific business keywords
        if any(keyword in text for keyword in self.business_patterns['down_home_keywords']):
            return 'Down Home'
        elif any(keyword in text for keyword in self.business_patterns['mcr_keywords']):
            return 'Music City Rodeo'
        elif 'personal' in text or calendar_business_type == 'Personal':
            return 'Personal'
        else:
            return calendar_business_type
    
    def _classify_event_type(self, title: str, description: str, location: str) -> str:
        """Classify the type of event"""
        text = f"{title} {description}".lower()
        
        if any(keyword in text for keyword in ['meeting', 'call', 'discussion', 'review']):
            return 'meeting'
        elif any(keyword in text for keyword in ['travel', 'flight', 'trip', 'visit']):
            return 'travel'
        elif any(keyword in text for keyword in ['lunch', 'dinner', 'coffee', 'meal']):
            return 'meal'
        elif any(keyword in text for keyword in ['conference', 'event', 'seminar', 'workshop']):
            return 'conference'
        elif any(keyword in text for keyword in ['shoot', 'production', 'recording']):
            return 'production'
        elif any(keyword in text for keyword in ['performance', 'show', 'concert', 'gig']):
            return 'performance'
        else:
            return 'other'
    
    def _analyze_travel_expectation(self, title: str, description: str, location: str) -> bool:
        """Analyze if travel is expected for this event"""
        text = f"{title} {description} {location}".lower()
        
        # Check for travel indicators
        if any(keyword in text for keyword in self.business_patterns['travel_indicators']):
            return True
        
        # Check for out-of-office locations
        if location and any(keyword in location.lower() for keyword in ['airport', 'hotel', 'conference', 'out of town']):
            return True
        
        # Check for multiple-day events (often require travel)
        return False  # Would need start/end times to determine this
    
    def _generate_expense_context(self, title: str, description: str, location: str, business_type: str) -> Dict:
        """Generate expense context for the event"""
        text = f"{title} {description}".lower()
        
        context = {
            'justified_categories': [],
            'expected_expenses': [],
            'business_purpose': '',
            'tax_deductible': business_type != 'Personal'
        }
        
        # Meal context
        if any(keyword in text for keyword in self.business_patterns['meal_contexts']):
            context['justified_categories'].append('Business Meals')
            context['expected_expenses'].append('restaurant_expense')
            context['business_purpose'] = f'{business_type} business meeting with meal'
        
        # Travel context
        if any(keyword in text for keyword in self.business_patterns['travel_indicators']):
            context['justified_categories'].extend(['Travel', 'Transportation'])
            context['expected_expenses'].extend(['hotel', 'flight', 'uber', 'gas'])
            context['business_purpose'] = f'{business_type} business travel'
        
        # Meeting context
        if 'meeting' in text or 'call' in text:
            context['justified_categories'].append('Business Meetings')
            context['expected_expenses'].extend(['coffee', 'parking', 'transportation'])
            context['business_purpose'] = f'{business_type} business meeting'
        
        # Production context (Down Home specific)
        if business_type == 'Down Home' and any(keyword in text for keyword in ['shoot', 'production', 'video']):
            context['justified_categories'].extend(['Equipment', 'Production Costs'])
            context['expected_expenses'].extend(['equipment_rental', 'location_fees', 'crew_meals'])
            context['business_purpose'] = 'Video production for Down Home Media'
        
        # Event context (MCR specific)
        if business_type == 'Music City Rodeo' and any(keyword in text for keyword in ['event', 'performance', 'venue']):
            context['justified_categories'].extend(['Venue Rental', 'Equipment'])
            context['expected_expenses'].extend(['venue_fees', 'sound_equipment', 'artist_fees'])
            context['business_purpose'] = 'Music City Rodeo event production'
        
        return context
    
    def _analyze_events_for_context(self, events: List[CalendarEvent], target_date: datetime) -> BusinessContext:
        """Analyze events to generate comprehensive business context"""
        if not events:
            return self._fallback_business_context(target_date)
        
        # Find closest event to target date
        closest_event = min(events, key=lambda e: abs((e.start_time - target_date).total_seconds()))
        
        # Determine if it's a business day
        is_business_day = self._is_business_day(target_date) or any(
            event.business_type != 'Personal' for event in events
        )
        
        # Extract active projects
        active_projects = list(set([
            event.title for event in events 
            if event.business_type != 'Personal' and 'project' in event.title.lower()
        ]))
        
        # Generate meeting context
        business_events = [e for e in events if e.business_type != 'Personal']
        if business_events:
            meeting_context = f"Business activities: {', '.join([e.title for e in business_events[:3]])}"
        else:
            meeting_context = "Personal activities scheduled"
        
        # Determine travel status
        travel_events = [e for e in events if e.travel_expected]
        if travel_events:
            travel_status = f"Travel expected for: {travel_events[0].title}"
        else:
            travel_status = "No travel scheduled"
        
        # Determine primary business type
        business_types = [e.business_type for e in events if e.business_type != 'Personal']
        if business_types:
            business_type = max(set(business_types), key=business_types.count)
        else:
            business_type = 'Personal'
        
        # Generate expense justification
        if closest_event.business_type != 'Personal':
            expense_justification = f"Expense related to '{closest_event.title}' - {closest_event.expense_context.get('business_purpose', 'business activity')}"
        else:
            expense_justification = "Personal expense - calendar shows personal activities"
        
        return BusinessContext(
            is_business_day=is_business_day,
            active_projects=active_projects,
            meeting_context=meeting_context,
            travel_status=travel_status,
            business_type=business_type,
            expense_justification=expense_justification
        )
    
    def _is_business_day(self, date: datetime) -> bool:
        """Determine if date is a business day"""
        # Monday = 0, Sunday = 6
        return date.weekday() < 5  # Monday through Friday
    
    def _fallback_business_context(self, date: datetime) -> BusinessContext:
        """Generate fallback business context when calendar is not available"""
        is_business_day = self._is_business_day(date)
        
        return BusinessContext(
            is_business_day=is_business_day,
            active_projects=[],
            meeting_context="Calendar not connected - unable to determine meeting context",
            travel_status="Calendar not connected - unable to determine travel status",
            business_type="Unknown" if is_business_day else "Personal",
            expense_justification="Business expense" if is_business_day else "Personal expense"
        )
    
    def get_events_for_date(self, date: datetime) -> List[CalendarEvent]:
        """Get all events for a specific date"""
        try:
            if not self.connected:
                return []
            
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            return self._get_events_in_range(start_of_day, end_of_day)
            
        except Exception as e:
            logger.error(f"❌ Failed to get events for date: {e}")
            return []
    
    def analyze_expense_against_calendar(self, expense_data: Dict) -> Dict:
        """Analyze expense against calendar context"""
        try:
            expense_date = expense_data.get('date')
            if isinstance(expense_date, str):
                expense_date = datetime.fromisoformat(expense_date.replace('Z', '+00:00'))
            elif not isinstance(expense_date, datetime):
                expense_date = datetime.now()
            
            # Get business context for expense date/time
            business_context = self.get_business_context(expense_date)
            
            # Get events for that day
            events = self.get_events_for_date(expense_date)
            
            analysis = {
                'calendar_connected': self.connected,
                'business_context': {
                    'is_business_day': business_context.is_business_day,
                    'business_type': business_context.business_type,
                    'justification': business_context.expense_justification
                },
                'matching_events': [],
                'expense_validation': {
                    'calendar_supports': False,
                    'confidence': 0.5,
                    'reasoning': 'No calendar data available'
                }
            }
            
            if events:
                # Find events that might justify this expense
                merchant = expense_data.get('merchant', '').lower()
                amount = expense_data.get('amount', 0)
                
                matching_events = []
                for event in events:
                    if self._event_supports_expense(event, expense_data):
                        matching_events.append({
                            'title': event.title,
                            'time': event.start_time.isoformat(),
                            'business_type': event.business_type,
                            'justification': event.expense_context.get('business_purpose', ''),
                            'expected_categories': event.expense_context.get('justified_categories', [])
                        })
                
                analysis['matching_events'] = matching_events
                
                if matching_events:
                    analysis['expense_validation'] = {
                        'calendar_supports': True,
                        'confidence': 0.9,
                        'reasoning': f"Calendar shows {len(matching_events)} supporting events"
                    }
                else:
                    analysis['expense_validation'] = {
                        'calendar_supports': False,
                        'confidence': 0.3,
                        'reasoning': "No calendar events support this expense"
                    }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Expense calendar analysis failed: {e}")
            return {
                'calendar_connected': False,
                'error': str(e),
                'expense_validation': {
                    'calendar_supports': False,
                    'confidence': 0.5,
                    'reasoning': 'Calendar analysis failed'
                }
            }
    
    def _event_supports_expense(self, event: CalendarEvent, expense_data: Dict) -> bool:
        """Determine if a calendar event supports/justifies an expense"""
        merchant = expense_data.get('merchant', '').lower()
        description = expense_data.get('description', '').lower()
        category = expense_data.get('category', '').lower()
        
        # Check if expense category matches event's expected categories
        expected_categories = [cat.lower() for cat in event.expense_context.get('justified_categories', [])]
        if category in expected_categories:
            return True
        
        # Check for meal expenses during meal events
        if (event.event_type == 'meal' and 
            any(keyword in merchant for keyword in ['restaurant', 'coffee', 'food', 'starbucks'])):
            return True
        
        # Check for travel expenses during travel events
        if (event.travel_expected and 
            any(keyword in merchant for keyword in ['uber', 'lyft', 'hotel', 'flight', 'gas'])):
            return True
        
        # Check for equipment/venue expenses during production/event activities
        if (event.business_type in ['Down Home', 'Music City Rodeo'] and
            any(keyword in merchant for keyword in ['equipment', 'rental', 'venue', 'studio'])):
            return True
        
        return False
    
    def get_health_status(self) -> Dict:
        """Get calendar intelligence health status"""
        return {
            'service': 'Calendar Intelligence',
            'status': 'connected' if self.connected else 'disconnected',
            'connected': self.connected,
            'calendars_loaded': len(self.calendars),
            'google_api_available': GOOGLE_CALENDAR_AVAILABLE,
            'primary_calendar': next((cal['name'] for cal in self.calendars if cal.get('primary')), 'None'),
            'business_calendars': len([cal for cal in self.calendars if cal['business_type'] != 'Personal']),
            'capabilities': [
                'Business Context Analysis',
                'Expense Validation',
                'Travel Detection',
                'Meeting Correlation'
            ] if self.connected else ['Limited - No Connection'],
            'setup_required': not self.connected,
            'setup_instructions': 'Configure Google Calendar API credentials' if not self.connected else None,
            'last_health_check': datetime.now().isoformat()
        }

# Factory function
def create_calendar_intelligence() -> CalendarIntelligence:
    """Create and return Calendar Intelligence instance"""
    return CalendarIntelligence()

# Blueprint registration function for Flask
def register_calendar_blueprint(app):
    """Register calendar endpoints with Flask app"""
    from flask import Blueprint, jsonify, request
    
    calendar_bp = Blueprint('calendar', __name__, url_prefix='/api/calendar')
    calendar_intelligence = create_calendar_intelligence()
    
    @calendar_bp.route('/health', methods=['GET'])
    def calendar_health():
        """Calendar health check endpoint"""
        try:
            health_status = calendar_intelligence.get_health_status()
            return jsonify(health_status)
        except Exception as e:
            return jsonify({
                'service': 'Calendar Intelligence',
                'status': 'error',
                'connected': False,
                'error': str(e),
                'last_health_check': datetime.now().isoformat()
            }), 200
    
    @calendar_bp.route('/context', methods=['POST'])
    def get_business_context():
        """Get business context for a date/time"""
        try:
            data = request.get_json() or {}
            date_str = data.get('date')
            
            if date_str:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                date = datetime.now()
            
            context = calendar_intelligence.get_business_context(date)
            
            return jsonify({
                'success': True,
                'date': date.isoformat(),
                'business_context': {
                    'is_business_day': context.is_business_day,
                    'active_projects': context.active_projects,
                    'meeting_context': context.meeting_context,
                    'travel_status': context.travel_status,
                    'business_type': context.business_type,
                    'expense_justification': context.expense_justification
                }
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @calendar_bp.route('/analyze-expense', methods=['POST'])
    def analyze_expense_context():
        """Analyze expense against calendar context"""
        try:
            expense_data = request.get_json() or {}
            analysis = calendar_intelligence.analyze_expense_against_calendar(expense_data)
            
            return jsonify({
                'success': True,
                'analysis': analysis
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @calendar_bp.route('/events', methods=['GET'])
    def get_events():
        """Get calendar events for a date"""
        try:
            date_str = request.args.get('date')
            
            if date_str:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                date = datetime.now()
            
            events = calendar_intelligence.get_events_for_date(date)
            
            events_data = []
            for event in events:
                events_data.append({
                    'id': event.event_id,
                    'title': event.title,
                    'start_time': event.start_time.isoformat(),
                    'end_time': event.end_time.isoformat(),
                    'location': event.location,
                    'business_type': event.business_type,
                    'event_type': event.event_type,
                    'travel_expected': event.travel_expected,
                    'attendees_count': len(event.attendees)
                })
            
            return jsonify({
                'success': True,
                'date': date.isoformat(),
                'events': events_data,
                'events_count': len(events_data)
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    app.register_blueprint(calendar_bp)
    logger.info("📅 Calendar Intelligence blueprint registered") 
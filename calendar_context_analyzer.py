"""
Brian Kaplan's Intelligent Calendar Context Analyzer
Understands meetings, travel, and events to provide contextual expense analysis
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
import calendar

# Google Calendar integration
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False
    logging.warning("Google Calendar dependencies not available")

logger = logging.getLogger(__name__)

@dataclass
class CalendarEvent:
    """Calendar event with business context"""
    id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    attendees: List[str]
    event_type: str  # "meeting", "travel", "personal", "business"
    business_context: str  # "down_home", "mcr", "personal", "mixed"
    confidence: float
    related_expenses: List[str]  # List of expense IDs that match this event

@dataclass
class TravelEvent:
    """Travel event with location and purpose context"""
    id: str
    destination: str
    departure_date: datetime
    return_date: datetime
    purpose: str  # "business", "personal", "mixed"
    business_type: str  # "down_home", "mcr", "personal"
    transportation_mode: str  # "flight", "drive", "train", "other"
    accommodation: Optional[str]
    related_meetings: List[str]  # Related meeting IDs
    expected_expenses: List[str]  # Expected expense types

@dataclass
class ContextMatch:
    """Context match between expense and calendar events"""
    expense_id: str
    event_id: str
    match_type: str  # "time", "location", "purpose", "attendees"
    confidence: float
    context_explanation: str
    business_justification: str

class CalendarContextAnalyzer:
    """
    Intelligent Calendar Context Analyzer for Brian Kaplan
    
    This system:
    1. Syncs with Google Calendar to understand Brian's schedule
    2. Identifies business vs personal events
    3. Recognizes travel patterns and meeting contexts
    4. Matches expenses to calendar events for better categorization
    5. Provides intelligent business justification for expenses
    6. Learns from patterns to improve accuracy over time
    """
    
    def __init__(self):
        self.credentials_path = os.getenv('GOOGLE_CALENDAR_CREDENTIALS', 'credentials/service_account.json')
        self.calendar_service = None
        self.primary_calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        
        # Brian's business context
        self.business_keywords = {
            "down_home": [
                "client", "production", "director", "crew", "editing", "post-production",
                "strategic consulting", "business development", "soho house", "media",
                "video production", "content creation", "location scout", "equipment"
            ],
            "mcr": [
                "rodeo", "arena", "cowboy", "country music", "nfr", "vegas", "music city",
                "event planning", "venue", "entertainment", "western", "bull riding",
                "nashville", "country", "music industry"
            ],
            "business_general": [
                "meeting", "conference", "networking", "client", "vendor", "supplier",
                "business lunch", "industry event", "trade show", "workshop"
            ]
        }
        
        self.travel_keywords = [
            "flight", "airport", "hotel", "travel", "trip", "destination",
            "business trip", "conference", "client visit", "site visit"
        ]
        
        self.expense_correlation_patterns = {
            "meals": ["lunch", "dinner", "breakfast", "meal", "restaurant", "catering"],
            "transportation": ["uber", "lyft", "taxi", "rental car", "parking", "gas"],
            "accommodation": ["hotel", "airbnb", "lodging", "accommodation"],
            "equipment": ["camera", "microphone", "lighting", "computer", "software"],
            "office": ["supplies", "office", "equipment", "software", "subscription"]
        }
        
        self._initialize_calendar_service()
        logger.info("📅 Calendar Context Analyzer initialized")
    
    def _initialize_calendar_service(self):
        """Initialize Google Calendar service"""
        if not GOOGLE_CALENDAR_AVAILABLE:
            logger.warning("Google Calendar not available - install google-api-python-client")
            return
        
        try:
            if os.path.exists(self.credentials_path):
                credentials = Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/calendar.readonly']
                )
                self.calendar_service = build('calendar', 'v3', credentials=credentials)
                logger.info("✅ Google Calendar service initialized")
            else:
                logger.warning(f"Calendar credentials not found at {self.credentials_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Calendar service: {e}")
    
    def sync_calendar_events(self, days_back: int = 30, days_forward: int = 30) -> List[CalendarEvent]:
        """
        Sync calendar events and analyze business context
        """
        if not self.calendar_service:
            logger.warning("Calendar service not available")
            return []
        
        try:
            # Calculate time range
            now = datetime.utcnow()
            time_min = (now - timedelta(days=days_back)).isoformat() + 'Z'
            time_max = (now + timedelta(days=days_forward)).isoformat() + 'Z'
            
            # Fetch events
            events_result = self.calendar_service.events().list(
                calendarId=self.primary_calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=500,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Process and analyze events
            analyzed_events = []
            for event in events:
                analyzed_event = self._analyze_calendar_event(event)
                if analyzed_event:
                    analyzed_events.append(analyzed_event)
            
            logger.info(f"📅 Synced {len(analyzed_events)} calendar events")
            return analyzed_events
            
        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Calendar sync error: {e}")
            return []
    
    def _analyze_calendar_event(self, event: Dict) -> Optional[CalendarEvent]:
        """Analyze a single calendar event for business context"""
        try:
            # Extract basic event data
            event_id = event.get('id', '')
            title = event.get('summary', 'No Title')
            description = event.get('description', '')
            location = event.get('location', '')
            
            # Parse start/end times
            start = event.get('start', {})
            end = event.get('end', {})
            
            start_time = self._parse_calendar_datetime(start)
            end_time = self._parse_calendar_datetime(end)
            
            if not start_time or not end_time:
                return None
            
            # Extract attendees
            attendees = []
            for attendee in event.get('attendees', []):
                email = attendee.get('email', '')
                if email:
                    attendees.append(email)
            
            # Analyze business context
            event_type, business_context, confidence = self._determine_event_context(
                title, description, location, attendees
            )
            
            return CalendarEvent(
                id=event_id,
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                location=location,
                attendees=attendees,
                event_type=event_type,
                business_context=business_context,
                confidence=confidence,
                related_expenses=[]
            )
            
        except Exception as e:
            logger.error(f"Error analyzing calendar event: {e}")
            return None
    
    def _parse_calendar_datetime(self, time_dict: Dict) -> Optional[datetime]:
        """Parse Google Calendar datetime format"""
        try:
            if 'dateTime' in time_dict:
                # Full datetime with timezone
                dt_str = time_dict['dateTime']
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            elif 'date' in time_dict:
                # All-day event
                date_str = time_dict['date']
                return datetime.strptime(date_str, '%Y-%m-%d')
            return None
        except Exception as e:
            logger.error(f"Error parsing calendar datetime: {e}")
            return None
    
    def _determine_event_context(self, title: str, description: str, location: str, attendees: List[str]) -> Tuple[str, str, float]:
        """Determine event type and business context with confidence"""
        combined_text = f"{title} {description} {location}".lower()
        
        # Check for travel indicators
        if any(keyword in combined_text for keyword in self.travel_keywords):
            event_type = "travel"
        elif any(keyword in combined_text for keyword in ["meeting", "call", "conference", "client"]):
            event_type = "meeting"
        elif any(keyword in combined_text for keyword in ["personal", "family", "doctor", "appointment"]):
            event_type = "personal"
        else:
            event_type = "business"  # Default assumption for Brian
        
        # Determine business context
        down_home_score = sum(1 for keyword in self.business_keywords["down_home"] if keyword in combined_text)
        mcr_score = sum(1 for keyword in self.business_keywords["mcr"] if keyword in combined_text)
        business_score = sum(1 for keyword in self.business_keywords["business_general"] if keyword in combined_text)
        
        # Check attendee domains for business context
        business_domains = ["downhome.com", "musiccityrodeo.com"]
        attendee_business_score = sum(1 for attendee in attendees if any(domain in attendee for domain in business_domains))
        
        # Determine primary business context
        if down_home_score > mcr_score and down_home_score > 0:
            business_context = "down_home"
            confidence = min(0.9, 0.5 + (down_home_score * 0.1) + (attendee_business_score * 0.1))
        elif mcr_score > down_home_score and mcr_score > 0:
            business_context = "mcr"
            confidence = min(0.9, 0.5 + (mcr_score * 0.1) + (attendee_business_score * 0.1))
        elif business_score > 0 or attendee_business_score > 0:
            business_context = "mixed"
            confidence = min(0.8, 0.4 + (business_score * 0.1) + (attendee_business_score * 0.1))
        elif event_type == "personal":
            business_context = "personal"
            confidence = 0.8
        else:
            business_context = "mixed"
            confidence = 0.3
        
        return event_type, business_context, confidence
    
    def identify_travel_events(self, calendar_events: List[CalendarEvent]) -> List[TravelEvent]:
        """Identify and analyze travel events from calendar"""
        travel_events = []
        
        # Group events by date to find travel patterns
        travel_candidates = [event for event in calendar_events if event.event_type == "travel"]
        
        for event in travel_candidates:
            travel_event = self._analyze_travel_event(event, calendar_events)
            if travel_event:
                travel_events.append(travel_event)
        
        logger.info(f"✈️ Identified {len(travel_events)} travel events")
        return travel_events
    
    def _analyze_travel_event(self, event: CalendarEvent, all_events: List[CalendarEvent]) -> Optional[TravelEvent]:
        """Analyze a travel event for context and related meetings"""
        try:
            # Extract destination from title/location
            destination = self._extract_destination(event.title, event.location, event.description)
            
            # Determine transportation mode
            transportation = self._determine_transportation_mode(event.title, event.description)
            
            # Find related meetings on the same dates
            related_meetings = []
            event_date = event.start_time.date()
            
            for other_event in all_events:
                if (other_event.id != event.id and 
                    other_event.start_time.date() == event_date and
                    other_event.event_type == "meeting"):
                    related_meetings.append(other_event.id)
            
            # Determine business purpose
            purpose = "business" if event.business_context in ["down_home", "mcr", "mixed"] else "personal"
            
            # Expected expenses for this travel
            expected_expenses = self._predict_travel_expenses(destination, transportation, len(related_meetings))
            
            return TravelEvent(
                id=event.id,
                destination=destination,
                departure_date=event.start_time,
                return_date=event.end_time,
                purpose=purpose,
                business_type=event.business_context,
                transportation_mode=transportation,
                accommodation=None,  # Will be determined from expenses
                related_meetings=related_meetings,
                expected_expenses=expected_expenses
            )
            
        except Exception as e:
            logger.error(f"Error analyzing travel event: {e}")
            return None
    
    def match_expenses_to_calendar(self, expenses: List[Dict], calendar_events: List[CalendarEvent]) -> List[ContextMatch]:
        """Match expenses to calendar events for contextual understanding"""
        matches = []
        
        for expense in expenses:
            expense_date = self._parse_expense_date(expense.get('date'))
            if not expense_date:
                continue
            
            # Find events within 24 hours of the expense
            relevant_events = [
                event for event in calendar_events
                if abs((event.start_time.date() - expense_date.date()).days) <= 1
            ]
            
            for event in relevant_events:
                match = self._calculate_expense_event_match(expense, event)
                if match and match.confidence > 0.3:
                    matches.append(match)
        
        # Sort by confidence
        matches.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"🔗 Found {len(matches)} expense-calendar matches")
        return matches
    
    def _calculate_expense_event_match(self, expense: Dict, event: CalendarEvent) -> Optional[ContextMatch]:
        """Calculate match confidence between expense and calendar event"""
        try:
            expense_id = expense.get('id', '')
            merchant = expense.get('merchant', '').lower()
            amount = expense.get('amount', 0)
            description = expense.get('description', '').lower()
            
            # Time-based matching
            expense_date = self._parse_expense_date(expense.get('date'))
            if not expense_date:
                return None
            
            time_diff = abs((event.start_time - expense_date).total_seconds()) / 3600  # Hours
            time_score = max(0, 1 - (time_diff / 24))  # Decay over 24 hours
            
            # Location matching
            location_score = 0
            if event.location:
                location_keywords = event.location.lower().split()
                location_score = sum(0.2 for keyword in location_keywords if keyword in merchant or keyword in description)
            
            # Purpose matching
            purpose_score = 0
            combined_event_text = f"{event.title} {event.description}".lower()
            
            # Check expense type correlation
            for expense_type, keywords in self.expense_correlation_patterns.items():
                if any(keyword in merchant or keyword in description for keyword in keywords):
                    if any(keyword in combined_event_text for keyword in keywords):
                        purpose_score += 0.3
            
            # Business context matching
            business_score = 0
            if event.business_context in ["down_home", "mcr"]:
                business_keywords = self.business_keywords[event.business_context]
                business_score = sum(0.1 for keyword in business_keywords if keyword in merchant or keyword in description)
            
            # Calculate overall confidence
            confidence = (time_score * 0.4 + location_score * 0.2 + purpose_score * 0.3 + business_score * 0.1)
            confidence = min(confidence, 0.95)  # Cap at 95%
            
            if confidence < 0.3:
                return None
            
            # Generate context explanation
            context_explanation = self._generate_context_explanation(expense, event, time_score, location_score, purpose_score)
            business_justification = self._generate_business_justification(expense, event)
            
            # Determine match type
            if time_score > 0.8 and location_score > 0.5:
                match_type = "time_location"
            elif purpose_score > 0.5:
                match_type = "purpose"
            elif time_score > 0.6:
                match_type = "time"
            else:
                match_type = "general"
            
            return ContextMatch(
                expense_id=expense_id,
                event_id=event.id,
                match_type=match_type,
                confidence=confidence,
                context_explanation=context_explanation,
                business_justification=business_justification
            )
            
        except Exception as e:
            logger.error(f"Error calculating expense-event match: {e}")
            return None
    
    def _generate_context_explanation(self, expense: Dict, event: CalendarEvent, time_score: float, location_score: float, purpose_score: float) -> str:
        """Generate human-readable context explanation"""
        explanations = []
        
        if time_score > 0.8:
            explanations.append(f"occurred during '{event.title}'")
        elif time_score > 0.5:
            explanations.append(f"happened near the time of '{event.title}'")
        
        if location_score > 0.5:
            explanations.append(f"at same location ({event.location})")
        
        if purpose_score > 0.5:
            explanations.append("matches event purpose/type")
        
        if event.business_context in ["down_home", "mcr"]:
            explanations.append(f"related to {event.business_context.replace('_', ' ').title()} business")
        
        if not explanations:
            explanations.append("general time correlation")
        
        return "Expense " + " and ".join(explanations)
    
    def _generate_business_justification(self, expense: Dict, event: CalendarEvent) -> str:
        """Generate business justification for the expense"""
        merchant = expense.get('merchant', '')
        amount = expense.get('amount', 0)
        
        if event.business_context == "down_home":
            return f"${amount} at {merchant} for Down Home Media Production business meeting/activity: '{event.title}'"
        elif event.business_context == "mcr":
            return f"${amount} at {merchant} for Music City Rodeo business meeting/activity: '{event.title}'"
        elif event.event_type == "meeting":
            return f"${amount} at {merchant} for business meeting: '{event.title}'"
        elif event.event_type == "travel":
            return f"${amount} at {merchant} for business travel related to: '{event.title}'"
        else:
            return f"${amount} at {merchant} related to calendar event: '{event.title}'"
    
    def _extract_destination(self, title: str, location: str, description: str) -> str:
        """Extract travel destination from event details"""
        # Priority: location > title > description
        if location and len(location.strip()) > 2:
            return location.strip()
        
        # Look for city/state patterns in title
        combined_text = f"{title} {description}"
        
        # Common destination patterns
        destination_patterns = [
            r'(?:to|in|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+,\s*[A-Z]{2})',  # City, State
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # Two-word cities
        ]
        
        for pattern in destination_patterns:
            matches = re.findall(pattern, combined_text)
            if matches:
                return matches[0].strip()
        
        return "Unknown Destination"
    
    def _determine_transportation_mode(self, title: str, description: str) -> str:
        """Determine transportation mode from event details"""
        combined_text = f"{title} {description}".lower()
        
        if any(word in combined_text for word in ["flight", "fly", "airport", "airline"]):
            return "flight"
        elif any(word in combined_text for word in ["drive", "driving", "car", "road trip"]):
            return "drive"
        elif any(word in combined_text for word in ["train", "amtrak", "rail"]):
            return "train"
        else:
            return "other"
    
    def _predict_travel_expenses(self, destination: str, transportation: str, meeting_count: int) -> List[str]:
        """Predict expected expense types for travel"""
        expected = []
        
        # Transportation expenses
        if transportation == "flight":
            expected.extend(["airline", "airport parking", "taxi/uber to airport"])
        elif transportation == "drive":
            expected.extend(["gas", "tolls", "parking"])
        
        # Accommodation (if multi-day)
        expected.append("hotel/accommodation")
        
        # Meals
        expected.extend(["breakfast", "lunch", "dinner"])
        
        # Business expenses based on meeting count
        if meeting_count > 0:
            expected.extend(["client dinner", "business lunch", "coffee meeting"])
        
        # Location-specific
        if "vegas" in destination.lower():
            expected.extend(["entertainment", "shows", "networking events"])
        elif "nashville" in destination.lower():
            expected.extend(["music venues", "industry events"])
        
        return expected
    
    def _parse_expense_date(self, date_value) -> Optional[datetime]:
        """Parse expense date from various formats"""
        if isinstance(date_value, datetime):
            return date_value
        elif isinstance(date_value, str):
            try:
                # Try various formats
                formats = ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']
                for fmt in formats:
                    try:
                        return datetime.strptime(date_value, fmt)
                    except ValueError:
                        continue
                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except:
                return None
        return None
    
    def generate_calendar_insights(self, calendar_events: List[CalendarEvent], matches: List[ContextMatch]) -> Dict:
        """Generate insights about calendar and expense patterns"""
        insights = {
            "total_events": len(calendar_events),
            "business_events": len([e for e in calendar_events if e.business_context in ["down_home", "mcr", "mixed"]]),
            "travel_events": len([e for e in calendar_events if e.event_type == "travel"]),
            "meeting_events": len([e for e in calendar_events if e.event_type == "meeting"]),
            "matched_expenses": len(matches),
            "high_confidence_matches": len([m for m in matches if m.confidence > 0.7]),
            "business_context_breakdown": {},
            "recommendations": []
        }
        
        # Business context breakdown
        for event in calendar_events:
            context = event.business_context
            if context not in insights["business_context_breakdown"]:
                insights["business_context_breakdown"][context] = 0
            insights["business_context_breakdown"][context] += 1
        
        # Generate recommendations
        if insights["matched_expenses"] < insights["total_events"] * 0.3:
            insights["recommendations"].append("Consider adding more detailed event descriptions for better expense matching")
        
        if insights["travel_events"] > 0 and len([m for m in matches if "travel" in m.context_explanation]) == 0:
            insights["recommendations"].append("Add travel-related expense tracking for better business documentation")
        
        return insights

def main():
    """Test the calendar context analyzer"""
    analyzer = CalendarContextAnalyzer()
    
    # Sync calendar events
    events = analyzer.sync_calendar_events(days_back=7, days_forward=30)
    print(f"Synced {len(events)} calendar events")
    
    # Identify travel
    travel_events = analyzer.identify_travel_events(events)
    print(f"Found {len(travel_events)} travel events")
    
    # Test with sample expenses
    sample_expenses = [
        {
            "id": "exp_1",
            "merchant": "Soho House",
            "amount": 85.50,
            "date": datetime.now().isoformat(),
            "description": "Client lunch meeting"
        }
    ]
    
    matches = analyzer.match_expenses_to_calendar(sample_expenses, events)
    print(f"Found {len(matches)} expense matches")
    
    insights = analyzer.generate_calendar_insights(events, matches)
    print(f"Generated insights: {insights}")

if __name__ == "__main__":
    main() 
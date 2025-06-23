"""
Expense Categorizer for Email Intelligence System
Converts JavaScript categorization logic to Python for Brian's expense tracking
"""

import re
import logging
import os
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import OpenAI for enhanced categorization
try:
    import openai
    openai.api_key = os.getenv('OPENAI_API_KEY')
    OPENAI_AVAILABLE = bool(os.getenv('OPENAI_API_KEY'))
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - using rule-based categorization only")

class BusinessType(Enum):
    """Business types for categorization"""
    DOWN_HOME = "DH"
    MUSIC_CITY_RODEO = "MCR"
    PERSONAL = "PERSONAL"
    BUSINESS_DEVELOPMENT = "BD"

@dataclass
class CategoryConfig:
    """Configuration for expense categories"""
    keywords: List[str]
    category: str
    details: str
    confidence_boost: float = 0.0

@dataclass
class ExpenseCategory:
    """Result of expense categorization"""
    category: str
    details: str
    confidence: float
    needs_review: int
    location: Optional[str] = None
    client_name: Optional[str] = None
    business_type: Optional[str] = None

class ExpenseCategorizer:
    """
    Intelligent expense categorizer for Brian's business expenses
    Handles Down Home, Music City Rodeo, and personal expenses
    """
    
    def __init__(self):
        self.categories = self._initialize_categories()
        self.location_keywords = ['in', 'to', 'at', 'from', 'via', 'through']
        self.client_patterns = [
            r'with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'client:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'meeting\s+with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'dinner\s+with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
    
    def _initialize_categories(self) -> Dict[str, CategoryConfig]:
        """Initialize NetSuite expense categories with keywords and mappings"""
        return {
            # Business Development Categories
            'BD_ADVERTISING': CategoryConfig(
                keywords=['advertising', 'promotion', 'marketing', 'ad campaign', 'branding', 'google ads', 'facebook ads'],
                category='BD: Advertising & Promotion',
                details='Marketing/Advertising',
                confidence_boost=0.1
            ),
            'BD_CLIENT_MEALS': CategoryConfig(
                keywords=['dinner', 'lunch', 'breakfast', 'restaurant', 'meal', 'dining', 'client', 'business meal'],
                category='BD: Client Business Meals',
                details='Client Business Meal',
                confidence_boost=0.2
            ),
            'BD_COMMISSIONS': CategoryConfig(
                keywords=['commission', 'fee', 'referral', 'finder', 'agent'],
                category='BD: Commissions & Fees',
                details='Commission/Fee'
            ),
            'BD_CONSULTANTS': CategoryConfig(
                keywords=['consultant', 'freelancer', 'contractor', 'advisor', 'expert'],
                category='BD: Consultants',
                details='Consultant Services'
            ),
            'BD_INTERNAL_PROJECTS': CategoryConfig(
                keywords=['pro bono', 'internal', 'volunteer', 'charity', 'community'],
                category='BD: Internal / Pro Bono Projects',
                details='Pro Bono Work'
            ),
            'BD_SUBSCRIPTIONS': CategoryConfig(
                keywords=['subscription', 'membership', 'journal', 'database', 'research', 'publication', 'saas'],
                category='BD: Subscriptions & Research Costs',
                details='Subscription/Research'
            ),
            'BD_WRITERS_ROOM': CategoryConfig(
                keywords=['writing', 'script', 'story', 'creative', 'brainstorm', 'writers room'],
                category="BD: Writer's Room",
                details='Creative Writing'
            ),
            'BD_OTHER': CategoryConfig(
                keywords=['misc', 'other', 'miscellaneous'],
                category='BD: Other Costs',
                details='Other Business Cost'
            ),

            # Travel & Entertainment - Down Home
            'DH_TRAVEL_AIRFARE': CategoryConfig(
                keywords=['flight', 'airline', 'ticket', 'airfare', 'american airlines', 'delta', 'united', 'southwest'],
                category='DH: Travel Costs - Airfare',
                details='Business Flight',
                confidence_boost=0.2
            ),
            'DH_TRAVEL_GROUND': CategoryConfig(
                keywords=['uber', 'lyft', 'taxi', 'cab', 'bus fare', 'metro', 'subway', 'rideshare'],
                category='DH: Travel Costs - Cab/Uber/Bus Fare',
                details='Ground Transportation',
                confidence_boost=0.2
            ),
            'DH_TRAVEL_CAR': CategoryConfig(
                keywords=['gas', 'fuel', 'rental car', 'hertz', 'enterprise', 'budget', 'avis', 'national', 'alamo', 'chevron', 'shell', 'bp', 'exxon'],
                category='DH: Travel Costs - Gas/Rental Car',
                details='Car/Gas Expense',
                confidence_boost=0.2
            ),
            'DH_TRAVEL_HOTEL': CategoryConfig(
                keywords=['hotel', 'stay', 'accommodation', 'inn', 'resort', 'lodge', 'motel', 'marriott', 'hilton', 'airbnb'],
                category='DH: Travel Costs - Hotel',
                details='Accommodation',
                confidence_boost=0.2
            ),
            'DH_TRAVEL_MEALS': CategoryConfig(
                keywords=['travel meal', 'airport food', 'highway', 'road trip', 'per diem'],
                category='DH: Travel costs - Meals',
                details='Travel Meal'
            ),
            'DH_SOHO_HOUSE': CategoryConfig(
                keywords=['soho house', 'soho', 'membership club', 'private club'],
                category='DH:  Soho House Fees',
                details='Soho House'
            ),

            # Strategic Consulting Travel
            'STRATEGIC_TRAVEL': CategoryConfig(
                keywords=['strategic', 'consulting travel', 'client visit'],
                category='Strategic  Consulting:  Travel',
                details='Strategic Consulting Travel'
            ),

            # Office & Equipment
            'OFFICE_EQUIPMENT': CategoryConfig(
                keywords=['computer', 'laptop', 'monitor', 'camera', 'equipment', 'hardware'],
                category='Office Equipment',
                details='Office Equipment'
            ),
            'OFFICE_SUPPLIES': CategoryConfig(
                keywords=['supplies', 'stationery', 'pens', 'paper', 'staples', 'office depot', 'amazon'],
                category='Office Supplies',
                details='Office Supplies'
            ),
            'PRINTING_COPYING': CategoryConfig(
                keywords=['printing', 'copying', 'fedex', 'kinkos', 'print shop'],
                category='Printing & Copying',
                details='Printing/Copying'
            ),
            'PRODUCTION_EQUIPMENT': CategoryConfig(
                keywords=['production', 'video', 'audio', 'lighting', 'gear'],
                category='Production Equipment',
                details='Production Gear'
            ),
            'INTERNET_COSTS': CategoryConfig(
                keywords=['internet', 'wifi', 'broadband', 'comcast', 'spectrum'],
                category='Internet Costs',
                details='Internet Service'
            ),
            'MOBILE_PHONE': CategoryConfig(
                keywords=['mobile', 'phone', 'cell', 'verizon', 'at&t', 't-mobile'],
                category='Mobile Phone Costs',
                details='Mobile Phone'
            ),
            'SOFTWARE_SUBSCRIPTIONS': CategoryConfig(
                keywords=['software', 'adobe', 'microsoft', 'google', 'zoom', 'slack', 'license'],
                category='Software subscriptions',
                details='Software/SaaS',
                confidence_boost=0.1
            ),

            # Content Creation (SCC)
            'SCC_DIRECTOR': CategoryConfig(
                keywords=['director', 'directing'],
                category='SCC: Director Fees',
                details='Director Fee'
            ),
            'SCC_EDITORIAL': CategoryConfig(
                keywords=['editing', 'post', 'finishing', 'color', 'sound'],
                category='SCC: Editorial / Finishing Costs',
                details='Editorial/Finishing'
            ),
            'SCC_EQUIPMENT': CategoryConfig(
                keywords=['equipment cost', 'rental equipment'],
                category='SCC: Equipment Cost',
                details='Equipment Cost'
            ),
            'SCC_HARD_DRIVES': CategoryConfig(
                keywords=['hard drive', 'storage', 'ssd', 'drive'],
                category='SCC: Hard Drives',
                details='Storage/Drives'
            ),
            'SCC_WRITING': CategoryConfig(
                keywords=['ideation', 'writing', 'script'],
                category='SCC: Ideation / Writing Fees',
                details='Writing Fee'
            ),
            'SCC_INFLUENCER': CategoryConfig(
                keywords=['influencer', 'agency'],
                category='SCC: Influencer Agency Fees',
                details='Influencer Fee'
            ),
            'SCC_INTERNAL_LABOR': CategoryConfig(
                keywords=['internal labor'],
                category='SCC: Internal Labor',
                details='Internal Labor'
            ),
            'SCC_LOCATION_RENTAL': CategoryConfig(
                keywords=['location', 'rental fee', 'venue'],
                category='SCC: Local / Rental Fee',
                details='Location Rental'
            ),
            'SCC_LOCATION_TRAVEL': CategoryConfig(
                keywords=['location travel'],
                category='SCC: Location - Travel Expense',
                details='Location Travel'
            ),
            'SCC_LOCATION_MEALS': CategoryConfig(
                keywords=['location meals', 'craft services'],
                category='SCC : Location - Meals',
                details='Location Meals'
            ),
            'SCC_MISC': CategoryConfig(
                keywords=['miscellaneous'],
                category='SCC: Miscellaneous Costs',
                details='Misc Production'
            ),
            'SCC_OTHER': CategoryConfig(
                keywords=['other costs'],
                category='SCC: Other Costs',
                details='Other Production'
            ),
            'SCC_PAYROLL': CategoryConfig(
                keywords=['payroll', 'taxes'],
                category='SCC: Payroll Taxes / Fees',
                details='Payroll/Taxes'
            ),
            'SCC_PREPRODUCTION': CategoryConfig(
                keywords=['pre-production', 'prep', 'wrap'],
                category='SCC: Pre-production Wrap Cost',
                details='Pre-production'
            ),
            'SCC_INSURANCE': CategoryConfig(
                keywords=['production insurance', 'insurance'],
                category='SCC: Production Insurance',
                details='Production Insurance'
            ),
            'SCC_PROPS': CategoryConfig(
                keywords=['props', 'wardrobe', 'costume'],
                category='SCC: Props / Wardrobe',
                details='Props/Wardrobe'
            ),
            'SCC_CREW': CategoryConfig(
                keywords=['crew', 'shooting'],
                category='SCC: Shooting Crew Labor',
                details='Crew Labor'
            ),
            'SCC_STUDIO': CategoryConfig(
                keywords=['studio', 'set construction'],
                category='SCC: Studio / Set Construction',
                details='Studio/Set'
            ),
            'SCC_TALENT': CategoryConfig(
                keywords=['talent', 'actor', 'performer'],
                category='SCC: Talent / Influencer Cost / Expenses',
                details='Talent Cost'
            ),

            # Internal Labor
            'INTERNAL_PAID_MEDIA': CategoryConfig(
                keywords=['paid media'],
                category='Internal Labor: Paid Media',
                details='Paid Media Labor'
            ),
            'INTERNAL_SOCIAL': CategoryConfig(
                keywords=['social content'],
                category='Internal Labor: Social Content',
                details='Social Content Labor'
            ),
            'INTERNAL_STRATEGIC': CategoryConfig(
                keywords=['strategic consulting'],
                category='Internal Labor: Strategic Consulting',
                details='Strategic Labor'
            ),

            # Meetings & Entertainment
            'COMPANY_MEETINGS': CategoryConfig(
                keywords=['company meeting', 'team lunch', 'office lunch', 'staff meeting', 'catering'],
                category='Company Meetings and Meals',
                details='Company Meeting',
                confidence_boost=0.1
            ),
            'CONFERENCE': CategoryConfig(
                keywords=['conference', 'seminar', 'workshop', 'training', 'summit', 'symposium'],
                category='Conference',
                details='Conference/Training'
            ),

            # Other Categories
            'INSURANCE_REIMBURSEMENT': CategoryConfig(
                keywords=['insurance reimbursement'],
                category='Insurance Reimbursement',
                details='Insurance'
            ),
            'SOCIAL_CONTENT_CREATION': CategoryConfig(
                keywords=['social content creation'],
                category='Social Content Creation',
                details='Social Content'
            ),

            # Vegas/NFR/Rodeo Specific (keeping for Music City Rodeo)
            'VEGAS_NFR': CategoryConfig(
                keywords=['vegas', 'las vegas', 'nfr', 'strip', 'casino', 'rodeo', 'arena', 'cowboy'],
                category='SCC: Location - Travel Expense',  # Map to existing SCC category
                details='Vegas/NFR Event',
                confidence_boost=0.3
            )
        }
    
    def extract_location(self, text: str) -> Optional[str]:
        """
        Extract location from text using common patterns
        
        Args:
            text: Text to extract location from
            
        Returns:
            Extracted location or None if not found
        """
        if not text:
            return None
        
        # Look for location patterns after keywords
        for keyword in self.location_keywords:
            pattern = rf'{keyword}\s+([\w\s]+)(?:,|\.|$)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                # Filter out common non-location words
                if len(location) > 2 and location.lower() not in ['the', 'and', 'for', 'with']:
                    return location
        
        # Look for city, state patterns
        city_state_pattern = r'([A-Z][a-z]+),?\s+([A-Z]{2})'
        match = re.search(city_state_pattern, text)
        if match:
            return f"{match.group(1)}, {match.group(2)}"
        
        return None
    
    def extract_client_name(self, text: str) -> Optional[str]:
        """
        Extract client name from text
        
        Args:
            text: Text to extract client name from
            
        Returns:
            Extracted client name or None if not found
        """
        if not text:
            return None
        
        for pattern in self.client_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                client_name = match.group(1).strip()
                # Basic validation - should be reasonable length and format
                if 2 <= len(client_name) <= 50 and not any(char.isdigit() for char in client_name):
                    return client_name
        
        return None
    
    def determine_business_type(self, text: str, email_account: str = None) -> str:
        """
        Determine business type based on text content and email account
        
        Args:
            text: Combined text from expense description
            email_account: Email account the expense came from
            
        Returns:
            Business type identifier
        """
        text_upper = text.upper()
        
        # Email account-based determination
        if email_account:
            if 'downhome.com' in email_account.lower():
                return BusinessType.DOWN_HOME.value
            elif 'musiccityrodeo.com' in email_account.lower():
                return BusinessType.MUSIC_CITY_RODEO.value
        
        # Content-based determination
        mcr_keywords = ['rodeo', 'nfr', 'vegas', 'arena', 'cowboy', 'livestock', 'western']
        dh_keywords = ['client', 'business development', 'bd', 'down home']
        
        if any(keyword.upper() in text_upper for keyword in mcr_keywords):
            return BusinessType.MUSIC_CITY_RODEO.value
        elif any(keyword.upper() in text_upper for keyword in dh_keywords):
            return BusinessType.DOWN_HOME.value
        
        return BusinessType.BUSINESS_DEVELOPMENT.value
    
    def get_ai_category_suggestion(self, expense: Dict) -> Optional[str]:
        """
        Get AI-enhanced category suggestion using OpenAI
        
        Args:
            expense: Dictionary containing expense details
            
        Returns:
            Suggested NetSuite category or None if AI not available
        """
        if not OPENAI_AVAILABLE:
            return None
        
        try:
            # Get all available categories for validation
            all_categories = [config.category for config in self.categories.values()]
            categories_list = '\n'.join([f"- {cat}" for cat in sorted(set(all_categories))])
            
            prompt = f"""You are a NetSuite expense categorization expert for a media production company.

Given this expense transaction, suggest the most appropriate category from the list below.
Only return the exact category name, nothing else.

EXPENSE DETAILS:
- Vendor/Merchant: {expense.get('merchant', expense.get('description', ''))}
- Description: {expense.get('memo', expense.get('description', ''))}
- Amount: ${expense.get('amount', 0)}
- Email Account: {expense.get('email_account', '')}

AVAILABLE CATEGORIES:
{categories_list}

BUSINESS CONTEXT:
- Down Home (DH): Main business travel and client entertainment
- BD: Business development and general business expenses
- SCC: Content creation and production costs
- Internal Labor: Staff time allocation
- Office: Equipment and operational costs

Return only the exact category name that best matches this expense."""

            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                max_tokens=100,
                temperature=0.1
            )
            
            suggested_category = response.choices[0].message.content.strip()
            
            # Validate that the suggested category exists
            if suggested_category in all_categories:
                logger.info(f"🤖 AI suggested category: {suggested_category}")
                return suggested_category
            else:
                logger.warning(f"AI suggested invalid category: {suggested_category}")
                return None
                
        except Exception as e:
            logger.error(f"AI categorization failed: {e}")
            return None
    
    def categorize_expense(self, expense: Dict) -> ExpenseCategory:
        """
        Categorize a single expense using both AI and rule-based methods
        
        Args:
            expense: Dictionary containing expense details
                    Expected keys: description, memo, merchant, amount, etc.
                    
        Returns:
            ExpenseCategory object with categorization results
        """
        description = expense.get('description', '').upper()
        memo = expense.get('memo', '').upper()
        merchant = expense.get('merchant', '').upper()
        combined_text = f"{description} {memo} {merchant}"
        
        # STEP 1: Try AI-enhanced categorization first
        ai_suggested_category = self.get_ai_category_suggestion(expense)
        ai_match = None
        
        if ai_suggested_category:
            # Find the config for the AI suggested category
            for config in self.categories.values():
                if config.category == ai_suggested_category:
                    ai_match = config
                    break
        
        # STEP 2: Rule-based keyword matching
        best_match = None
        best_confidence = 0.0
        
        # Check each category for keyword matches
        for category_key, config in self.categories.items():
            matches = 0
            total_keywords = len(config.keywords)
            
            if total_keywords == 0:  # Skip categories with no keywords
                continue
            
            for keyword in config.keywords:
                if keyword.upper() in combined_text:
                    matches += 1
            
            if matches > 0:
                # Calculate confidence based on keyword matches
                base_confidence = matches / total_keywords
                confidence = min(base_confidence + config.confidence_boost, 1.0)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = config
        
        # STEP 3: Choose best categorization method
        final_category = None
        final_confidence = 0.0
        final_details = "Needs Classification"
        
        if ai_match and best_match:
            # Both AI and rules found matches - choose based on confidence
            if ai_match.category == best_match.category:
                # AI and rules agree - high confidence
                final_category = ai_match.category
                final_details = ai_match.details + " (AI + Rules)"
                final_confidence = min(best_confidence + 0.3, 1.0)  # Boost for agreement
            elif best_confidence > 0.7:
                # High confidence rule match
                final_category = best_match.category
                final_details = best_match.details + " (Rules)"
                final_confidence = best_confidence
            else:
                # Use AI suggestion with moderate confidence
                final_category = ai_match.category
                final_details = ai_match.details + " (AI)"
                final_confidence = 0.75  # Moderate AI confidence
        elif ai_match:
            # Only AI found a match
            final_category = ai_match.category
            final_details = ai_match.details + " (AI)"
            final_confidence = 0.7  # Good AI confidence
        elif best_match:
            # Only rules found a match
            final_category = best_match.category
            final_details = best_match.details + " (Rules)"
            final_confidence = best_confidence
        else:
            # No matches found - use default
            final_category = 'BD: Other Costs'
            final_details = 'Needs Classification'
            final_confidence = 0.3
        
        # Extract additional information
        location = self.extract_location(f"{description} {memo}")
        client_name = self.extract_client_name(f"{description} {memo}")
        business_type = self.determine_business_type(combined_text, expense.get('email_account'))
        
        # Determine if manual review is needed
        needs_review = 1 if final_confidence < 0.6 else 0
        
        return ExpenseCategory(
            category=final_category,
            details=final_details,
            confidence=final_confidence,
            needs_review=needs_review,
            location=location,
            client_name=client_name,
            business_type=business_type
        )
    
    def batch_categorize_expenses(self, expenses: List[Dict]) -> List[Dict]:
        """
        Batch categorize multiple expenses
        
        Args:
            expenses: List of expense dictionaries
            
        Returns:
            List of expenses with categorization added
        """
        categorized_expenses = []
        
        for expense in expenses:
            try:
                category_result = self.categorize_expense(expense)
                
                # Add categorization results to expense
                categorized_expense = expense.copy()
                categorized_expense.update({
                    'category': category_result.category,
                    'details': category_result.details,
                    'confidence': category_result.confidence,
                    'needs_review': category_result.needs_review,
                    'location': category_result.location,
                    'client_name': category_result.client_name,
                    'business_type': category_result.business_type
                })
                
                categorized_expenses.append(categorized_expense)
                
            except Exception as e:
                logger.error(f"Error categorizing expense {expense.get('id', 'unknown')}: {e}")
                # Add default categorization on error
                error_expense = expense.copy()
                error_expense.update({
                    'category': 'BD: Other Costs',
                    'details': 'Classification Error',
                    'confidence': 0.1,
                    'needs_review': 1,
                    'location': None,
                    'client_name': None,
                    'business_type': 'BD'
                })
                categorized_expenses.append(error_expense)
        
        return categorized_expenses
    
    def get_category_statistics(self, expenses: List[Dict]) -> Dict:
        """
        Get statistics about categorized expenses
        
        Args:
            expenses: List of categorized expenses
            
        Returns:
            Dictionary with categorization statistics
        """
        stats = {
            'total_expenses': len(expenses),
            'needs_review': 0,
            'high_confidence': 0,
            'medium_confidence': 0,
            'low_confidence': 0,
            'categories': {},
            'business_types': {}
        }
        
        for expense in expenses:
            confidence = expense.get('confidence', 0)
            category = expense.get('category', 'Unknown')
            business_type = expense.get('business_type', 'Unknown')
            
            # Review statistics
            if expense.get('needs_review', 0):
                stats['needs_review'] += 1
            
            # Confidence statistics
            if confidence >= 0.8:
                stats['high_confidence'] += 1
            elif confidence >= 0.5:
                stats['medium_confidence'] += 1
            else:
                stats['low_confidence'] += 1
            
            # Category statistics
            if category not in stats['categories']:
                stats['categories'][category] = 0
            stats['categories'][category] += 1
            
            # Business type statistics
            if business_type not in stats['business_types']:
                stats['business_types'][business_type] = 0
            stats['business_types'][business_type] += 1
        
        return stats

# Usage example and testing
def main():
    """Example usage of the expense categorizer"""
    categorizer = ExpenseCategorizer()
    
    # Sample expenses for testing NetSuite categories
    sample_expenses = [
        {
            'id': 'exp_1',
            'description': 'CHEVRON GAS STATION',
            'memo': 'Gas for client visit to Nashville',
            'merchant': 'Chevron',
            'amount': 45.67,
            'email_account': 'brian@downhome.com'
        },
        {
            'id': 'exp_2',
            'description': 'DEL FRISCOS STEAKHOUSE',
            'memo': 'Dinner with potential client John Smith',
            'merchant': 'Del Friscos',
            'amount': 127.50,
            'email_account': 'brian@downhome.com'
        },
        {
            'id': 'exp_3',
            'description': 'VEGAS HOTEL ACCOMMODATION',
            'memo': 'NFR event production location',
            'merchant': 'Vegas Hotel',
            'amount': 299.00,
            'email_account': 'brian@musiccityrodeo.com'
        },
        {
            'id': 'exp_4',
            'description': 'ADOBE CREATIVE CLOUD',
            'memo': 'Monthly software subscription',
            'merchant': 'Adobe',
            'amount': 52.99,
            'email_account': 'kaplan.brian@gmail.com'
        },
        {
            'id': 'exp_5',
            'description': 'UBER RIDE',
            'memo': 'Transportation to client meeting',
            'merchant': 'Uber',
            'amount': 23.45,
            'email_account': 'brian@downhome.com'
        },
        {
            'id': 'exp_6',
            'description': 'EQUIPMENT RENTAL',
            'memo': 'Camera equipment for shoot',
            'merchant': 'Pro Video Rentals',
            'amount': 450.00,
            'email_account': 'kaplan.brian@gmail.com'
        }
    ]
    
    # Categorize expenses
    categorized = categorizer.batch_categorize_expenses(sample_expenses)
    
    # Print results
    for expense in categorized:
        print(f"\nExpense ID: {expense['id']}")
        print(f"Description: {expense['description']}")
        print(f"Category: {expense['category']}")
        print(f"Details: {expense['details']}")
        print(f"Confidence: {expense['confidence']:.2f}")
        print(f"Needs Review: {'Yes' if expense['needs_review'] else 'No'}")
        if expense['location']:
            print(f"Location: {expense['location']}")
        if expense['client_name']:
            print(f"Client: {expense['client_name']}")
        print(f"Business Type: {expense['business_type']}")
    
    # Print statistics
    stats = categorizer.get_category_statistics(categorized)
    print(f"\n\nCategorization Statistics:")
    print(f"Total Expenses: {stats['total_expenses']}")
    print(f"Needs Review: {stats['needs_review']}")
    print(f"High Confidence: {stats['high_confidence']}")
    print(f"Categories: {stats['categories']}")

if __name__ == "__main__":
    main() 
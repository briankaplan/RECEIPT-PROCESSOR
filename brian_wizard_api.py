"""
Brian's Personal AI Financial Wizard - API Endpoints
Integration with Flask app for comprehensive expense management
"""

import os
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from brian_financial_wizard import BrianFinancialWizard, ReceiptIntelligence
from email_receipt_detector import EmailReceiptDetector

logger = logging.getLogger(__name__)

# Create Blueprint for Brian's Wizard endpoints
brian_wizard_bp = Blueprint('brian_wizard', __name__, url_prefix='/api/brian')

@brian_wizard_bp.route('/analyze-expense', methods=['POST'])
def analyze_expense():
    """
    Brian's AI expense analysis with business context understanding
    """
    try:
        data = request.get_json()
        expense_data = data.get('expense', {})
        
        # Initialize Brian's Financial Wizard
        wizard = BrianFinancialWizard()
        
        # Perform comprehensive analysis
        analysis = wizard.smart_expense_categorization(expense_data)
        
        return jsonify({
            'success': True,
            'analysis': {
                'merchant': analysis.merchant,
                'amount': analysis.amount,
                'category': analysis.category,
                'business_type': analysis.business_type,
                'confidence': analysis.confidence,
                'purpose': analysis.purpose,
                'tax_deductible': analysis.tax_deductible,
                'needs_review': analysis.needs_review,
                'auto_approved': analysis.auto_approved,
                'receipt_source': analysis.receipt_source,
                'business_context': {
                    'down_home': analysis.business_type == 'down_home',
                    'music_city_rodeo': analysis.business_type == 'mcr',
                    'personal': analysis.business_type == 'personal'
                }
            },
            'recommendations': {
                'should_approve': analysis.auto_approved,
                'confidence_level': 'high' if analysis.confidence > 0.8 else 'medium' if analysis.confidence > 0.6 else 'low',
                'review_reason': 'High amount' if analysis.amount > 500 else 'Low confidence' if analysis.confidence < 0.8 else None
            }
        })
        
    except Exception as e:
        logger.error(f"Brian's expense analysis failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@brian_wizard_bp.route('/scan-emails', methods=['POST'])
def scan_emails():
    """
    Scan emails for receipts with automatic AI categorization
    """
    try:
        # Handle both JSON and form data to prevent 415 errors
        if request.is_json and request.get_json():
            data = request.get_json()
        elif request.form:
            data = request.form.to_dict()
            # Convert form data to expected format
            data['email_accounts'] = []  # Form data won't have complex structures
            data['days_back'] = int(data.get('days_back', 30))
            data['auto_download'] = data.get('auto_download', 'true').lower() == 'true'
        else:
            data = {
                'email_accounts': [],
                'days_back': 30,
                'auto_download': True
            }
        
        # Email scanning parameters
        email_accounts = data.get('email_accounts', [])
        days_back = data.get('days_back', 30)
        auto_download = data.get('auto_download', True)
        
        # Initialize systems
        detector = EmailReceiptDetector()
        wizard = BrianFinancialWizard()
        
        all_receipts = []
        total_processed = 0
        
        # Process each email account
        for account_info in email_accounts:
            email = account_info.get('email')
            # Note: In production, use OAuth instead of passwords
            password = account_info.get('password')
            
            if not email or not password:
                continue
            
            # Scan for receipts
            receipts = detector.scan_emails_for_receipts(email, password, days_back)
            
            # Process each receipt with Brian's Wizard
            for receipt in receipts:
                expense_data = {
                    'merchant': receipt.merchant_detected or 'Unknown Merchant',
                    'amount': receipt.amount_detected or 0,
                    'description': receipt.email_subject,
                    'date': receipt.email_date,
                    'source': f'email_{receipt.receipt_type}'
                }
                
                # AI analysis
                analysis = wizard.smart_expense_categorization(expense_data)
                
                # Download receipt if available and requested
                receipt_content = None
                if auto_download and receipt.download_url:
                    receipt_content = detector.download_receipt_from_link(
                        receipt.download_url, 
                        receipt.merchant_detected
                    )
                
                processed_receipt = {
                    'id': f"email_{total_processed}",
                    'email_info': {
                        'account': email,
                        'subject': receipt.email_subject,
                        'from': receipt.email_from,
                        'date': receipt.email_date.isoformat(),
                        'type': receipt.receipt_type,
                        'confidence': receipt.confidence
                    },
                    'expense_analysis': {
                        'merchant': analysis.merchant,
                        'amount': analysis.amount,
                        'category': analysis.category,
                        'business_type': analysis.business_type,
                        'purpose': analysis.purpose,
                        'confidence': analysis.confidence,
                        'auto_approved': analysis.auto_approved,
                        'needs_review': analysis.needs_review
                    },
                    'receipt_data': {
                        'download_url': receipt.download_url,
                        'attachment_name': receipt.attachment_name,
                        'has_content': receipt_content is not None,
                        'content_size': len(receipt_content) if receipt_content else 0
                    },
                    'brian_insights': {
                        'business_context': analysis.business_type,
                        'tax_implications': 'deductible' if analysis.tax_deductible else 'personal',
                        'approval_status': 'auto' if analysis.auto_approved else 'review'
                    }
                }
                
                all_receipts.append(processed_receipt)
                total_processed += 1
        
        # Generate summary statistics
        summary = {
            'total_receipts': len(all_receipts),
            'by_business_type': {
                'down_home': len([r for r in all_receipts if r['expense_analysis']['business_type'] == 'down_home']),
                'music_city_rodeo': len([r for r in all_receipts if r['expense_analysis']['business_type'] == 'mcr']),
                'personal': len([r for r in all_receipts if r['expense_analysis']['business_type'] == 'personal'])
            },
            'auto_approved': len([r for r in all_receipts if r['expense_analysis']['auto_approved']]),
            'needs_review': len([r for r in all_receipts if r['expense_analysis']['needs_review']]),
            'total_amount': sum(r['expense_analysis']['amount'] for r in all_receipts),
            'tax_deductible_amount': sum(
                r['expense_analysis']['amount'] for r in all_receipts 
                if r['brian_insights']['tax_implications'] == 'deductible'
            )
        }
        
        return jsonify({
            'success': True,
            'summary': summary,
            'receipts': all_receipts
        })
        
    except Exception as e:
        logger.error(f"Email receipt scanning failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@brian_wizard_bp.route('/train', methods=['POST'])
def train_wizard():
    """
    Train Brian's Wizard from user corrections and feedback
    """
    try:
        data = request.get_json()
        
        # Training data
        original_analysis = data.get('original_analysis', {})
        corrections = data.get('corrections', {})
        user_feedback = data.get('feedback', '')
        
        # Initialize wizard
        wizard = BrianFinancialWizard()
        
        # Create original ReceiptIntelligence object
        original = ReceiptIntelligence(
            merchant=original_analysis.get('merchant', ''),
            amount=original_analysis.get('amount', 0),
            date=datetime.now(),
            category=original_analysis.get('category', ''),
            business_type=original_analysis.get('business_type', ''),
            confidence=original_analysis.get('confidence', 0),
            purpose=original_analysis.get('purpose', ''),
            tax_deductible=original_analysis.get('tax_deductible', True),
            needs_review=original_analysis.get('needs_review', False),
            auto_approved=original_analysis.get('auto_approved', False),
            receipt_source=original_analysis.get('receipt_source', 'manual'),
            raw_data=original_analysis
        )
        
        # Apply corrections
        corrected_category = corrections.get('category', original.category)
        corrected_business_type = corrections.get('business_type', original.business_type)
        
        # Train the wizard
        wizard.learn_from_correction(
            original, 
            corrected_category, 
            corrected_business_type, 
            user_feedback
        )
        
        return jsonify({
            'success': True,
            'message': f'Brian\'s Wizard learned from correction: {original.merchant} -> {corrected_category}',
            'learning_summary': {
                'merchant': original.merchant,
                'original_category': original.category,
                'corrected_category': corrected_category,
                'original_business': original.business_type,
                'corrected_business': corrected_business_type,
                'confidence_improvement': 'Learning pattern stored for future transactions'
            }
        })
        
    except Exception as e:
        logger.error(f"Wizard training failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@brian_wizard_bp.route('/profile', methods=['GET'])
def get_profile():
    """
    Get Brian's business profile and context settings
    """
    try:
        wizard = BrianFinancialWizard()
        profile = wizard.profile
        
        return jsonify({
            'success': True,
            'profile': {
                'name': profile.name,
                'businesses': {
                    'down_home': {
                        'role': profile.down_home_role,
                        'description': profile.down_home_business,
                        'keywords': profile.business_keywords.get('down_home', [])
                    },
                    'music_city_rodeo': {
                        'role': profile.mcr_role,
                        'description': profile.mcr_business,
                        'keywords': profile.business_keywords.get('mcr', [])
                    }
                },
                'personal': {
                    'family_members': profile.family_members,
                    'interests': profile.personal_interests,
                    'keywords': profile.personal_keywords
                }
            },
            'learning_stats': {
                'patterns_learned': len(wizard.learning_patterns.get('merchant_patterns', {})),
                'category_overrides': len(wizard.learning_patterns.get('category_overrides', {})),
                'auto_approval_rules': len(wizard.learning_patterns.get('auto_approval_rules', []))
            }
        })
        
    except Exception as e:
        logger.error(f"Profile retrieval failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@brian_wizard_bp.route('/business-context/<merchant>', methods=['GET'])
def analyze_merchant_context(merchant):
    """
    Analyze specific merchant for business context
    """
    try:
        wizard = BrianFinancialWizard()
        
        # Analyze merchant context
        business_type = wizard._determine_business_context(merchant, "", 0)
        
        # Check learned patterns
        learned_pattern = wizard._check_learned_patterns(merchant, 0, "")
        
        return jsonify({
            'success': True,
            'merchant': merchant,
            'analysis': {
                'business_type': business_type,
                'learned_pattern': learned_pattern is not None,
                'pattern_details': learned_pattern if learned_pattern else None,
                'context_confidence': 0.9 if learned_pattern else 0.6
            },
            'recommendations': {
                'suggested_category': learned_pattern.get('category') if learned_pattern else None,
                'auto_approve': business_type in ['down_home', 'mcr'] and learned_pattern is not None
            }
        })
        
    except Exception as e:
        logger.error(f"Merchant context analysis failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Health check for Brian's systems
@brian_wizard_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check for Brian's Financial Wizard system
    """
    try:
        # Test wizard initialization
        wizard = BrianFinancialWizard()
        detector = EmailReceiptDetector()
        
        # Test basic functionality
        test_expense = {
            'merchant': 'test merchant',
            'amount': 50.0,
            'description': 'test expense',
            'date': datetime.now()
        }
        
        analysis = wizard.smart_expense_categorization(test_expense)
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'components': {
                'financial_wizard': 'operational',
                'email_detector': 'operational',
                'ai_analysis': 'functional',
                'learning_system': 'active'
            },
            'test_results': {
                'analysis_successful': True,
                'confidence_score': analysis.confidence,
                'business_type_detected': analysis.business_type
            }
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@brian_wizard_bp.route('/conversation', methods=['POST'])
def ultimate_ai_conversation():
    """
    🎙️ ULTIMATE AI CONVERSATION WIZARD
    Natural language expense management - "Would you like to do your expenses..."
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        # Parse the conversation context
        conversation_analysis = analyze_user_intent(user_message)
        
        # Generate intelligent response based on context
        if conversation_analysis['intent'] == 'expense_report_request':
            return handle_expense_report_conversation(conversation_analysis)
        elif conversation_analysis['intent'] == 'missing_receipt_handling':
            return handle_missing_receipt_conversation(conversation_analysis)
        elif conversation_analysis['intent'] == 'business_separation':
            return handle_business_separation_conversation(conversation_analysis)
        else:
            return initiate_expense_conversation()
            
    except Exception as e:
        logger.error(f"AI conversation failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'fallback_response': "I'm here to help with your expenses! What would you like me to do?"
        }), 500

def analyze_user_intent(message):
    """🧠 Analyze user's natural language intent"""
    import re
    from datetime import datetime, timedelta
    
    message_lower = message.lower()
    
    # Parse date ranges with multiple formats
    date_range = None
    date_patterns = [
        # "July 1, 2024 - July 1, 2025"
        r'(\w+ \d+,?\s*\d{4})\s*-\s*(\w+ \d+,?\s*\d{4})',
        # "7/1/2024 - 7/1/2025"  
        r'(\d{1,2}/\d{1,2}/\d{4})\s*-\s*(\d{1,2}/\d{1,2}/\d{4})',
        # "Jan 2024 to Dec 2024"
        r'(\w+ \d{4})\s*(?:to|-)\s*(\w+ \d{4})',
        # Special cases
        r'(last year|this year|last month|this month|last quarter)'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            if 'last year' in match.group(0):
                current_year = datetime.now().year
                date_range = {
                    'start': f'{current_year - 1}-01-01',
                    'end': f'{current_year - 1}-12-31',
                    'description': 'Last year',
                    'parsed_from': match.group(0)
                }
            elif 'this year' in match.group(0):
                current_year = datetime.now().year
                date_range = {
                    'start': f'{current_year}-01-01',
                    'end': f'{current_year}-12-31', 
                    'description': 'This year',
                    'parsed_from': match.group(0)
                }
            elif len(match.groups()) >= 2:
                date_range = {
                    'start': match.group(1),
                    'end': match.group(2),
                    'description': f'{match.group(1)} to {match.group(2)}',
                    'parsed_from': match.group(0)
                }
            break
    
    # Parse business types
    business_types = []
    if 'down home' in message_lower or 'downhome' in message_lower:
        business_types.append('down_home')
    if 'music city rodeo' in message_lower or 'mcr' in message_lower:
        business_types.append('mcr')  
    if 'personal' in message_lower:
        business_types.append('personal')
    if 'all 3' in message_lower or 'all three' in message_lower or 'separate reports' in message_lower:
        business_types = ['down_home', 'mcr', 'personal']
    if not business_types:
        business_types = ['down_home', 'mcr', 'personal']  # Default to all
    
    # Determine intent
    intent = 'greeting'
    if date_range and business_types:
        intent = 'expense_report_request'
    elif 'missing' in message_lower and 'receipt' in message_lower:
        intent = 'missing_receipt_handling'
    elif 'separate' in message_lower and 'report' in message_lower:
        intent = 'business_separation'
    elif any(word in message_lower for word in ['expense', 'report', 'tax', 'business']):
        intent = 'expense_related'
    
    return {
        'intent': intent,
        'date_range': date_range,
        'business_types': business_types,
        'raw_message': message,
        'confidence': 0.9 if date_range else 0.6
    }

def handle_expense_report_conversation(analysis):
    """Handle complete expense report request with dates and business types"""
    from bson import ObjectId
    
    try:
        date_range = analysis['date_range']
        business_types = analysis['business_types']
        
        # Generate reports for each business type
        reports = {}
        total_missing_receipts = 0
        
        for business_type in business_types:
            report = generate_business_expense_report(date_range, business_type)
            reports[business_type] = report
            total_missing_receipts += len(report.get('missing_receipts', []))
        
        # Prepare AI response
        response = {
            'success': True,
            'understood': {
                'date_range': date_range['description'],
                'business_types': [bt.replace('_', ' ').title() for bt in business_types],
                'separate_reports': len(business_types) > 1
            },
            'reports': reports,
            'summary': {
                'total_businesses': len(business_types),
                'total_missing_receipts': total_missing_receipts,
                'reports_ready': True
            }
        }
        
        # Generate conversational response
        if total_missing_receipts > 0:
            response['ai_message'] = f"✅ I've generated your expense reports for {date_range['description']}!\n\n"
            response['ai_message'] += f"📊 **Reports Created:** {len(business_types)} separate business reports\n"
            response['ai_message'] += f"⚠️ **Found {total_missing_receipts} missing receipts** - would you like me to:\n"
            response['ai_message'] += "• Search Gmail for missing receipts?\n"
            response['ai_message'] += "• Check Google Photos for receipt images?\n" 
            response['ai_message'] += "• Upload missing receipts manually?\n"
            response['ai_message'] += "• Generate reports without missing receipts?"
            
            response['next_actions'] = [
                {'action': 'search_gmail', 'label': '📧 Search Gmail for Missing Receipts'},
                {'action': 'search_photos', 'label': '📷 Search Google Photos'}, 
                {'action': 'manual_upload', 'label': '📁 Upload Missing Receipts'},
                {'action': 'generate_anyway', 'label': '📄 Generate Reports Now'}
            ]
            
            # List specific missing receipts
            response['missing_receipts'] = []
            for business_type, report in reports.items():
                for missing in report.get('missing_receipts', [])[:3]:  # Top 3 per business
                    response['missing_receipts'].append({
                        'business': business_type.replace('_', ' ').title(),
                        'merchant': missing.get('merchant_name', 'Unknown'),
                        'amount': f"${abs(missing.get('amount', 0)):,.2f}",
                        'date': missing.get('date', '').strftime('%m/%d/%Y') if hasattr(missing.get('date'), 'strftime') else str(missing.get('date', '')),
                        'suggested_search': f"Search Gmail for '{missing.get('merchant_name', '')}' receipt"
                    })
        else:
            response['ai_message'] = f"🎉 **Perfect!** All receipts found for {date_range['description']}!\n\n"
            response['ai_message'] += f"📊 **{len(business_types)} Complete Reports Ready**\n"
            response['ai_message'] += "Would you like me to:\n"
            response['ai_message'] += "• Export to Google Sheets?\n"
            response['ai_message'] += "• Generate PDF reports?\n"
            response['ai_message'] += "• Email reports to your accountant?\n"
            response['ai_message'] += "• Create tax-ready summaries?"
            
            response['next_actions'] = [
                {'action': 'export_sheets', 'label': '📊 Export to Google Sheets'},
                {'action': 'generate_pdf', 'label': '📄 Generate PDF Reports'},
                {'action': 'email_accountant', 'label': '📧 Email to Accountant'},
                {'action': 'tax_summary', 'label': '🧾 Create Tax Summary'}
            ]
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Expense report conversation failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'ai_message': "I had trouble generating your expense reports. Let me try a different approach - what specific date range do you need?"
        }), 500

def generate_business_expense_report(date_range, business_type):
    """Generate comprehensive expense report for specific business and date range"""
    try:
        from pymongo import MongoClient
        from bson import ObjectId
        
        # Connect to MongoDB (you'll need to import this from your main app)
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        client = MongoClient(mongo_uri)
        db = client['expense']
        
        # Parse date range
        from dateutil import parser
        try:
            start_date = parser.parse(date_range['start'])
            end_date = parser.parse(date_range['end'])
        except:
            # Fallback to current year if parsing fails
            from datetime import datetime
            start_date = datetime(datetime.now().year, 1, 1)
            end_date = datetime(datetime.now().year, 12, 31)
        
        # Query transactions for this business and date range
        query = {
            'business_type': business_type,
            'date': {
                '$gte': start_date,
                '$lte': end_date
            }
        }
        
        transactions = list(db.bank_transactions.find(query).sort('date', -1))
        
        # Calculate totals
        total_amount = sum(abs(t.get('amount', 0)) for t in transactions)
        total_count = len(transactions)
        
        # Find missing receipts (transactions without receipts)
        missing_receipts = [
            t for t in transactions 
            if not t.get('receipt_matched') and t.get('amount', 0) < 0  # Only expenses
        ]
        
        # Category breakdown
        categories = {}
        for t in transactions:
            cat = t.get('category', 'Uncategorized')
            if cat not in categories:
                categories[cat] = {'count': 0, 'amount': 0, 'transactions': []}
            categories[cat]['count'] += 1
            categories[cat]['amount'] += abs(t.get('amount', 0))
            categories[cat]['transactions'].append(t)
        
        # Monthly breakdown
        months = {}
        for t in transactions:
            if t.get('date'):
                month_key = t['date'].strftime('%Y-%m') if hasattr(t['date'], 'strftime') else 'unknown'
                if month_key not in months:
                    months[month_key] = {'count': 0, 'amount': 0}
                months[month_key]['count'] += 1
                months[month_key]['amount'] += abs(t.get('amount', 0))
        
        return {
            'business_type': business_type,
            'business_display': business_type.replace('_', ' ').title(),
            'date_range': date_range,
            'totals': {
                'total_amount': total_amount,
                'total_count': total_count,
                'average_transaction': total_amount / total_count if total_count > 0 else 0,
                'tax_deductible_amount': sum(abs(t.get('amount', 0)) for t in transactions if t.get('tax_deductible', True))
            },
            'missing_receipts': missing_receipts,
            'missing_count': len(missing_receipts),
            'missing_amount': sum(abs(r.get('amount', 0)) for r in missing_receipts),
            'categories': categories,
            'monthly_breakdown': months,
            'top_merchants': get_top_merchants(transactions),
            'completion_status': {
                'receipts_found': total_count - len(missing_receipts),
                'receipts_missing': len(missing_receipts),
                'completion_percentage': ((total_count - len(missing_receipts)) / total_count * 100) if total_count > 0 else 100
            }
        }
        
    except Exception as e:
        logger.error(f"Report generation failed for {business_type}: {e}")
        return {
            'business_type': business_type,
            'error': str(e),
            'totals': {'total_amount': 0, 'total_count': 0},
            'missing_receipts': [],
            'categories': {}
        }

def get_top_merchants(transactions):
    """Get top merchants by spending"""
    merchants = {}
    for t in transactions:
        merchant = t.get('merchant_name') or t.get('counterparty', {}).get('name') or 'Unknown'
        if merchant not in merchants:
            merchants[merchant] = {'count': 0, 'amount': 0}
        merchants[merchant]['count'] += 1
        merchants[merchant]['amount'] += abs(t.get('amount', 0))
    
    # Sort by amount and return top 10
    return sorted(
        [{'merchant': k, **v} for k, v in merchants.items()],
        key=lambda x: x['amount'],
        reverse=True
    )[:10]

def handle_missing_receipt_conversation(analysis):
    """Handle missing receipt conversation flow"""
    return jsonify({
        'success': True,
        'ai_message': "I can help you find missing receipts! Let me search your emails and photos for any receipt images.",
        'next_actions': [
            {'action': 'search_gmail', 'label': '📧 Search Gmail for Receipts'},
            {'action': 'search_photos', 'label': '📷 Search Google Photos'},
            {'action': 'manual_upload', 'label': '📁 Upload Receipts Manually'}
        ]
    })

def handle_business_separation_conversation(analysis):
    """Handle business separation conversation flow"""
    return jsonify({
        'success': True,
        'ai_message': "I'll help you separate your business expenses! I can generate separate reports for Down Home Media and Music City Rodeo.",
        'next_actions': [
            {'action': 'separate_down_home', 'label': '🏢 Down Home Media Report'},
            {'action': 'separate_mcr', 'label': '🎵 Music City Rodeo Report'},
            {'action': 'separate_all', 'label': '📊 All Business Reports'}
        ]
    })

def initiate_expense_conversation():
    """Initiate general expense conversation"""
    return jsonify({
        'success': True,
        'ai_message': "Hi! I'm Brian's AI Assistant. I can help you with:\n\n• Expense categorization\n• Receipt matching\n• Business expense reports\n• Tax preparation\n\nWhat would you like me to help you with today?",
        'quick_actions': [
            {'action': 'expense_report', 'label': '📊 Generate Expense Report'},
            {'action': 'receipt_matching', 'label': '🔍 Match Receipts'},
            {'action': 'business_separation', 'label': '🏢 Separate Business Expenses'},
            {'action': 'tax_prep', 'label': '🧾 Tax Preparation'}
        ]
    })

def register_brian_wizard_blueprint(app):
    """
    Register Brian's Financial Wizard blueprint with Flask app
    """
    try:
        app.register_blueprint(brian_wizard_bp)
        logger.info("🧙‍♂️ Brian's Financial Wizard API blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register Brian's Wizard blueprint: {e}")
        raise 
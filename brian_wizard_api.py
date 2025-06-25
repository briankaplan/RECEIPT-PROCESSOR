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
        data = request.get_json()
        
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
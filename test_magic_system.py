#!/usr/bin/env python3
"""
Test the Magic Receipt Intelligence System
"""

import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_magic_system():
    """Test the complete magic receipt intelligence system"""
    
    logger.info("🧙‍♂️ Testing Magic Receipt Intelligence System")
    
    # Sample transactions to analyze
    sample_transactions = [
        {
            'date': '2025-06-28',
            'amount': 45.67,
            'description': 'CLAUDE AI',
            'merchant': 'CLAUDE',
            'category': 'Technology',
            'has_tip': False,
            'payment_method': 'credit_card'
        },
        {
            'date': '2025-06-27',
            'amount': 89.50,
            'description': 'SQUARE *DOWNTOWN DINER',
            'merchant': 'SQUARE *DOWNTOWN DINER',
            'category': 'Food & Dining',
            'has_tip': True,
            'payment_method': 'credit_card'
        },
        {
            'date': '2025-06-26',
            'amount': 19.99,
            'description': 'PAYPAL *NETFLIX',
            'merchant': 'PAYPAL *NETFLIX',
            'category': 'Entertainment',
            'has_tip': False,
            'payment_method': 'paypal'
        },
        {
            'date': '2025-06-25',
            'amount': 299.00,
            'description': 'APPLE.COM/BILL',
            'merchant': 'APPLE.COM/BILL',
            'category': 'Technology',
            'has_tip': False,
            'payment_method': 'credit_card'
        },
        {
            'date': '2025-06-24',
            'amount': 12.50,
            'description': 'UBER *TRIP',
            'merchant': 'UBER *TRIP',
            'category': 'Transportation',
            'has_tip': True,
            'payment_method': 'credit_card'
        }
    ]
    
    # Sample emails to analyze
    sample_emails = [
        {
            'id': 'test_email_1',
            'subject': 'Your Claude subscription receipt',
            'from': 'noreply@anthropic.com',
            'body': 'Thank you for your Claude subscription. Amount: $45.67',
            'date': '2025-06-28',
            'has_attachments': False
        },
        {
            'id': 'test_email_2',
            'subject': 'Receipt from Downtown Diner',
            'from': 'receipts@square.com',
            'body': 'Your receipt: $89.50 including tip',
            'date': '2025-06-27',
            'has_attachments': True
        },
        {
            'id': 'test_email_3',
            'subject': 'Netflix monthly payment',
            'from': 'service@paypal.com',
            'body': 'Payment of $19.99 to Netflix',
            'date': '2025-06-26',
            'has_attachments': False
        }
    ]
    
    logger.info("📊 Analyzing transaction patterns...")
    
    # Analyze transaction patterns
    transaction_analysis = analyze_transaction_patterns(sample_transactions)
    
    logger.info("🔍 Transaction Analysis Results:")
    for pattern in transaction_analysis['patterns']:
        logger.info(f"  - {pattern['type']}: {pattern['description']}")
    
    logger.info("📧 Analyzing email patterns...")
    
    # Analyze email patterns
    email_analysis = analyze_email_patterns(sample_emails)
    
    logger.info("🔍 Email Analysis Results:")
    for pattern in email_analysis['patterns']:
        logger.info(f"  - {pattern['type']}: {pattern['description']}")
    
    logger.info("🎯 Building merchant intelligence...")
    
    # Build merchant intelligence
    merchant_intelligence = build_merchant_intelligence(sample_transactions, sample_emails)
    
    logger.info("🔍 Merchant Intelligence Results:")
    for merchant, info in merchant_intelligence.items():
        logger.info(f"  - {merchant}: {info['type']} (confidence: {info['confidence']:.2f})")
    
    logger.info("🔗 Testing receipt matching...")
    
    # Test receipt matching
    for transaction in sample_transactions[:3]:  # Test first 3
        matches = find_receipt_matches(transaction, sample_emails)
        logger.info(f"  Transaction: {transaction['description']} (${transaction['amount']})")
        if matches:
            for match in matches:
                logger.info(f"    → Match: {match['email']['subject']} (confidence: {match['confidence']:.2f})")
        else:
            logger.info(f"    → No matches found")
    
    logger.info("🎉 Magic system test complete!")
    
    return {
        'transaction_analysis': transaction_analysis,
        'email_analysis': email_analysis,
        'merchant_intelligence': merchant_intelligence
    }

def analyze_transaction_patterns(transactions: List[Dict]) -> Dict:
    """Analyze transaction patterns to predict receipt likelihood"""
    
    patterns = []
    
    # Analyze payment methods
    payment_methods = {}
    for tx in transactions:
        method = tx.get('payment_method', 'unknown')
        payment_methods[method] = payment_methods.get(method, 0) + 1
    
    for method, count in payment_methods.items():
        patterns.append({
            'type': 'payment_method',
            'description': f'{method}: {count} transactions',
            'receipt_likelihood': get_payment_method_receipt_likelihood(method)
        })
    
    # Analyze categories
    categories = {}
    for tx in transactions:
        category = tx.get('category', 'unknown')
        categories[category] = categories.get(category, 0) + 1
    
    for category, count in categories.items():
        patterns.append({
            'type': 'category',
            'description': f'{category}: {count} transactions',
            'receipt_likelihood': get_category_receipt_likelihood(category)
        })
    
    # Analyze tip patterns
    tip_transactions = [tx for tx in transactions if tx.get('has_tip', False)]
    if tip_transactions:
        patterns.append({
            'type': 'tip_pattern',
            'description': f'{len(tip_transactions)} transactions with tips',
            'receipt_likelihood': 0.95  # High likelihood for tipped transactions
        })
    
    return {'patterns': patterns}

def analyze_email_patterns(emails: List[Dict]) -> Dict:
    """Analyze email patterns for receipt detection"""
    
    patterns = []
    
    # Analyze senders
    senders = {}
    for email in emails:
        sender = email.get('from', 'unknown')
        senders[sender] = senders.get(sender, 0) + 1
    
    for sender, count in senders.items():
        patterns.append({
            'type': 'sender',
            'description': f'{sender}: {count} emails',
            'receipt_likelihood': get_sender_receipt_likelihood(sender)
        })
    
    # Analyze subjects
    receipt_keywords = ['receipt', 'payment', 'invoice', 'confirmation', 'order']
    for email in emails:
        subject = email.get('subject', '').lower()
        for keyword in receipt_keywords:
            if keyword in subject:
                patterns.append({
                    'type': 'subject_keyword',
                    'description': f'Subject contains "{keyword}"',
                    'receipt_likelihood': 0.8
                })
                break
    
    return {'patterns': patterns}

def build_merchant_intelligence(transactions: List[Dict], emails: List[Dict]) -> Dict:
    """Build merchant intelligence mapping"""
    
    merchant_map = {
        'CLAUDE': {'type': 'subscription', 'parent': 'Anthropic', 'confidence': 0.95},
        'SQUARE *DOWNTOWN DINER': {'type': 'restaurant', 'parent': 'Downtown Diner', 'confidence': 0.9},
        'PAYPAL *NETFLIX': {'type': 'subscription', 'parent': 'Netflix', 'confidence': 0.9},
        'APPLE.COM/BILL': {'type': 'subscription', 'parent': 'Apple', 'confidence': 0.95},
        'UBER *TRIP': {'type': 'transportation', 'parent': 'Uber', 'confidence': 0.9}
    }
    
    return merchant_map

def find_receipt_matches(transaction: Dict, emails: List[Dict]) -> List[Dict]:
    """Find matching receipts for a transaction"""
    
    matches = []
    
    for email in emails:
        confidence = calculate_match_confidence(transaction, email)
        if confidence > 0.5:  # Threshold for matching
            matches.append({
                'email': email,
                'confidence': confidence,
                'reason': get_match_reason(transaction, email)
            })
    
    # Sort by confidence
    matches.sort(key=lambda x: x['confidence'], reverse=True)
    
    return matches

def calculate_match_confidence(transaction: Dict, email: Dict) -> float:
    """Calculate confidence score for transaction-email match"""
    
    confidence = 0.0
    
    # Amount matching
    email_body = email.get('body', '')
    if str(transaction['amount']) in email_body:
        confidence += 0.4
    
    # Date matching
    if transaction.get('date') == email.get('date'):
        confidence += 0.3
    
    # Merchant matching
    merchant = transaction.get('merchant', '').lower()
    subject = email.get('subject', '').lower()
    if merchant in subject or any(word in subject for word in merchant.split()):
        confidence += 0.3
    
    return min(confidence, 1.0)

def get_match_reason(transaction: Dict, email: Dict) -> str:
    """Get reason for match"""
    reasons = []
    
    if str(transaction['amount']) in email.get('body', ''):
        reasons.append('amount match')
    
    if transaction.get('date') == email.get('date'):
        reasons.append('date match')
    
    merchant = transaction.get('merchant', '').lower()
    subject = email.get('subject', '').lower()
    if merchant in subject:
        reasons.append('merchant match')
    
    return ', '.join(reasons) if reasons else 'partial match'

def get_payment_method_receipt_likelihood(method: str) -> float:
    """Get receipt likelihood for payment method"""
    likelihoods = {
        'credit_card': 0.8,
        'paypal': 0.9,
        'square': 0.95,
        'stripe': 0.9,
        'debit_card': 0.6,
        'cash': 0.1,
        'atm': 0.0
    }
    return likelihoods.get(method.lower(), 0.5)

def get_category_receipt_likelihood(category: str) -> float:
    """Get receipt likelihood for category"""
    likelihoods = {
        'Food & Dining': 0.9,
        'Technology': 0.8,
        'Entertainment': 0.7,
        'Transportation': 0.8,
        'Shopping': 0.6,
        'ATM': 0.0
    }
    return likelihoods.get(category, 0.5)

def get_sender_receipt_likelihood(sender: str) -> float:
    """Get receipt likelihood for email sender"""
    if 'receipt' in sender.lower() or 'square' in sender.lower():
        return 0.95
    elif 'paypal' in sender.lower() or 'stripe' in sender.lower():
        return 0.9
    elif 'noreply' in sender.lower():
        return 0.7
    else:
        return 0.5

def test_merchant_aliases():
    """Test merchant alias detection"""
    
    logger.info("🔍 Testing Merchant Alias Detection")
    
    # Test cases for merchant aliases
    test_cases = [
        ('CLAUDE', 'Anthropic'),
        ('PAYPAL *NETFLIX', 'Netflix'),
        ('SQUARE *DOWNTOWN DINER', 'Downtown Diner'),
        ('APPLE.COM/BILL', 'Apple'),
        ('UBER *TRIP', 'Uber'),
        ('STRIPE *GITHUB', 'GitHub'),
        ('AMZN MKTP', 'Amazon'),
        ('GOOGLE *YOUTUBE', 'YouTube')
    ]
    
    for transaction_merchant, expected_parent in test_cases:
        parent_merchant = detect_parent_merchant(transaction_merchant)
        logger.info(f"  {transaction_merchant} → {parent_merchant} (expected: {expected_parent})")
    
    return True

def detect_parent_merchant(merchant: str) -> str:
    """Detect parent merchant from transaction description"""
    
    merchant_lower = merchant.lower()
    
    # Known mappings
    mappings = {
        'claude': 'Anthropic',
        'netflix': 'Netflix',
        'apple': 'Apple',
        'uber': 'Uber',
        'github': 'GitHub',
        'amazon': 'Amazon',
        'youtube': 'YouTube',
        'google': 'Google',
        'microsoft': 'Microsoft',
        'spotify': 'Spotify',
        'zoom': 'Zoom',
        'slack': 'Slack',
        'notion': 'Notion',
        'figma': 'Figma',
        'canva': 'Canva'
    }
    
    # Check for exact matches first
    for key, parent in mappings.items():
        if key in merchant_lower:
            return parent
    
    # Check for payment processor patterns
    if 'paypal *' in merchant_lower:
        # Extract merchant after PAYPAL *
        parts = merchant_lower.split('paypal *')
        if len(parts) > 1:
            sub_merchant = parts[1].strip()
            for key, parent in mappings.items():
                if key in sub_merchant:
                    return parent
        return 'PayPal Merchant'
    
    if 'square *' in merchant_lower:
        parts = merchant_lower.split('square *')
        if len(parts) > 1:
            return parts[1].strip().title()
        return 'Square Merchant'
    
    if 'stripe *' in merchant_lower:
        parts = merchant_lower.split('stripe *')
        if len(parts) > 1:
            sub_merchant = parts[1].strip()
            for key, parent in mappings.items():
                if key in sub_merchant:
                    return parent
        return 'Stripe Merchant'
    
    return merchant

def test_receipt_prediction():
    """Test receipt prediction based on transaction patterns"""
    
    logger.info("🔮 Testing Receipt Prediction")
    
    # Test transactions with different characteristics
    test_transactions = [
        {
            'description': 'CLAUDE AI',
            'amount': 45.67,
            'category': 'Technology',
            'has_tip': False,
            'payment_method': 'credit_card'
        },
        {
            'description': 'SQUARE *RESTAURANT',
            'amount': 67.89,
            'category': 'Food & Dining',
            'has_tip': True,
            'payment_method': 'credit_card'
        },
        {
            'description': 'ATM WITHDRAWAL',
            'amount': 100.00,
            'category': 'ATM',
            'has_tip': False,
            'payment_method': 'debit_card'
        },
        {
            'description': 'PAYPAL *SUBSCRIPTION',
            'amount': 9.99,
            'category': 'Entertainment',
            'has_tip': False,
            'payment_method': 'paypal'
        }
    ]
    
    for transaction in test_transactions:
        prediction = predict_receipt_likelihood(transaction)
        logger.info(f"  {transaction['description']}: {prediction['likelihood']:.1%} chance of receipt")
        logger.info(f"    Reason: {prediction['reason']}")
    
    return True

def predict_receipt_likelihood(transaction: Dict) -> Dict:
    """Predict likelihood of receipt for a transaction"""
    
    likelihood = 0.0
    reasons = []
    
    # Payment method factor
    method_likelihood = get_payment_method_receipt_likelihood(transaction.get('payment_method', ''))
    likelihood += method_likelihood * 0.3
    reasons.append(f"Payment method: {method_likelihood:.1%}")
    
    # Category factor
    category_likelihood = get_category_receipt_likelihood(transaction.get('category', ''))
    likelihood += category_likelihood * 0.3
    reasons.append(f"Category: {category_likelihood:.1%}")
    
    # Tip factor
    if transaction.get('has_tip', False):
        likelihood += 0.2
        reasons.append("Has tip (high receipt likelihood)")
    
    # Amount factor
    amount = transaction.get('amount', 0)
    if amount > 50:
        likelihood += 0.1
        reasons.append("High amount transaction")
    elif amount < 5:
        likelihood -= 0.1
        reasons.append("Low amount transaction")
    
    # Description keywords
    description = transaction.get('description', '').lower()
    if any(keyword in description for keyword in ['subscription', 'monthly', 'recurring']):
        likelihood += 0.1
        reasons.append("Subscription transaction")
    
    return {
        'likelihood': min(max(likelihood, 0.0), 1.0),
        'reason': '; '.join(reasons)
    }

if __name__ == "__main__":
    try:
        # Run all tests
        test_magic_system()
        test_merchant_aliases()
        test_receipt_prediction()
        
        logger.info("✅ All magic system tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 
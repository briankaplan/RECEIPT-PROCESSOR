#!/usr/bin/env python3
"""
Enhanced Transaction Processing Utilities
Comprehensive transaction analysis, categorization, and processing functions
"""

import os
import json
import logging
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# ============================================================================
# 🛠️ TRANSACTION PROCESSING UTILITIES
# ============================================================================

def get_sort_field(sort_by):
    """Get MongoDB sort field from sort parameter"""
    sort_fields = {
        'date': 'date',
        'amount': 'amount',
        'merchant': 'merchant_name',
        'category': 'category',
        'match_confidence': 'match_confidence',
        'created': 'synced_at'
    }
    return sort_fields.get(sort_by, 'date')

def build_transaction_query(filter_type=None, search=None, category_filter=None, 
                           amount_min=None, amount_max=None, date_from=None, 
                           date_to=None, business_type=None, match_status=None):
    """Build MongoDB query from filter parameters"""
    query = {}
    
    # Filter by type
    if filter_type == 'matched':
        query['receipt_matched'] = True
    elif filter_type == 'unmatched':
        query['receipt_matched'] = {'$ne': True}
    elif filter_type == 'expenses':
        query['amount'] = {'$lt': 0}
    elif filter_type == 'income':
        query['amount'] = {'$gt': 0}
    elif filter_type == 'split':
        query['is_split'] = True
    elif filter_type == 'needs_review':
        query['needs_review'] = True
    elif filter_type == 'recent':
        query['date'] = {'$gte': datetime.utcnow() - timedelta(days=7)}
    
    # Search across multiple fields
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query['$or'] = [
            {'description': search_regex},
            {'merchant_name': search_regex},
            {'counterparty.name': search_regex},
            {'category': search_regex},
            {'business_type': search_regex},
            {'account_name': search_regex},
            {'transaction_id': search_regex}
        ]
    
    # Category filter
    if category_filter:
        query['category'] = category_filter
    
    # Business type filter
    if business_type:
        query['business_type'] = business_type
    
    # Amount range
    if amount_min or amount_max:
        amount_query = {}
        if amount_min:
            amount_query['$gte'] = float(amount_min)
        if amount_max:
            amount_query['$lte'] = float(amount_max)
        query['amount'] = amount_query
    
    # Date range
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query['$gte'] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        if date_to:
            date_query['$lte'] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        query['date'] = date_query
    
    # Match status
    if match_status == 'matched':
        query['receipt_matched'] = True
    elif match_status == 'unmatched':
        query['receipt_matched'] = {'$ne': True}
    elif match_status == 'needs_review':
        query['needs_review'] = True
    
    return query

def categorize_and_analyze_transaction(transaction):
    """AI-powered transaction categorization and business type detection"""
    from datetime import datetime
    import re
    
    # Extract basic info
    merchant_name = transaction.get('merchant_name', '').lower() if transaction.get('merchant_name') else ''
    description = transaction.get('description', '').lower() if transaction.get('description') else ''
    counterparty_name = transaction.get('counterparty', {}).get('name', '').lower() if transaction.get('counterparty') else ''
    
    # Use the best available merchant identifier
    merchant = merchant_name or counterparty_name or description
    amount = abs(transaction.get('amount', 0))
    
    # Initialize result
    result = {
        'category': 'Other',
        'business_type': 'Personal',
        'confidence': 0.5,
        'needs_review': False,
        'review_reasons': [],
        'tags': []
    }
    
    # Enhanced categorization rules
    category_rules = {
        'Food & Beverage': {
            'keywords': ['starbucks', 'coffee', 'restaurant', 'food', 'dining', 'pizza', 'burger', 'cafe', 'bar', 'brewery', 'doordash', 'ubereats', 'grubhub', 'chipotle', 'subway', 'mcdonalds'],
            'confidence': 0.9
        },
        'Transportation': {
            'keywords': ['shell', 'gas', 'fuel', 'exxon', 'chevron', 'bp', 'uber', 'lyft', 'taxi', 'parking', 'toll', 'metro', 'transit', 'airline', 'flight'],
            'confidence': 0.95
        },
        'Shopping': {
            'keywords': ['target', 'walmart', 'amazon', 'store', 'shop', 'retail', 'mall', 'market', 'costco', 'best buy', 'home depot', 'lowes'],
            'confidence': 0.85
        },
        'Technology': {
            'keywords': ['apple', 'microsoft', 'google', 'software', 'app store', 'steam', 'adobe', 'netflix', 'spotify', 'zoom', 'dropbox'],
            'confidence': 0.9
        },
        'Healthcare': {
            'keywords': ['medical', 'doctor', 'pharmacy', 'health', 'dental', 'hospital', 'clinic', 'cvs', 'walgreens', 'urgent care'],
            'confidence': 0.95
        },
        'Utilities': {
            'keywords': ['electric', 'water', 'gas', 'internet', 'phone', 'cable', 'utility', 'power', 'comcast', 'verizon', 'att'],
            'confidence': 0.95
        },
        'Entertainment': {
            'keywords': ['movie', 'theater', 'cinema', 'concert', 'game', 'sport', 'ticket', 'event', 'amusement', 'spotify', 'netflix'],
            'confidence': 0.8
        },
        'Business Services': {
            'keywords': ['office', 'supplies', 'staples', 'fedex', 'ups', 'shipping', 'consulting', 'legal', 'accounting', 'marketing'],
            'confidence': 0.85
        }
    }
    
    # Find best category match
    best_score = 0
    for category, rules in category_rules.items():
        score = 0
        matched_keywords = []
        
        for keyword in rules['keywords']:
            if keyword in merchant or keyword in description:
                score += 1
                matched_keywords.append(keyword)
        
        if score > 0:
            confidence = min(score / len(rules['keywords']) * rules['confidence'], 1.0)
            if confidence > best_score:
                best_score = confidence
                result['category'] = category
                result['confidence'] = confidence
                result['tags'].extend(matched_keywords[:3])  # Top 3 matched keywords
    
    # Business type detection based on merchant patterns
    business_keywords = {
        'down_home': ['soho house', 'production', 'media', 'creative', 'studio', 'film', 'video', 'editing', 'design'],
        'mcr': ['rodeo', 'vegas', 'nfr', 'country', 'western', 'nashville', 'music city', 'entertainment', 'event'],
        'personal': ['grocery', 'home', 'personal', 'family', 'medical', 'pharmacy', 'gas', 'utilities']
    }
    
    for business_type, keywords in business_keywords.items():
        for keyword in keywords:
            if keyword in merchant or keyword in description:
                result['business_type'] = business_type.replace('_', ' ').title()
                break
    
    # Review flags
    if amount > 1000:
        result['needs_review'] = True
        result['review_reasons'].append('High amount transaction')
    
    if result['confidence'] < 0.7:
        result['needs_review'] = True
        result['review_reasons'].append('Low categorization confidence')
    
    # Special merchant handling
    if 'apple' in merchant and amount < 10:
        result['category'] = 'Technology'
        result['business_type'] = 'Personal'
        result['confidence'] = 0.9
    
    return result

def process_transaction_for_display(transaction):
    """Process transaction for enhanced display with all computed fields"""
    # Convert datetime objects
    for date_field in ['date', 'synced_at', 'matched_at', 'webhook_received_at']:
        if date_field in transaction and hasattr(transaction[date_field], 'isoformat'):
            transaction[date_field] = transaction[date_field].isoformat()
    
    amount = transaction.get('amount', 0)
    txn_date = datetime.fromisoformat(transaction['date'].replace('Z', '+00:00')) if transaction.get('date') else datetime.now()
    days_ago = (datetime.now() - txn_date).days
    
    enhanced_txn = {
        **transaction,
        '_id': str(transaction.get('_id', '')),
        'formatted_amount': f"${abs(amount):,.2f}",
        'amount_type': 'expense' if amount < 0 else 'income',
        'amount_color': 'danger' if amount < 0 else 'success',
        'formatted_date': txn_date.strftime('%m/%d/%Y'),
        'formatted_datetime': txn_date.strftime('%m/%d/%Y %I:%M %p'),
        'merchant_display': extract_display_merchant(transaction),
        'days_ago': days_ago,
        'is_recent': days_ago <= 7,
        'is_this_month': txn_date.month == datetime.now().month and txn_date.year == datetime.now().year,
        'data_source': 'Real-time Webhook' if transaction.get('source') == 'webhook' else 'Historical Sync',
        'data_source_icon': '⚡' if transaction.get('source') == 'webhook' else '📊',
        'match_status_display': get_match_status_display(transaction),
        'match_status_color': get_match_status_color(transaction),
        'confidence_display': f"{int(transaction.get('match_confidence', 0) * 100)}%" if transaction.get('match_confidence') else 'N/A',
        'confidence_level': get_confidence_level(transaction.get('match_confidence', 0)),
        'category_display': transaction.get('category', 'Uncategorized').title(),
        'business_type_display': transaction.get('business_type', 'Unknown').title(),
        'split_indicator': get_split_indicator(transaction),
        'review_indicator': get_review_indicator(transaction),
        'tags_display': ', '.join(transaction.get('tags', [])),
        'account_display': transaction.get('account_name', 'Unknown Account'),
        'status_display': transaction.get('status', 'pending').title(),
        'status_color': get_status_color(transaction.get('status', 'pending'))
    }
    
    return enhanced_txn

def process_receipt_for_display(receipt):
    """Process receipt for enhanced display"""
    for date_field in ['date', 'processed_at', 'matched_at']:
        if date_field in receipt and hasattr(receipt[date_field], 'isoformat'):
            receipt[date_field] = receipt[date_field].isoformat()
    
    receipt['_id'] = str(receipt.get('_id', ''))
    receipt['formatted_amount'] = f"${receipt.get('total_amount', 0):,.2f}"
    receipt['formatted_date'] = datetime.fromisoformat(receipt['date'].replace('Z', '+00:00')).strftime('%m/%d/%Y') if receipt.get('date') else 'Unknown'
    
    return receipt

def get_match_status_display(transaction):
    """Get display text for match status"""
    if transaction.get('receipt_matched'):
        confidence = transaction.get('match_confidence', 0)
        if confidence >= 0.9:
            return '✅ Perfect Match'
        elif confidence >= 0.75:
            return '✅ Good Match'
        else:
            return '✅ Matched'
    elif transaction.get('needs_review'):
        return '⚠️ Needs Review'
    else:
        return '⏳ No Receipt'

def get_match_status_color(transaction):
    """Get Bootstrap color for match status"""
    if transaction.get('receipt_matched'):
        confidence = transaction.get('match_confidence', 0)
        if confidence >= 0.9:
            return 'success'
        elif confidence >= 0.75:
            return 'info'
        else:
            return 'primary'
    elif transaction.get('needs_review'):
        return 'warning'
    else:
        return 'secondary'

def get_confidence_level(confidence):
    """Get confidence level category"""
    if confidence >= 0.9:
        return 'high'
    elif confidence >= 0.7:
        return 'medium'
    else:
        return 'low'

def get_split_indicator(transaction):
    """Get split indicator display"""
    if transaction.get('is_split'):
        split_count = len(transaction.get('split_transactions', []))
        return f'🔄 Split ({split_count})'
    elif transaction.get('parent_transaction_id'):
        return '🔗 Part of Split'
    else:
        return ''

def get_review_indicator(transaction):
    """Get review indicator display"""
    if transaction.get('needs_review'):
        reasons = transaction.get('review_reasons', [])
        return f'⚠️ Review ({len(reasons)})'
    else:
        return ''

def get_status_color(status):
    """Get Bootstrap color for transaction status"""
    status_colors = {
        'pending': 'warning',
        'posted': 'success',
        'failed': 'danger',
        'cancelled': 'secondary',
        'processing': 'info'
    }
    return status_colors.get(status.lower(), 'secondary')

def extract_merchant_name(transaction):
    """Extract the best merchant name from transaction data"""
    # Try merchant_name first
    if transaction.get('merchant_name'):
        return clean_merchant_name(transaction['merchant_name'])
    
    # Try counterparty name
    counterparty = transaction.get('counterparty', {})
    if counterparty and counterparty.get('name'):
        return clean_merchant_name(counterparty['name'])
    
    # Fall back to description
    description = transaction.get('description', '')
    if description:
        return clean_merchant_name(description)
    
    return "Unknown Merchant"

def clean_merchant_name(name):
    """Clean and standardize merchant names"""
    if not name:
        return "Unknown"
    
    name = name.strip()
    
    # Remove common payment processor prefixes
    prefixes_to_remove = [
        'SQ *', 'TST*', 'SP *', 'PAYPAL *', 'VENMO *', 'ZELLE *',
        'CHECKCARD ', 'DEBIT CARD ', 'CREDIT CARD '
    ]
    
    for prefix in prefixes_to_remove:
        if name.upper().startswith(prefix):
            name = name[len(prefix):].strip()
    
    # Capitalize properly
    name = ' '.join(word.capitalize() for word in name.split())
    
    return name

def extract_display_merchant(transaction):
    """Extract merchant name optimized for display"""
    merchant = extract_merchant_name(transaction)
    
    # Truncate very long names
    if len(merchant) > 25:
        merchant = merchant[:22] + "..."
    
    return merchant

def calculate_comprehensive_stats():
    """Calculate comprehensive transaction statistics"""
    try:
        # This would integrate with your MongoDB client
        # For now, return basic structure
        return {
            "total_transactions": 0,
            "total_expenses": 0,
            "total_income": 0,
            "net_amount": 0,
            "matched_transactions": 0,
            "unmatched_transactions": 0,
            "match_percentage": 0,
            "category_breakdown": {},
            "business_type_breakdown": {},
            "completion_percentage": {
                "categorized": 0,
                "matched": 0,
                "processed": 0
            }
        }
        
    except Exception as e:
        logger.error(f"Stats calculation error: {e}")
        return {}

def can_transaction_be_split(transaction):
    """Check if transaction can be split"""
    if transaction.get('is_split'):
        return False  # Already split
    
    amount = abs(transaction.get('amount', 0))
    if amount < 20:  # Too small to split meaningfully
        return False
    
    return True

def assess_transaction_review_status(transaction):
    """Assess what review actions are needed"""
    review_items = []
    
    if not transaction.get('category') or transaction.get('category') == 'Other':
        review_items.append('Needs categorization')
    
    if not transaction.get('receipt_matched') and transaction.get('amount', 0) < 0:
        review_items.append('Missing receipt')
    
    if transaction.get('ai_confidence', 1) < 0.7:
        review_items.append('Low AI confidence')
    
    if abs(transaction.get('amount', 0)) > 500:
        review_items.append('High value transaction')
    
    return {
        'needs_review': len(review_items) > 0,
        'review_items': review_items,
        'priority': 'high' if len(review_items) >= 3 else 'medium' if len(review_items) >= 2 else 'low'
    }

def find_similar_transactions(transaction, limit=5):
    """Find similar transactions for pattern analysis (placeholder)"""
    # This would integrate with your MongoDB client
    return []

def generate_transaction_insights(transaction, similar_transactions):
    """Generate intelligent insights about transaction patterns"""
    insights = []
    amount = abs(transaction.get('amount', 0))
    
    # Pattern insights
    if len(similar_transactions) >= 3:
        avg_amount = sum(abs(t.get('amount', 0)) for t in similar_transactions) / len(similar_transactions)
        if abs(amount - avg_amount) > (avg_amount * 0.3):
            insights.append(f"Amount differs significantly from typical ${avg_amount:.2f} for this merchant")
        else:
            insights.append(f"Consistent with typical spending pattern (avg: ${avg_amount:.2f})")
    
    # Merchant insights
    merchant = extract_merchant_name(transaction)
    if 'apple' in merchant.lower():
        insights.append("Apple transactions often contain both business and personal items")
    elif 'amazon' in merchant.lower():
        insights.append("Amazon purchases may need business/personal classification")
    
    # Amount insights
    if amount > 500:
        insights.append("High-value transaction - consider if receipt and business justification needed")
    
    return insights

def generate_transaction_recommendations(transaction):
    """Generate actionable recommendations"""
    recommendations = []
    
    # Receipt recommendations
    if not transaction.get('receipt_matched') and transaction.get('amount', 0) < 0:
        recommendations.append({
            'type': 'receipt',
            'priority': 'high',
            'action': 'Upload receipt',
            'description': 'Add receipt for this expense to ensure proper documentation'
        })
    
    # Categorization recommendations
    if not transaction.get('category') or transaction.get('category') == 'Other':
        recommendations.append({
            'type': 'category',
            'priority': 'medium',
            'action': 'Categorize transaction',
            'description': 'Assign proper category for better expense tracking'
        })
    
    # Review recommendations
    if transaction.get('ai_confidence', 1) < 0.7:
        recommendations.append({
            'type': 'review',
            'priority': 'low',
            'action': 'Review categorization',
            'description': 'AI categorization confidence is low - manual review recommended'
        })
    
    return recommendations

def create_export_row(transaction, split_data=None):
    """Create export row with comprehensive data"""
    # Use split data if provided, otherwise main transaction
    data = split_data if split_data else transaction
    amount = data.get('amount', transaction.get('amount', 0))
    
    row = {
        'Transaction ID': transaction.get('transaction_id', ''),
        'Date': datetime.fromisoformat(transaction['date'].replace('Z', '+00:00')).strftime('%m/%d/%Y') if transaction.get('date') else '',
        'Description': transaction.get('description', ''),
        'Merchant': extract_merchant_name(transaction),
        'Amount': amount,
        'Formatted Amount': f"${abs(amount):,.2f}",
        'Type': 'Expense' if amount < 0 else 'Income',
        'Category': data.get('category', transaction.get('category', 'Uncategorized')),
        'Business Type': data.get('business_type', transaction.get('business_type', 'Unknown')),
        'Account': transaction.get('account_name', 'Unknown'),
        'Bank': transaction.get('bank_name', 'Unknown'),
        'Receipt Matched': 'Yes' if transaction.get('receipt_matched') else 'No',
        'Match Confidence': f"{int(transaction.get('match_confidence', 0) * 100)}%" if transaction.get('match_confidence') else 'N/A',
        'Data Source': 'Webhook' if transaction.get('source') == 'webhook' else 'API',
        'Split Type': data.get('split_type', '') if split_data else ('Parent' if transaction.get('is_split') else ''),
        'Split Percentage': f"{data.get('percentage', 0):.1f}%" if split_data else '',
        'Needs Review': 'Yes' if transaction.get('needs_review') else 'No',
        'Review Reasons': ', '.join(transaction.get('review_reasons', [])),
        'Tags': ', '.join(transaction.get('tags', [])),
        'AI Confidence': f"{int(transaction.get('ai_confidence', 0) * 100)}%" if transaction.get('ai_confidence') else 'N/A',
        'Sync Date': datetime.fromisoformat(transaction['synced_at'].replace('Z', '+00:00')).strftime('%m/%d/%Y %H:%M') if transaction.get('synced_at') else '',
        'Status': transaction.get('status', 'Unknown').title()
    }
    
    return row

def generate_csv_export(export_data):
    """Generate CSV string from export data"""
    if not export_data:
        return ""
    
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
    writer.writeheader()
    writer.writerows(export_data)
    
    return output.getvalue()

def export_to_google_sheets(export_data):
    """Export data to Google Sheets (placeholder - implement with your Google Sheets integration)"""
    # This would integrate with your existing Google Sheets functionality
    return {
        'url': 'https://docs.google.com/spreadsheets/d/placeholder',
        'success': True,
        'message': 'Export to Google Sheets functionality to be implemented'
    }

def execute_manual_split(transaction, splits):
    """Execute manual transaction split (placeholder - needs MongoDB integration)"""
    try:
        # This would integrate with your MongoDB client
        split_transactions = []
        
        for i, split in enumerate(splits):
            split_txn = {
                'transaction_id': f"{transaction['transaction_id']}_split_{i+1}",
                'parent_transaction_id': transaction['transaction_id'],
                'amount': split['amount'],
                'date': transaction['date'],
                'description': split.get('description', f"Split {i+1} of {transaction.get('description', '')}"),
                'merchant_name': transaction.get('merchant_name'),
                'category': split.get('category', 'Other'),
                'business_type': split.get('business_type', 'Unknown'),
                'split_type': split.get('split_type', 'manual'),
                'split_percentage': split.get('percentage', 0),
                'is_split_child': True,
                'source': transaction.get('source', 'manual_split'),
                'synced_at': datetime.utcnow(),
                'split_method': 'manual',
                'ai_processed': True
            }
            
            split_txn['_id'] = f"split_{i+1}"  # Placeholder
            split_transactions.append(split_txn)
        
        return {
            'success': True,
            'splits': split_transactions
        }
        
    except Exception as e:
        logger.error(f"Manual split execution error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def should_split_transaction(transaction):
    """Determine if a transaction should be split based on amount and merchant"""
    amount = abs(transaction.get('amount', 0))
    merchant = transaction.get('merchant_name', '').lower() if transaction.get('merchant_name') else ''
    description = transaction.get('description', '').lower() if transaction.get('description') else ''
    
    # Split criteria
    if amount > 500:  # Large transactions likely have multiple items
        return True
        
    # Known merchants that often have mixed business/personal items
    split_merchants = ['amazon', 'target', 'walmart', 'costco', 'apple', 'google']
    for split_merchant in split_merchants:
        if split_merchant in merchant or split_merchant in description:
            return True
    
    return False

def split_transaction_intelligently(transaction):
    """Intelligently split a transaction based on business logic"""
    amount = abs(transaction.get('amount', 0))
    merchant = transaction.get('merchant_name', '').lower() if transaction.get('merchant_name') else ''
    description = transaction.get('description', '').lower() if transaction.get('description') else ''
    
    splits = []
    
    # Default split for large transactions
    if amount > 500:
        business_portion = amount * 0.6  # 60% business
        personal_portion = amount * 0.4  # 40% personal
        
        splits.append({
            'amount': business_portion,
            'business_type': 'Down Home',
            'category': 'Business',
            'description': f'Business portion of {merchant}'
        })
        
        splits.append({
            'amount': personal_portion,
            'business_type': 'Personal',
            'category': 'Personal',
            'description': f'Personal portion of {merchant}'
        })
    
    # Amazon-specific splitting
    elif 'amazon' in merchant:
        # Assume 70% business for Amazon purchases
        business_portion = amount * 0.7
        personal_portion = amount * 0.3
        
        splits.append({
            'amount': business_portion,
            'business_type': 'Down Home',
            'category': 'Technology',
            'description': f'Amazon business supplies'
        })
        
        splits.append({
            'amount': personal_portion,
            'business_type': 'Personal',
            'category': 'Shopping',
            'description': f'Amazon personal items'
        })
    
    # Apple-specific splitting
    elif 'apple' in merchant:
        if amount > 50:  # Likely hardware
            splits.append({
                'amount': amount * 0.8,
                'business_type': 'Down Home',
                'category': 'Technology',
                'description': 'Apple business equipment'
            })
            splits.append({
                'amount': amount * 0.2,
                'business_type': 'Personal',
                'category': 'Technology',
                'description': 'Apple personal use'
            })
        else:  # Likely apps/subscriptions
            splits.append({
                'amount': amount,
                'business_type': 'Personal',
                'category': 'Technology',
                'description': 'Apple apps/subscriptions'
            })
    
    return splits if splits else [transaction]  # Return original if no splits determined

def find_perfect_receipt_match(transaction):
    """Find perfect receipt matches for a transaction using advanced matching algorithms"""
    from datetime import datetime, timedelta
    import os
    
    # This is a placeholder function for advanced receipt matching
    # In production, this would connect to the database and use sophisticated matching
    matches = []
    
    # Basic matching criteria
    amount = abs(transaction.get('amount', 0))
    date = transaction.get('date')
    merchant = transaction.get('merchant_name', '') if transaction.get('merchant_name') else ''
    
    # Simulated receipt matching logic
    # In real implementation, this would query the receipts database
    match_criteria = {
        'amount_tolerance': 0.01,  # $0.01 tolerance
        'date_tolerance_days': 3,   # 3 days tolerance
        'merchant_similarity_threshold': 0.8
    }
    
    # Return empty list for now - this function would be implemented
    # with actual database queries in production
    return matches

def calculate_perfect_match_score(transaction, receipt):
    """Calculate match score between a transaction and receipt"""
    score = 0.0
    max_score = 100.0
    
    # Amount matching (40 points)
    txn_amount = abs(transaction.get('amount', 0))
    receipt_amount = abs(receipt.get('total_amount', 0))
    
    if txn_amount > 0 and receipt_amount > 0:
        amount_diff = abs(txn_amount - receipt_amount)
        amount_tolerance = 0.01  # $0.01 tolerance
        
        if amount_diff <= amount_tolerance:
            score += 40  # Perfect amount match
        elif amount_diff <= txn_amount * 0.05:  # Within 5%
            score += 30
        elif amount_diff <= txn_amount * 0.10:  # Within 10%
            score += 20
        else:
            score += max(0, 20 - (amount_diff / txn_amount * 100))
    
    # Date matching (30 points)
    from datetime import datetime, timedelta
    
    txn_date = transaction.get('date')
    receipt_date = receipt.get('date')
    
    if txn_date and receipt_date:
        if isinstance(txn_date, str):
            txn_date = datetime.fromisoformat(txn_date.replace('Z', '+00:00'))
        if isinstance(receipt_date, str):
            receipt_date = datetime.fromisoformat(receipt_date.replace('Z', '+00:00'))
        
        date_diff = abs((txn_date - receipt_date).days)
        
        if date_diff == 0:
            score += 30  # Same day
        elif date_diff <= 1:
            score += 25  # Within 1 day
        elif date_diff <= 3:
            score += 20  # Within 3 days
        elif date_diff <= 7:
            score += 10  # Within a week
        else:
            score += max(0, 10 - date_diff)
    
    # Merchant matching (30 points)
    txn_merchant = transaction.get('merchant_name', '').lower()
    receipt_merchant = receipt.get('merchant_name', '').lower()
    
    if txn_merchant and receipt_merchant:
        # Simple similarity check
        if txn_merchant == receipt_merchant:
            score += 30  # Perfect match
        elif txn_merchant in receipt_merchant or receipt_merchant in txn_merchant:
            score += 25  # Partial match
        else:
            # Calculate basic similarity
            common_words = set(txn_merchant.split()) & set(receipt_merchant.split())
            if common_words:
                score += min(20, len(common_words) * 5)
    
    return min(score, max_score)

def process_transaction_for_display(transaction):
    """Process transaction for enhanced display with all computed fields"""
    # Convert datetime objects
    for date_field in ['date', 'synced_at', 'matched_at', 'webhook_received_at']:
        if date_field in transaction and hasattr(transaction[date_field], 'isoformat'):
            transaction[date_field] = transaction[date_field].isoformat()
    
    amount = transaction.get('amount', 0)
    txn_date = datetime.fromisoformat(transaction['date'].replace('Z', '+00:00')) if transaction.get('date') else datetime.now()
    days_ago = (datetime.now() - txn_date).days
    
    enhanced_txn = {
        **transaction,
        '_id': str(transaction.get('_id', '')),
        'formatted_amount': f"${abs(amount):,.2f}",
        'amount_type': 'expense' if amount < 0 else 'income',
        'amount_color': 'danger' if amount < 0 else 'success',
        'formatted_date': txn_date.strftime('%m/%d/%Y'),
        'formatted_datetime': txn_date.strftime('%m/%d/%Y %I:%M %p'),
        'merchant_display': extract_display_merchant(transaction),
        'days_ago': days_ago,
        'is_recent': days_ago <= 7,
        'is_this_month': txn_date.month == datetime.now().month and txn_date.year == datetime.now().year,
        'data_source': 'Real-time Webhook' if transaction.get('source') == 'webhook' else 'Historical Sync',
        'data_source_icon': '⚡' if transaction.get('source') == 'webhook' else '📊',
        'match_status_display': get_match_status_display(transaction),
        'match_status_color': get_match_status_color(transaction),
        'confidence_display': f"{int(transaction.get('match_confidence', 0) * 100)}%" if transaction.get('match_confidence') else 'N/A',
        'confidence_level': get_confidence_level(transaction.get('match_confidence', 0)),
        'category_display': transaction.get('category', 'Uncategorized').title(),
        'business_type_display': transaction.get('business_type', 'Unknown').title(),
        'split_indicator': get_split_indicator(transaction),
        'review_indicator': get_review_indicator(transaction),
        'tags_display': ', '.join(transaction.get('tags', [])),
        'account_display': transaction.get('account_name', 'Unknown Account'),
        'status_display': transaction.get('status', 'pending').title(),
        'status_color': get_status_color(transaction.get('status', 'pending'))
    }
    
    return enhanced_txn 
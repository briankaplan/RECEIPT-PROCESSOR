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
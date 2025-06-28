#!/usr/bin/env python3
"""
Helper Functions for Enhanced Receipt Processor
All missing functions needed for the application to work
"""

import os
import json
import logging
import re
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

def _get_category_analysis(mongo_client, start_date, end_date, business_type):
    """Get detailed category analysis"""
    try:
        query = {
            'date': {'$gte': start_date, '$lte': end_date},
            'amount': {'$lt': 0}
        }
        if business_type != 'all':
            query['business_type'] = business_type
        
        pipeline = [
            {'$match': query},
            {'$group': {
                '_id': '$category',
                'total_amount': {'$sum': {'$abs': '$amount'}},
                'transaction_count': {'$sum': 1},
                'avg_amount': {'$avg': {'$abs': '$amount'}}
            }},
            {'$sort': {'total_amount': -1}},
            {'$limit': 10}
        ]
        
        results = list(mongo_client.db.bank_transactions.aggregate(pipeline))
        
        categories = []
        total_amount = sum(r['total_amount'] for r in results)
        
        for result in results:
            category = result['_id'] or 'Uncategorized'
            percentage = (result['total_amount'] / total_amount * 100) if total_amount > 0 else 0
            
            categories.append({
                'category': category,
                'total_amount': round(result['total_amount'], 2),
                'transaction_count': result['transaction_count'],
                'percentage': round(percentage, 1),
                'avg_amount': round(result['avg_amount'], 2)
            })
        
        return {
            'top_categories': categories,
            'category_count': len(categories),
            'total_analyzed': total_amount
        }
        
    except Exception as e:
        logger.error(f"Category analysis error: {e}")
        return {'top_categories': [], 'category_count': 0, 'total_analyzed': 0}

def _get_spending_trends(mongo_client, start_date, end_date):
    """Get spending trends over time"""
    try:
        # Daily spending pipeline
        pipeline = [
            {'$match': {
                'date': {'$gte': start_date, '$lte': end_date},
                'amount': {'$lt': 0}
            }},
            {'$group': {
                '_id': {
                    'year': {'$year': '$date'},
                    'month': {'$month': '$date'},
                    'day': {'$dayOfMonth': '$date'}
                },
                'daily_total': {'$sum': {'$abs': '$amount'}},
                'transaction_count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}}
        ]
        
        daily_results = list(mongo_client.db.bank_transactions.aggregate(pipeline))
        
        # Calculate trend direction
        if len(daily_results) >= 2:
            recent_avg = sum(r['daily_total'] for r in daily_results[-7:]) / min(7, len(daily_results))
            earlier_avg = sum(r['daily_total'] for r in daily_results[:-7]) / max(1, len(daily_results) - 7)
            trend_direction = 'increasing' if recent_avg > earlier_avg else 'decreasing' if recent_avg < earlier_avg else 'stable'
        else:
            trend_direction = 'insufficient_data'
        
        return {
            'daily_spending': [
                {
                    'date': f"{r['_id']['year']}-{r['_id']['month']:02d}-{r['_id']['day']:02d}",
                    'amount': round(r['daily_total'], 2),
                    'transactions': r['transaction_count']
                }
                for r in daily_results[-30:]  # Last 30 days
            ],
            'trend_direction': trend_direction,
            'total_days': len(daily_results)
        }
        
    except Exception as e:
        logger.error(f"Spending trends error: {e}")
        return {'daily_spending': [], 'trend_direction': 'unknown', 'total_days': 0}

def _get_receipt_matching_stats(mongo_client, start_date, end_date):
    """Get receipt matching statistics"""
    try:
        query = {'date': {'$gte': start_date, '$lte': end_date}}
        
        # Get all transactions in period
        transactions = list(mongo_client.db.bank_transactions.find(query))
        receipts = list(mongo_client.db.receipts.find(query))
        
        total_transactions = len(transactions)
        total_receipts = len(receipts)
        
        # Count matched transactions
        matched_transactions = sum(1 for t in transactions if t.get('receipt_matched'))
        unmatched_transactions = total_transactions - matched_transactions
        
        # Calculate match rate
        match_rate = (matched_transactions / total_transactions * 100) if total_transactions > 0 else 0
        
        # Get recent matching activity
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_matches = sum(1 for t in transactions 
                           if t.get('receipt_matched') and t.get('date', datetime.min) >= week_ago)
        
        return {
            'total_transactions': total_transactions,
            'total_receipts': total_receipts,
            'matched_transactions': matched_transactions,
            'unmatched_transactions': unmatched_transactions,
            'match_rate': round(match_rate, 1),
            'recent_matches': recent_matches,
            'receipts_without_transactions': max(0, total_receipts - matched_transactions)
        }
        
    except Exception as e:
        logger.error(f"Receipt matching stats error: {e}")
        return {
            'total_transactions': 0,
            'total_receipts': 0,
            'matched_transactions': 0,
            'unmatched_transactions': 0,
            'match_rate': 0,
            'recent_matches': 0,
            'receipts_without_transactions': 0
        }

def _generate_analytics_insights(mongo_client, start_date, end_date):
    """Generate intelligent insights from financial data"""
    try:
        insights = []
        
        # Get spending data
        expenses = list(mongo_client.db.bank_transactions.find({
            'date': {'$gte': start_date, '$lte': end_date},
            'amount': {'$lt': 0}
        }))
        
        if not expenses:
            insights.append({
                'type': 'info',
                'title': 'No Spending Data',
                'message': 'No expenses found in the selected period. Start tracking your spending to get insights!',
                'priority': 'low'
            })
            return insights
        
        total_spending = sum(abs(t.get('amount', 0)) for t in expenses)
        avg_daily = total_spending / max((end_date - start_date).days, 1)
        
        # Spending pattern insights
        if avg_daily > 100:
            insights.append({
                'type': 'warning',
                'title': 'High Daily Spending',
                'message': f'Average daily spending is ${avg_daily:.2f}. Consider reviewing your expenses.',
                'priority': 'high'
            })
        
        # Category insights
        category_totals = {}
        for expense in expenses:
            category = expense.get('category', 'Uncategorized')
            if category not in category_totals:
                category_totals[category] = 0
            category_totals[category] += abs(expense.get('amount', 0))
        
        if category_totals:
            top_category = max(category_totals.items(), key=lambda x: x[1])
            top_percentage = (top_category[1] / total_spending * 100) if total_spending > 0 else 0
            
            if top_percentage > 50:
                insights.append({
                    'type': 'info',
                    'title': 'Category Concentration',
                    'message': f'{top_category[0]} accounts for {top_percentage:.1f}% of your spending.',
                    'priority': 'medium'
                })
        
        # Business vs Personal insights
        business_expenses = [e for e in expenses if e.get('business_type') != 'Personal']
        personal_expenses = [e for e in expenses if e.get('business_type') == 'Personal']
        
        business_total = sum(abs(e.get('amount', 0)) for e in business_expenses)
        personal_total = sum(abs(e.get('amount', 0)) for e in personal_expenses)
        
        if business_total > 0 and personal_total > 0:
            business_ratio = business_total / (business_total + personal_total) * 100
            insights.append({
                'type': 'info',
                'title': 'Business vs Personal',
                'message': f'Business expenses: {business_ratio:.1f}%, Personal: {100-business_ratio:.1f}%',
                'priority': 'medium'
            })
        
        # Receipt matching insights
        matched_count = sum(1 for t in expenses if t.get('receipt_matched'))
        match_rate = (matched_count / len(expenses) * 100) if expenses else 0
        
        if match_rate < 70:
            insights.append({
                'type': 'warning',
                'title': 'Low Receipt Match Rate',
                'message': f'Only {match_rate:.1f}% of transactions have receipts. Consider scanning more receipts.',
                'priority': 'medium'
            })
        
        return insights
        
    except Exception as e:
        logger.error(f"Analytics insights error: {e}")
        return [{
            'type': 'error',
            'title': 'Analysis Error',
            'message': 'Unable to generate insights due to an error.',
            'priority': 'low'
        }]

def _get_smart_recommendations(mongo_client, start_date, end_date):
    """Get smart recommendations based on financial data"""
    try:
        recommendations = []
        
        # Get recent data
        recent_transactions = list(mongo_client.db.bank_transactions.find({
            'date': {'$gte': start_date, '$lte': end_date}
        }).sort('date', -1).limit(100))
        
        if not recent_transactions:
            recommendations.append({
                'type': 'setup',
                'title': 'Connect Your Accounts',
                'message': 'Start by connecting your bank accounts to get personalized recommendations.',
                'action': 'connect_banks',
                'priority': 'high'
            })
            return recommendations
        
        # Analyze spending patterns
        expenses = [t for t in recent_transactions if t.get('amount', 0) < 0]
        total_spending = sum(abs(t.get('amount', 0)) for t in expenses)
        
        # High spending recommendation
        if total_spending > 1000:
            recommendations.append({
                'type': 'savings',
                'title': 'Review High Spending',
                'message': f'You\'ve spent ${total_spending:.2f} this period. Consider setting a budget.',
                'action': 'set_budget',
                'priority': 'medium'
            })
        
        # Receipt scanning recommendation
        matched_count = sum(1 for t in expenses if t.get('receipt_matched'))
        if matched_count < len(expenses) * 0.5:
            recommendations.append({
                'type': 'organization',
                'title': 'Scan More Receipts',
                'message': f'Only {matched_count}/{len(expenses)} transactions have receipts. Scan receipts for better tracking.',
                'action': 'scan_receipts',
                'priority': 'medium'
            })
        
        # Category optimization
        category_totals = {}
        for expense in expenses:
            category = expense.get('category', 'Uncategorized')
            if category not in category_totals:
                category_totals[category] = 0
            category_totals[category] += abs(expense.get('amount', 0))
        
        if category_totals:
            top_category = max(category_totals.items(), key=lambda x: x[1])
            if top_category[1] > total_spending * 0.4:
                recommendations.append({
                    'type': 'optimization',
                    'title': 'Diversify Spending',
                    'message': f'{top_category[0]} is your highest spending category. Consider diversifying.',
                    'action': 'review_categories',
                    'priority': 'low'
                })
        
        # Export recommendation
        if len(recent_transactions) > 50:
            recommendations.append({
                'type': 'export',
                'title': 'Export Your Data',
                'message': 'You have significant transaction data. Consider exporting to Google Sheets for analysis.',
                'action': 'export_data',
                'priority': 'low'
            })
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Smart recommendations error: {e}")
        return [{
            'type': 'error',
            'title': 'Recommendation Error',
            'message': 'Unable to generate recommendations due to an error.',
            'action': 'none',
            'priority': 'low'
        }]

def _extract_receipt_from_email(gmail_message, r2_client=None):
    """Extract receipt information from Gmail API message structure with R2 upload support"""
    try:
        if not gmail_message:
            return None
        
        # Extract headers from Gmail message
        headers = gmail_message.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
        date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        message_id = gmail_message.get('id', '')
        
        # Extract email body
        body = _extract_email_body(gmail_message)
        
        # Look for receipt indicators in subject and sender
        receipt_keywords = ['receipt', 'invoice', 'order confirmation', 'purchase', 'payment', 'confirmation']
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        
        # Check if this looks like a receipt email
        is_receipt = (
            any(keyword in subject_lower for keyword in receipt_keywords) or
            any(keyword in sender_lower for keyword in receipt_keywords) or
            any(domain in sender_lower for domain in ['paypal', 'stripe', 'square', 'amazon', 'walmart', 'target', 'noreply', 'no-reply'])
        )
        
        if not is_receipt:
            return None
        
        # Extract merchant name from sender or subject
        merchant = _extract_merchant_from_email(sender, subject, body)
        
        # Extract amount from body
        amount = _extract_amount_from_email(body, subject)
        
        # Extract date
        receipt_date = _extract_date_from_email(date_str, body)
        
        # Determine business type and category
        business_type = 'Personal'
        category = 'Uncategorized'
        
        if merchant:
            merchant_lower = merchant.lower()
            # Business type detection
            business_keywords = ['office', 'business', 'corporate', 'work', 'company']
            if any(keyword in merchant_lower for keyword in business_keywords):
                business_type = 'Down Home'
            
            # Category detection
            if any(word in merchant_lower for word in ['starbucks', 'coffee', 'restaurant', 'food', 'dining']):
                category = 'Food & Drink'
            elif any(word in merchant_lower for word in ['amazon', 'walmart', 'target', 'shop', 'store']):
                category = 'Shopping'
            elif any(word in merchant_lower for word in ['gas', 'shell', 'exxon', 'fuel', 'chevron']):
                category = 'Transportation'
            elif any(word in merchant_lower for word in ['office', 'staples', 'depot', 'supplies']):
                category = 'Office Supplies'
            elif any(word in merchant_lower for word in ['uber', 'lyft', 'taxi', 'transport']):
                category = 'Transportation'
            elif any(word in merchant_lower for word in ['hotel', 'airbnb', 'lodging']):
                category = 'Travel'
        
        # Calculate confidence based on extracted data
        confidence = 0.3  # Base confidence
        if amount and amount > 0:
            confidence += 0.3
        if merchant and merchant != 'Unknown Merchant':
            confidence += 0.2
        if receipt_date:
            confidence += 0.1
        if category != 'Uncategorized':
            confidence += 0.1
        
        # Initialize receipt data
        receipt_data = {
            'merchant': merchant or 'Unknown Merchant',
            'amount': amount or 0.0,
            'date': receipt_date,
            'category': category,
            'business_type': business_type,
            'source': 'email_extraction',
            'confidence': min(confidence, 1.0),
            'email_subject': subject,
            'email_sender': sender,
            'email_date': date_str,
            'email_id': message_id,
            'attachments': [],
            'r2_urls': [],
            'matched_transaction_id': None,
            'match_confidence': 0.0
        }
        
        # Process attachments and upload to R2 if available
        if r2_client and r2_client.is_connected():
            attachments = _extract_attachments_from_email(gmail_message, r2_client, message_id)
            if attachments:
                receipt_data['attachments'] = attachments
                receipt_data['r2_urls'] = [att['r2_url'] for att in attachments if att.get('r2_url')]
                # Boost confidence if we have attachments
                receipt_data['confidence'] = min(receipt_data['confidence'] + 0.2, 1.0)
        
        return receipt_data
        
    except Exception as e:
        logger.error(f"Email receipt extraction error: {e}")
        return None

def _extract_attachments_from_email(gmail_message, r2_client, message_id):
    """Extract and upload attachments from Gmail message to R2"""
    try:
        attachments = []
        
        def process_payload(payload):
            if 'parts' in payload:
                for part in payload['parts']:
                    process_payload(part)
            
            # Check if this part is an attachment
            filename = payload.get('filename', '')
            attachment_id = payload.get('body', {}).get('attachmentId')
            
            if filename and attachment_id:
                # Check if it's a receipt-like file
                file_ext = os.path.splitext(filename.lower())[1]
                receipt_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}
                
                if file_ext in receipt_extensions:
                    try:
                        # Download attachment
                        attachment_data = _download_gmail_attachment(gmail_message, attachment_id)
                        if attachment_data:
                            # Upload to R2
                            r2_key = _upload_attachment_to_r2(attachment_data, filename, message_id, r2_client)
                            
                            if r2_key:
                                # Generate public URL
                                r2_public_url = os.getenv('R2_PUBLIC_URL', '')
                                r2_url = f"{r2_public_url}/{r2_key}" if r2_public_url else None
                                
                                attachments.append({
                                    'filename': filename,
                                    'size': len(attachment_data),
                                    'mime_type': payload.get('mimeType', 'application/octet-stream'),
                                    'r2_key': r2_key,
                                    'r2_url': r2_url,
                                    'attachment_id': attachment_id
                                })
                                
                                logger.info(f"📎 Uploaded attachment {filename} to R2: {r2_key}")
                    
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to process attachment {filename}: {e}")
        
        if 'payload' in gmail_message:
            process_payload(gmail_message['payload'])
        
        return attachments
        
    except Exception as e:
        logger.error(f"Error extracting attachments: {e}")
        return []

def _download_gmail_attachment(gmail_message, attachment_id):
    """Download attachment data from Gmail API"""
    try:
        # This would need to be called with the Gmail service
        # For now, return None - this will be handled in the main scanning function
        return None
    except Exception as e:
        logger.error(f"Error downloading attachment: {e}")
        return None

def _upload_attachment_to_r2(attachment_data, filename, message_id, r2_client):
    """Upload attachment data to R2 storage"""
    try:
        if not attachment_data or not r2_client:
            return None
        
        # Create temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            temp_file.write(attachment_data)
            temp_path = temp_file.name
        
        try:
            # Upload to R2
            date_str = datetime.utcnow().strftime('%Y/%m/%d')
            key = f"receipts/email_attachments/{date_str}/{message_id}_{filename}"
            
            metadata = {
                'email_id': message_id,
                'original_filename': filename,
                'upload_date': datetime.utcnow().isoformat()
            }
            
            if r2_client.upload_file(temp_path, key, metadata):
                return key
            else:
                return None
                
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Error uploading to R2: {e}")
        return None

def _extract_email_body(gmail_message):
    """Extract email body from Gmail message structure"""
    try:
        body = ""
        
        def extract_from_payload(payload):
            nonlocal body
            if 'body' in payload and payload['body'].get('data'):
                try:
                    import base64
                    data = payload['body']['data']
                    decoded = base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))
                    body += decoded.decode('utf-8', errors='ignore')
                except:
                    pass
            
            if 'parts' in payload:
                for part in payload['parts']:
                    extract_from_payload(part)
        
        if 'payload' in gmail_message:
            extract_from_payload(gmail_message['payload'])
        
        return body.lower()
        
    except Exception as e:
        logger.error(f"Error extracting email body: {e}")
        return ""

def _extract_merchant_from_email(sender, subject, body):
    """Extract merchant name from email sender, subject, or body"""
    try:
        # Try to extract from sender first
        if sender:
            # Remove email domain and common prefixes
            sender_clean = sender.replace('<', '').replace('>', '')
            if '@' in sender_clean:
                sender_clean = sender_clean.split('@')[0]
            
            # Remove common prefixes
            prefixes = ['noreply', 'no-reply', 'donotreply', 'billing', 'orders', 'receipts']
            for prefix in prefixes:
                if sender_clean.lower().startswith(prefix):
                    sender_clean = sender_clean[len(prefix):]
            
            if sender_clean.strip():
                return sender_clean.strip()
        
        # Try to extract from subject
        subject_patterns = [
            r'from\s+([a-zA-Z0-9\s&]+)',
            r'receipt\s+from\s+([a-zA-Z0-9\s&]+)',
            r'invoice\s+from\s+([a-zA-Z0-9\s&]+)',
            r'order\s+from\s+([a-zA-Z0-9\s&]+)'
        ]
        
        for pattern in subject_patterns:
            match = re.search(pattern, subject, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Try to extract from body
        body_patterns = [
            r'merchant:\s*([a-zA-Z0-9\s&]+)',
            r'store:\s*([a-zA-Z0-9\s&]+)',
            r'vendor:\s*([a-zA-Z0-9\s&]+)',
            r'from\s+([a-zA-Z0-9\s&]+)'
        ]
        
        for pattern in body_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting merchant: {e}")
        return None

def _extract_amount_from_email(body, subject):
    """Extract amount from email body or subject"""
    try:
        # Combine body and subject for searching
        text = f"{subject} {body}"
        
        # Amount patterns
        amount_patterns = [
            r'total:\s*\$?([0-9,]+\.?[0-9]*)',
            r'amount:\s*\$?([0-9,]+\.?[0-9]*)',
            r'charged:\s*\$?([0-9,]+\.?[0-9]*)',
            r'payment:\s*\$?([0-9,]+\.?[0-9]*)',
            r'\$([0-9,]+\.?[0-9]*)',
            r'([0-9,]+\.?[0-9]*)\s*dollars',
            r'([0-9,]+\.?[0-9]*)\s*usd'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    amount = float(amount_str)
                    if amount > 0 and amount < 10000:  # Reasonable range
                        return amount
                except ValueError:
                    continue
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting amount: {e}")
        return None

def _extract_date_from_email(date_str, body):
    """Extract date from email date header or body"""
    try:
        # Try to parse the email date header first
        if date_str:
            try:
                import email.utils
                parsed_date = email.utils.parsedate_to_datetime(date_str)
                return parsed_date
            except:
                pass
        
        # Try to extract from body
        date_patterns = [
            r'date:\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})',
            r'([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})',
            r'([0-9]{4}-[0-9]{2}-[0-9]{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, body)
            if match:
                try:
                    date_str = match.group(1)
                    if '/' in date_str:
                        if len(date_str.split('/')[-1]) == 2:
                            receipt_date = datetime.strptime(date_str, '%m/%d/%y')
                        else:
                            receipt_date = datetime.strptime(date_str, '%m/%d/%Y')
                    else:
                        receipt_date = datetime.strptime(date_str, '%Y-%m-%d')
                    return receipt_date
                except ValueError:
                    continue
        
        # Fallback to current date
        return datetime.utcnow()
        
    except Exception as e:
        logger.error(f"Error extracting date: {e}")
        return datetime.utcnow()

# def _create_sample_receipts(mongo_client):
#     """Create sample receipt data for demonstration"""
#     try:
#         sample_receipts = [
#             ...
#         ]
#         result = mongo_client.db.receipts.insert_many(sample_receipts)
#         return result
#     except Exception as e:
#         logger.error(f"Sample receipt creation error: {e}")
#         return None

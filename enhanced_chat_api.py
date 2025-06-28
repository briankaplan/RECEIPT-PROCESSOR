#!/usr/bin/env python3
"""
Enhanced Chat API with Real AI Integration
Brian's Financial Assistant with actual intelligence and context
"""

from flask import jsonify, request
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def register_enhanced_chat_api(app, mongo_client):
    """Register enhanced chat API endpoints with real AI"""
    
    @app.route('/api/ai-chat', methods=['POST'])
    def enhanced_ai_chat():
        """
        Enhanced AI chat with real business intelligence
        """
        try:
            data = request.get_json() or {}
            message = data.get('message', '').strip()
            context = data.get('context', {})
            
            if not message:
                return jsonify({
                    'success': False,
                    'error': 'No message provided'
                }), 400
            
            # Try to use Brian's Financial Wizard if available
            try:
                from brian_financial_wizard import BrianFinancialWizard
                wizard = BrianFinancialWizard()
                
                # Get real financial context
                financial_context = _get_financial_context(mongo_client)
                
                # Generate AI response with real data
                response = wizard.chat_response(message, {
                    **context,
                    'financial_data': financial_context
                })
                
                # Enhance response with real-time data
                enhanced_response = _enhance_response_with_data(response, mongo_client, message)
                
                return jsonify({
                    'success': True,
                    'response': enhanced_response,
                    'ai_powered': True,
                    'context_used': True,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            except ImportError:
                logger.warning("Brian's Financial Wizard not available - using fallback")
                return _fallback_chat_response(message, mongo_client)
            
        except Exception as e:
            logger.error(f"Enhanced chat error: {e}")
            return jsonify({
                'success': False,
                'error': 'Chat service temporarily unavailable',
                'fallback_message': 'I\'m Brian\'s AI Assistant. I can help with expense analysis when my full AI capabilities are restored.'
            }), 500
    
    @app.route('/api/chat/expense-analysis', methods=['POST'])
    def chat_expense_analysis():
        """
        Specialized chat endpoint for expense analysis
        """
        try:
            data = request.get_json() or {}
            query_type = data.get('type', 'general')  # general, category, business, trend
            time_period = data.get('time_period', 30)  # days
            business_filter = data.get('business_type', 'all')
            
            # Get real financial data
            financial_data = _get_detailed_financial_data(mongo_client, time_period, business_filter)
            
            if query_type == 'business_breakdown':
                response = _generate_business_breakdown_response(financial_data)
            elif query_type == 'category_analysis':
                response = _generate_category_analysis_response(financial_data)
            elif query_type == 'spending_trends':
                response = _generate_spending_trends_response(financial_data)
            elif query_type == 'tax_summary':
                response = _generate_tax_summary_response(financial_data)
            else:
                response = _generate_general_analysis_response(financial_data)
            
            return jsonify({
                'success': True,
                'analysis': response,
                'data_period': f'Last {time_period} days',
                'business_filter': business_filter,
                'generated_at': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Expense analysis chat error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/chat/smart-insights', methods=['POST'])
    def chat_smart_insights():
        """
        Generate smart insights based on spending patterns
        """
        try:
            # Get comprehensive financial data
            insights_data = _get_insights_data(mongo_client)
            
            # Generate personalized insights
            insights = _generate_smart_insights(insights_data)
            
            return jsonify({
                'success': True,
                'insights': insights,
                'generated_at': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Smart insights error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

def _get_financial_context(mongo_client) -> Dict:
    """Get comprehensive financial context for AI responses"""
    try:
        if not mongo_client.connected:
            return _empty_financial_context()
        
        # Last 30 days of data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # Get transaction counts and totals
        total_transactions = mongo_client.db.bank_transactions.count_documents({
            'date': {'$gte': start_date}
        })
        
        total_receipts = mongo_client.db.receipts.count_documents({
            'date': {'$gte': start_date}
        })
        
        # Business breakdown
        business_pipeline = [
            {'$match': {
                'date': {'$gte': start_date},
                'amount': {'$lt': 0}
            }},
            {'$group': {
                '_id': '$business_type',
                'total': {'$sum': {'$abs': '$amount'}},
                'count': {'$sum': 1}
            }}
        ]
        
        business_results = list(mongo_client.db.bank_transactions.aggregate(business_pipeline))
        business_breakdown = {
            result['_id'] or 'Unknown': {
                'total': round(result['total'], 2),
                'count': result['count']
            }
            for result in business_results
        }
        
        # Top categories
        category_pipeline = [
            {'$match': {
                'date': {'$gte': start_date},
                'amount': {'$lt': 0}
            }},
            {'$group': {
                '_id': '$category',
                'total': {'$sum': {'$abs': '$amount'}},
                'count': {'$sum': 1}
            }},
            {'$sort': {'total': -1}},
            {'$limit': 5}
        ]
        
        category_results = list(mongo_client.db.bank_transactions.aggregate(category_pipeline))
        top_categories = [
            {
                'category': result['_id'] or 'Uncategorized',
                'total': round(result['total'], 2),
                'count': result['count']
            }
            for result in category_results
        ]
        
        # Match rate
        matched_transactions = mongo_client.db.bank_transactions.count_documents({
            'date': {'$gte': start_date},
            'receipt_matched': True
        })
        
        match_rate = (matched_transactions / max(total_transactions, 1)) * 100
        
        return {
            'has_data': total_transactions > 0,
            'total_transactions': total_transactions,
            'total_receipts': total_receipts,
            'match_rate': round(match_rate, 1),
            'business_breakdown': business_breakdown,
            'top_categories': top_categories,
            'period': '30 days',
            'last_updated': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Financial context error: {e}")
        return _empty_financial_context()

def _enhance_response_with_data(response: Dict, mongo_client, message: str) -> Dict:
    """Enhance AI response with real-time data"""
    try:
        message_lower = message.lower()
        
        # Add real data based on message intent
        if any(word in message_lower for word in ['spending', 'total', 'amount', 'cost']):
            # Add recent spending data
            recent_spending = _get_recent_spending(mongo_client)
            if 'data' not in response:
                response['data'] = {}
            response['data'].update(recent_spending)
        
        if any(word in message_lower for word in ['down home', 'video', 'production']):
            # Add Down Home specific data
            down_home_data = _get_business_specific_data(mongo_client, 'Down Home')
            if 'data' not in response:
                response['data'] = {}
            response['data']['down_home_details'] = down_home_data
        
        if any(word in message_lower for word in ['music city', 'rodeo', 'mcr']):
            # Add MCR specific data
            mcr_data = _get_business_specific_data(mongo_client, 'Music City Rodeo')
            if 'data' not in response:
                response['data'] = {}
            response['data']['mcr_details'] = mcr_data
        
        if any(word in message_lower for word in ['receipt', 'match', 'missing']):
            # Add receipt matching data
            receipt_data = _get_receipt_matching_data(mongo_client)
            if 'data' not in response:
                response['data'] = {}
            response['data']['receipt_stats'] = receipt_data
        
        # Add smart actions based on data
        response['smart_actions'] = _generate_smart_actions(mongo_client, message_lower)
        
        return response
        
    except Exception as e:
        logger.error(f"Response enhancement error: {e}")
        return response

def _fallback_chat_response(message: str, mongo_client) -> Dict:
    """Fallback chat response when AI is not available"""
    try:
        message_lower = message.lower()
        
        # Get basic financial data
        basic_data = _get_basic_financial_summary(mongo_client)
        
        # Generate appropriate response based on intent
        if any(word in message_lower for word in ['analyze', 'report', 'summary', 'breakdown']):
            return jsonify({
                'success': True,
                'response': {
                    'message': f"📊 Here's your financial summary:\n\n• Total transactions: {basic_data['total_transactions']}\n• Business expenses: ${basic_data['business_total']:,.2f}\n• Personal expenses: ${basic_data['personal_total']:,.2f}\n• Receipt match rate: {basic_data['match_rate']:.1f}%\n\nI'm currently in basic mode - enable full AI for deeper insights!",
                    'type': 'financial_summary',
                    'data': basic_data,
                    'quick_actions': ['Connect AI', 'Detailed breakdown', 'Export data']
                },
                'ai_powered': False,
                'upgrade_available': True,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        elif any(word in message_lower for word in ['help', 'what', 'how']):
            return jsonify({
                'success': True,
                'response': {
                    'message': "👋 I'm Brian's Financial Assistant!\n\nI can help you with:\n• Expense analysis and categorization\n• Business vs personal expense tracking\n• Receipt matching and organization\n• Tax deduction identification\n• Export to Google Sheets\n\n💡 Enable full AI for advanced insights and natural conversation!",
                    'type': 'help',
                    'quick_actions': ['Analyze expenses', 'Connect AI', 'Show recent activity', 'Export data']
                },
                'ai_powered': False,
                'upgrade_available': True,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        else:
            return jsonify({
                'success': True,
                'response': {
                    'message': f"I understand you're asking about: '{message}'\n\nI'm currently in basic mode but I can still help with expense analysis and financial summaries. Enable full AI capabilities for natural conversation and advanced insights!\n\nWhat would you like me to help you with?",
                    'type': 'general',
                    'data': basic_data,
                    'quick_actions': ['Connect AI', 'Analyze expenses', 'Show breakdown']
                },
                'ai_powered': False,
                'upgrade_available': True,
                'timestamp': datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Fallback chat error: {e}")
        return jsonify({
            'success': False,
            'error': 'Chat service unavailable'
        }), 500

def _get_detailed_financial_data(mongo_client, days: int, business_filter: str) -> Dict:
    """Get detailed financial data for analysis"""
    try:
        if not mongo_client.connected:
            return {'has_data': False}
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        query = {'date': {'$gte': start_date, '$lte': end_date}}
        if business_filter != 'all':
            query['business_type'] = business_filter
        
        # Get transactions
        transactions = list(mongo_client.db.bank_transactions.find(query))
        expenses = [t for t in transactions if t.get('amount', 0) < 0]
        
        # Calculate totals
        total_spent = sum(abs(t.get('amount', 0)) for t in expenses)
        
        # Business breakdown
        business_totals = {}
        for expense in expenses:
            btype = expense.get('business_type', 'Unknown')
            if btype not in business_totals:
                business_totals[btype] = 0
            business_totals[btype] += abs(expense.get('amount', 0))
        
        # Category breakdown
        category_totals = {}
        for expense in expenses:
            category = expense.get('category', 'Uncategorized')
            if category not in category_totals:
                category_totals[category] = 0
            category_totals[category] += abs(expense.get('amount', 0))
        
        # Top merchants
        merchant_totals = {}
        for expense in expenses:
            merchant = expense.get('merchant_name') or expense.get('description', 'Unknown')[:30]
            if merchant not in merchant_totals:
                merchant_totals[merchant] = {'total': 0, 'count': 0}
            merchant_totals[merchant]['total'] += abs(expense.get('amount', 0))
            merchant_totals[merchant]['count'] += 1
        
        top_merchants = sorted(merchant_totals.items(), key=lambda x: x[1]['total'], reverse=True)[:10]
        
        return {
            'has_data': len(expenses) > 0,
            'total_transactions': len(transactions),
            'total_expenses': len(expenses),
            'total_spent': total_spent,
            'daily_average': total_spent / max(days, 1),
            'business_breakdown': business_totals,
            'category_breakdown': category_totals,
            'top_merchants': [
                {
                    'merchant': merchant,
                    'total': round(data['total'], 2),
                    'count': data['count'],
                    'average': round(data['total'] / data['count'], 2)
                }
                for merchant, data in top_merchants
            ],
            'period_days': days,
            'filter_applied': business_filter
        }
        
    except Exception as e:
        logger.error(f"Detailed financial data error: {e}")
        return {'has_data': False, 'error': str(e)}

def _generate_business_breakdown_response(financial_data: Dict) -> Dict:
    """Generate business breakdown analysis response"""
    if not financial_data.get('has_data'):
        return {
            'message': "No business expense data available yet. Connect your bank accounts or upload receipts to see business breakdowns.",
            'type': 'no_data',
            'suggestions': ['Connect banks', 'Upload receipts', 'Import CSV']
        }
    
    business_breakdown = financial_data.get('business_breakdown', {})
    total_spent = financial_data.get('total_spent', 0)
    
    if not business_breakdown:
        return {
            'message': "No business expenses categorized yet. Process your transactions to see business breakdowns.",
            'type': 'needs_processing',
            'suggestions': ['Process transactions', 'Categorize expenses']
        }
    
    # Generate breakdown message
    breakdown_text = "📊 Business Expense Breakdown:\n\n"
    
    for business, amount in sorted(business_breakdown.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / total_spent * 100) if total_spent > 0 else 0
        if business == 'Down Home':
            breakdown_text += f"🎬 Down Home Media: ${amount:,.2f} ({percentage:.1f}%)\n"
        elif business == 'Music City Rodeo':
            breakdown_text += f"🤠 Music City Rodeo: ${amount:,.2f} ({percentage:.1f}%)\n"
        elif business == 'Personal':
            breakdown_text += f"👤 Personal: ${amount:,.2f} ({percentage:.1f}%)\n"
        else:
            breakdown_text += f"📋 {business}: ${amount:,.2f} ({percentage:.1f}%)\n"
    
    breakdown_text += f"\n💰 Total Analyzed: ${total_spent:,.2f} over {financial_data.get('period_days', 30)} days"
    
    return {
        'message': breakdown_text,
        'type': 'business_breakdown',
        'data': {
            'breakdown': business_breakdown,
            'total': total_spent,
            'period': financial_data.get('period_days', 30)
        },
        'quick_actions': ['Export breakdown', 'Show Down Home details', 'Show MCR details', 'Tax summary']
    }

def _generate_category_analysis_response(financial_data: Dict) -> Dict:
    """Generate category analysis response"""
    if not financial_data.get('has_data'):
        return {
            'message': "No expense data available for category analysis. Upload receipts or connect banks to see spending categories.",
            'type': 'no_data'
        }
    
    category_breakdown = financial_data.get('category_breakdown', {})
    total_spent = financial_data.get('total_spent', 0)
    
    # Generate top categories
    top_categories = sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)[:8]
    
    category_text = "📂 Spending by Category:\n\n"
    
    for category, amount in top_categories:
        percentage = (amount / total_spent * 100) if total_spent > 0 else 0
        
        # Add emoji based on category
        emoji = "📋"
        if 'meal' in category.lower() or 'food' in category.lower():
            emoji = "🍽️"
        elif 'travel' in category.lower() or 'transport' in category.lower():
            emoji = "✈️"
        elif 'software' in category.lower() or 'tech' in category.lower():
            emoji = "💻"
        elif 'equipment' in category.lower():
            emoji = "🎥"
        elif 'office' in category.lower():
            emoji = "🏢"
        
        category_text += f"{emoji} {category}: ${amount:,.2f} ({percentage:.1f}%)\n"
    
    return {
        'message': category_text,
        'type': 'category_analysis',
        'data': {
            'categories': dict(top_categories),
            'total': total_spent
        },
        'insights': _generate_category_insights(top_categories, total_spent),
        'quick_actions': ['Detailed category view', 'Tax deduction summary', 'Export categories']
    }

def _generate_spending_trends_response(financial_data: Dict) -> Dict:
    """Generate spending trends response"""
    if not financial_data.get('has_data'):
        return {
            'message': "No spending data available for trend analysis. Connect banks or upload transactions to see trends.",
            'type': 'no_data'
        }
    
    total_spent = financial_data.get('total_spent', 0)
    period_days = financial_data.get('period_days', 30)
    daily_average = financial_data.get('daily_average', 0)
    
    # Calculate monthly projection
    monthly_projection = daily_average * 30
    
    trends_text = f"📈 Spending Trends Analysis:\n\n"
    trends_text += f"Period: Last {period_days} days\n"
    trends_text += f"Total Spent: ${total_spent:,.2f}\n"
    trends_text += f"Daily Average: ${daily_average:,.2f}\n"
    trends_text += f"Monthly Projection: ${monthly_projection:,.2f}\n\n"
    
    # Add business trend insights
    business_breakdown = financial_data.get('business_breakdown', {})
    if business_breakdown:
        trends_text += "Business Focus:\n"
        for business, amount in sorted(business_breakdown.items(), key=lambda x: x[1], reverse=True):
            if business != 'Personal':
                monthly_business = (amount / period_days) * 30
                trends_text += f"• {business}: ${monthly_business:,.2f}/month projected\n"
    
    return {
        'message': trends_text,
        'type': 'spending_trends',
        'data': {
            'daily_average': daily_average,
            'monthly_projection': monthly_projection,
            'total_spent': total_spent,
            'period_days': period_days
        },
        'quick_actions': ['Monthly report', 'Spending forecast', 'Budget analysis']
    }

def _generate_tax_summary_response(financial_data: Dict) -> Dict:
    """Generate tax summary response"""
    if not financial_data.get('has_data'):
        return {
            'message': "No business expense data for tax analysis. Upload receipts and categorize business expenses to see tax insights.",
            'type': 'no_data'
        }
    
    business_breakdown = financial_data.get('business_breakdown', {})
    
    # Calculate deductible expenses
    deductible_total = 0
    for business, amount in business_breakdown.items():
        if business in ['Down Home', 'Music City Rodeo']:
            deductible_total += amount
    
    # Estimate tax savings (assuming 25% tax rate)
    estimated_savings = deductible_total * 0.25
    
    # Category analysis for tax purposes
    category_breakdown = financial_data.get('category_breakdown', {})
    deductible_categories = ['Business Meals', 'Travel', 'Equipment', 'Software', 'Office Supplies']
    
    tax_text = f"💼 Tax Deduction Summary:\n\n"
    tax_text += f"Business Expenses: ${deductible_total:,.2f}\n"
    tax_text += f"Estimated Tax Savings: ${estimated_savings:,.2f}\n\n"
    
    tax_text += "Deductible Categories:\n"
    for category, amount in category_breakdown.items():
        if any(deduct_cat.lower() in category.lower() for deduct_cat in deductible_categories):
            tax_text += f"• {category}: ${amount:,.2f}\n"
    
    return {
        'message': tax_text,
        'type': 'tax_summary',
        'data': {
            'deductible_total': deductible_total,
            'estimated_savings': estimated_savings,
            'business_breakdown': {k: v for k, v in business_breakdown.items() if k != 'Personal'}
        },
        'quick_actions': ['Export tax report', 'Receipt coverage check', 'Quarterly summary']
    }

def _generate_general_analysis_response(financial_data: Dict) -> Dict:
    """Generate general financial analysis response"""
    if not financial_data.get('has_data'):
        return {
            'message': "📊 Ready to analyze your finances!\n\nTo get started:\n• Connect your bank accounts\n• Upload receipt images\n• Scan Gmail for receipts\n• Import CSV files\n\nOnce you have data, I can provide detailed insights about your Down Home Media and Music City Rodeo expenses!",
            'type': 'getting_started',
            'quick_actions': ['Connect banks', 'Upload receipts', 'Scan emails', 'Import CSV']
        }
    
    total_spent = financial_data.get('total_spent', 0)
    total_transactions = financial_data.get('total_transactions', 0)
    period_days = financial_data.get('period_days', 30)
    
    analysis_text = f"📊 Financial Overview:\n\n"
    analysis_text += f"📈 Period: Last {period_days} days\n"
    analysis_text += f"💰 Total Spent: ${total_spent:,.2f}\n"
    analysis_text += f"📋 Transactions: {total_transactions}\n"
    analysis_text += f"📅 Daily Average: ${total_spent/max(period_days, 1):,.2f}\n\n"
    
    # Add business highlights
    business_breakdown = financial_data.get('business_breakdown', {})
    if business_breakdown:
        analysis_text += "Business Highlights:\n"
        for business, amount in sorted(business_breakdown.items(), key=lambda x: x[1], reverse=True)[:3]:
            percentage = (amount / total_spent * 100) if total_spent > 0 else 0
            analysis_text += f"• {business}: ${amount:,.2f} ({percentage:.1f}%)\n"
    
    return {
        'message': analysis_text,
        'type': 'general_analysis',
        'data': financial_data,
        'quick_actions': ['Business breakdown', 'Category analysis', 'Spending trends', 'Tax summary']
    }

# Helper functions
def _empty_financial_context() -> Dict:
    """Return empty financial context"""
    return {
        'has_data': False,
        'total_transactions': 0,
        'total_receipts': 0,
        'match_rate': 0,
        'business_breakdown': {},
        'top_categories': [],
        'message': 'No financial data available'
    }

def _get_recent_spending(mongo_client) -> Dict:
    """Get recent spending summary"""
    try:
        if not mongo_client.connected:
            return {}
        
        # Last 7 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        recent_expenses = list(mongo_client.db.bank_transactions.find({
            'date': {'$gte': start_date},
            'amount': {'$lt': 0}
        }))
        
        total_recent = sum(abs(t.get('amount', 0)) for t in recent_expenses)
        
        return {
            'recent_7_days': {
                'total': round(total_recent, 2),
                'count': len(recent_expenses),
                'daily_avg': round(total_recent / 7, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Recent spending error: {e}")
        return {}

def _get_business_specific_data(mongo_client, business_type: str) -> Dict:
    """Get data specific to a business"""
    try:
        if not mongo_client.connected:
            return {}
        
        # Last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        business_expenses = list(mongo_client.db.bank_transactions.find({
            'date': {'$gte': start_date},
            'amount': {'$lt': 0},
            'business_type': business_type
        }))
        
        total_business = sum(abs(t.get('amount', 0)) for t in business_expenses)
        
        # Category breakdown for this business
        categories = {}
        for expense in business_expenses:
            category = expense.get('category', 'Uncategorized')
            if category not in categories:
                categories[category] = 0
            categories[category] += abs(expense.get('amount', 0))
        
        return {
            'total_30_days': round(total_business, 2),
            'transaction_count': len(business_expenses),
            'categories': categories,
            'monthly_projection': round(total_business, 2)  # Already 30 days
        }
        
    except Exception as e:
        logger.error(f"Business specific data error: {e}")
        return {}

def _get_receipt_matching_data(mongo_client) -> Dict:
    """Get receipt matching statistics"""
    try:
        if not mongo_client.connected:
            return {}
        
        total_transactions = mongo_client.db.bank_transactions.count_documents({})
        matched_transactions = mongo_client.db.bank_transactions.count_documents({
            'receipt_matched': True
        })
        
        total_receipts = mongo_client.db.receipts.count_documents({})
        
        return {
            'total_transactions': total_transactions,
            'matched_transactions': matched_transactions,
            'total_receipts': total_receipts,
            'match_rate': round((matched_transactions / max(total_transactions, 1)) * 100, 1),
            'unmatched_count': total_transactions - matched_transactions
        }
        
    except Exception as e:
        logger.error(f"Receipt matching data error: {e}")
        return {}

def _generate_smart_actions(mongo_client, message: str) -> List[str]:
    """Generate smart actions based on message and data"""
    actions = []
    
    try:
        if not mongo_client.connected:
            return ['Connect database', 'Upload receipts', 'Scan emails']
        
        # Check data availability
        transaction_count = mongo_client.db.bank_transactions.count_documents({})
        receipt_count = mongo_client.db.receipts.count_documents({})
        
        if transaction_count == 0:
            actions.extend(['Connect banks', 'Import CSV', 'Upload receipts'])
        elif receipt_count == 0:
            actions.extend(['Scan emails', 'Upload receipts', 'Import receipts'])
        else:
            # Data-driven actions
            if 'report' in message or 'export' in message:
                actions.extend(['Export to sheets', 'Generate PDF report', 'Download CSV'])
            elif 'category' in message or 'categorize' in message:
                actions.extend(['Auto-categorize', 'Review categories', 'Set rules'])
            elif 'match' in message or 'receipt' in message:
                actions.extend(['AI receipt matching', 'Manual matching', 'Upload more receipts'])
            else:
                actions.extend(['Detailed analysis', 'Export data', 'AI categorization'])
        
        return actions[:4]  # Limit to 4 actions
        
    except Exception as e:
        logger.error(f"Smart actions error: {e}")
        return ['Refresh data', 'Try again', 'Contact support']

def _get_basic_financial_summary(mongo_client) -> Dict:
    """Get basic financial summary for fallback mode"""
    try:
        if not mongo_client.connected:
            return {
                'total_transactions': 0,
                'business_total': 0,
                'personal_total': 0,
                'match_rate': 0,
                'has_data': False
            }
        
        # Get basic counts and totals
        total_transactions = mongo_client.db.bank_transactions.count_documents({})
        
        # Business vs personal totals
        business_total = 0
        personal_total = 0
        
        business_expenses = list(mongo_client.db.bank_transactions.find({
            'business_type': {'$in': ['Down Home', 'Music City Rodeo']},
            'amount': {'$lt': 0}
        }))
        
        personal_expenses = list(mongo_client.db.bank_transactions.find({
            'business_type': 'Personal',
            'amount': {'$lt': 0}
        }))
        
        business_total = sum(abs(t.get('amount', 0)) for t in business_expenses)
        personal_total = sum(abs(t.get('amount', 0)) for t in personal_expenses)
        
        # Match rate
        matched = mongo_client.db.bank_transactions.count_documents({'receipt_matched': True})
        match_rate = (matched / max(total_transactions, 1)) * 100
        
        return {
            'total_transactions': total_transactions,
            'business_total': business_total,
            'personal_total': personal_total,
            'match_rate': match_rate,
            'has_data': total_transactions > 0
        }
        
    except Exception as e:
        logger.error(f"Basic financial summary error: {e}")
        return {
            'total_transactions': 0,
            'business_total': 0,
            'personal_total': 0,
            'match_rate': 0,
            'has_data': False
        }

def _get_insights_data(mongo_client) -> Dict:
    """Get data for generating smart insights"""
    try:
        if not mongo_client.connected:
            return {}
        
        # Get basic financial data for insights
        end_date = datetime.utcnow()
        start_date_30 = end_date - timedelta(days=30)
        start_date_60 = end_date - timedelta(days=60)
        
        # Current month vs previous month
        current_month = list(mongo_client.db.bank_transactions.find({
            'date': {'$gte': start_date_30},
            'amount': {'$lt': 0}
        }))
        
        previous_month = list(mongo_client.db.bank_transactions.find({
            'date': {'$gte': start_date_60, '$lt': start_date_30},
            'amount': {'$lt': 0}
        }))
        
        current_total = sum(abs(t.get('amount', 0)) for t in current_month)
        previous_total = sum(abs(t.get('amount', 0)) for t in previous_month)
        
        # Calculate spending change
        spending_change = 0
        if previous_total > 0:
            spending_change = ((current_total - previous_total) / previous_total) * 100
        
        # Check for unmatched business expenses
        unmatched_business = mongo_client.db.bank_transactions.count_documents({
            'business_type': {'$in': ['Down Home', 'Music City Rodeo']},
            'receipt_matched': {'$ne': True},
            'amount': {'$lt': 0}
        })
        
        return {
            'spending_increased': spending_change > 10,
            'spending_change_percent': round(spending_change, 1),
            'tax_deductions_available': unmatched_business > 5,
            'unmatched_business_count': unmatched_business,
            'current_month_total': current_total,
            'previous_month_total': previous_total
        }
        
    except Exception as e:
        logger.error(f"Insights data error: {e}")
        return {}

def _generate_smart_insights(insights_data: Dict) -> List[Dict]:
    """Generate smart insights from data"""
    insights = []
    
    try:
        # Spending pattern insights
        if insights_data.get('spending_increased'):
            change_percent = insights_data.get('spending_change_percent', 0)
            insights.append({
                'type': 'spending_alert',
                'priority': 'medium',
                'title': 'Spending Increase Detected',
                'message': f'Your spending has increased {change_percent}% compared to last month',
                'action': 'Review recent transactions'
            })
        
        # Business opportunity insights
        if insights_data.get('tax_deductions_available'):
            unmatched_count = insights_data.get('unmatched_business_count', 0)
            insights.append({
                'type': 'tax_opportunity',
                'priority': 'high',
                'title': 'Maximize Tax Deductions',
                'message': f'You have {unmatched_count} unmatched business expenses',
                'action': 'Upload receipts'
            })
        
        return insights
        
    except Exception as e:
        logger.error(f"Smart insights generation error: {e}")
        return []

def _generate_category_insights(top_categories: List, total_spent: float) -> List[str]:
    """Generate insights about category spending"""
    insights = []
    
    try:
        if top_categories:
            top_category, top_amount = top_categories[0]
            percentage = (top_amount / total_spent * 100) if total_spent > 0 else 0
            
            if percentage > 40:
                insights.append(f"{top_category} represents {percentage:.1f}% of your spending - consider if this aligns with your priorities")
            
            # Software subscription insight
            software_total = sum(amount for category, amount in top_categories if 'software' in category.lower())
            if software_total > 200:
                insights.append(f"Software subscriptions total ${software_total:,.2f} - review for optimization opportunities")
            
            # Business meal insight
            meal_total = sum(amount for category, amount in top_categories if 'meal' in category.lower())
            if meal_total > 300:
                insights.append(f"Business meals total ${meal_total:,.2f} - ensure proper documentation for tax deductions")
        
        return insights
        
    except Exception as e:
        logger.error(f"Category insights error: {e}")
        return [] 
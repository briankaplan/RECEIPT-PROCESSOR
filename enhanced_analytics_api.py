#!/usr/bin/env python3
"""
Enhanced Analytics API
Comprehensive business analytics with real data and intelligent insights
"""

from flask import jsonify, request
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def register_enhanced_analytics(app, mongo_client):
    """Register enhanced analytics endpoints"""
    
    @app.route('/api/analytics/summary')
    def enhanced_analytics_summary():
        """
        Comprehensive analytics summary with real business insights
        """
        try:
            # Parameters
            days_back = int(request.args.get('days_back', 30))
            business_type = request.args.get('business_type', 'all')
            
            if not mongo_client.connected:
                return _analytics_no_data_response()
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            # Get comprehensive analytics
            analytics = {
                'period_info': {
                    'days_analyzed': days_back,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'business_filter': business_type
                },
                'overview': _get_overview_analytics(mongo_client, start_date, end_date, business_type),
                'business_breakdown': _get_business_breakdown(mongo_client, start_date, end_date),
                'category_analysis': _get_category_analysis(mongo_client, start_date, end_date, business_type),
                'merchant_insights': _get_merchant_insights(mongo_client, start_date, end_date),
                'spending_trends': _get_spending_trends(mongo_client, start_date, end_date),
                'receipt_matching': _get_receipt_matching_stats(mongo_client, start_date, end_date),
                'tax_insights': _get_tax_insights(mongo_client, start_date, end_date),
                'recommendations': _get_smart_recommendations(mongo_client, start_date, end_date),
                'data_quality': _assess_data_quality(mongo_client, start_date, end_date)
            }
            
            return jsonify({
                'success': True,
                'analytics': analytics,
                'generated_at': datetime.utcnow().isoformat(),
                'has_data': analytics['overview']['total_transactions'] > 0
            })
            
        except Exception as e:
            logger.error(f"Analytics summary error: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'analytics': _analytics_fallback_response()
            }), 500
    
    @app.route('/api/analytics/business-comparison')
    def business_comparison_analytics():
        """
        Detailed comparison between Down Home, MCR, and Personal expenses
        """
        try:
            days_back = int(request.args.get('days_back', 90))  # 3 months default
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            if not mongo_client.connected:
                return _business_comparison_no_data()
            
            comparison = {
                'period': f"Last {days_back} days",
                'businesses': {
                    'Down Home': _get_business_specific_analytics(mongo_client, 'Down Home', start_date, end_date),
                    'Music City Rodeo': _get_business_specific_analytics(mongo_client, 'Music City Rodeo', start_date, end_date),
                    'Personal': _get_business_specific_analytics(mongo_client, 'Personal', start_date, end_date)
                },
                'cross_business_insights': _get_cross_business_insights(mongo_client, start_date, end_date),
                'efficiency_metrics': _calculate_business_efficiency(mongo_client, start_date, end_date)
            }
            
            return jsonify({
                'success': True,
                'comparison': comparison,
                'generated_at': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Business comparison error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/monthly-trends')
    def monthly_trends_analytics():
        """
        Monthly spending trends with forecasting
        """
        try:
            months_back = int(request.args.get('months_back', 12))
            
            if not mongo_client.connected:
                return _monthly_trends_no_data()
            
            trends = _calculate_monthly_trends(mongo_client, months_back)
            forecast = _generate_spending_forecast(trends)
            
            return jsonify({
                'success': True,
                'trends': trends,
                'forecast': forecast,
                'insights': _generate_trend_insights(trends),
                'generated_at': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Monthly trends error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

# ... (rest of the helper functions from your provided code) ... 
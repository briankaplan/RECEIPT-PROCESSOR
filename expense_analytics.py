#!/usr/bin/env python3
"""
Expense Analytics - Advanced analytics and insights for expense data
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
import pandas as pd
import numpy as np

class ExpenseAnalytics:
    """
    Advanced analytics system for expense insights and trend analysis
    """
    
    def __init__(self, expense_db):
        self.expense_db = expense_db
        self.analytics_cache = {}
        self.cache_ttl = 3600  # 1 hour cache
    
    async def generate_monthly_report(self, year: int, month: int) -> Dict:
        """Generate comprehensive monthly expense report"""
        
        start_date = f"{year}-{month:02d}-01"
        
        # Calculate end date
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        # Get expense data
        expenses = await self.expense_db.get_expenses_by_date_range(start_date, end_date)
        
        if not expenses:
            return {"error": "No expenses found for this period"}
        
        # Basic statistics
        amounts = [exp.amount for exp in expenses]
        total_amount = sum(amounts)
        avg_amount = total_amount / len(amounts)
        
        # Category analysis
        category_totals = defaultdict(float)
        category_counts = defaultdict(int)
        
        for exp in expenses:
            category_totals[exp.category] += exp.amount
            category_counts[exp.category] += 1
        
        # Merchant analysis
        merchant_totals = defaultdict(float)
        merchant_counts = defaultdict(int)
        
        for exp in expenses:
            merchant_totals[exp.merchant] += exp.amount
            merchant_counts[exp.merchant] += 1
        
        # Daily spending pattern
        daily_totals = defaultdict(float)
        for exp in expenses:
            daily_totals[exp.date] += exp.amount
        
        # Payment method breakdown
        payment_method_totals = defaultdict(float)
        for exp in expenses:
            payment_method_totals[exp.payment_method] += exp.amount
        
        # Tax and tip analysis
        total_tax = sum(exp.tax_amount for exp in expenses if exp.tax_amount)
        total_tip = sum(exp.tip_amount for exp in expenses if exp.tip_amount)
        
        return {
            "period": f"{year}-{month:02d}",
            "summary": {
                "total_amount": round(total_amount, 2),
                "transaction_count": len(expenses),
                "average_amount": round(avg_amount, 2),
                "highest_amount": max(amounts),
                "lowest_amount": min(amounts),
                "total_tax": round(total_tax, 2),
                "total_tip": round(total_tip, 2)
            },
            "category_breakdown": [
                {"category": cat, "total": round(total, 2), "count": category_counts[cat]}
                for cat, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
            ],
            "top_merchants": [
                {"merchant": merchant, "total": round(total, 2), "count": merchant_counts[merchant]}
                for merchant, total in sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:10]
            ],
            "payment_methods": [
                {"method": method, "total": round(total, 2)}
                for method, total in sorted(payment_method_totals.items(), key=lambda x: x[1], reverse=True)
            ],
            "daily_spending": [
                {"date": date, "total": round(total, 2)}
                for date, total in sorted(daily_totals.items())
            ]
        }
    
    async def analyze_spending_trends(self, months: int = 12) -> Dict:
        """Analyze spending trends over time"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        expenses = await self.expense_db.get_expenses_by_date_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if not expenses:
            return {"error": "No expenses found for trend analysis"}
        
        # Monthly trends
        monthly_totals = defaultdict(float)
        monthly_counts = defaultdict(int)
        
        for exp in expenses:
            month_key = exp.date[:7]  # YYYY-MM
            monthly_totals[month_key] += exp.amount
            monthly_counts[month_key] += 1
        
        # Category trends
        category_monthly = defaultdict(lambda: defaultdict(float))
        for exp in expenses:
            month_key = exp.date[:7]
            category_monthly[exp.category][month_key] += exp.amount
        
        # Calculate growth rates
        months_sorted = sorted(monthly_totals.keys())
        growth_rates = []
        
        for i in range(1, len(months_sorted)):
            prev_month = monthly_totals[months_sorted[i-1]]
            curr_month = monthly_totals[months_sorted[i]]
            
            if prev_month > 0:
                growth_rate = ((curr_month - prev_month) / prev_month) * 100
                growth_rates.append({
                    "month": months_sorted[i],
                    "growth_rate": round(growth_rate, 2),
                    "amount": round(curr_month, 2)
                })
        
        return {
            "period_analyzed": f"{months} months",
            "monthly_trends": [
                {
                    "month": month,
                    "total": round(monthly_totals[month], 2),
                    "count": monthly_counts[month],
                    "average": round(monthly_totals[month] / monthly_counts[month], 2)
                }
                for month in months_sorted
            ],
            "growth_analysis": growth_rates,
            "category_trends": {
                category: [
                    {"month": month, "total": round(totals[month], 2)}
                    for month in sorted(totals.keys())
                ]
                for category, totals in category_monthly.items()
            }
        }
    
    async def detect_anomalies(self, sensitivity: float = 2.0) -> List[Dict]:
        """Detect unusual spending patterns"""
        
        # Get last 90 days of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        expenses = await self.expense_db.get_expenses_by_date_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if len(expenses) < 10:
            return []
        
        amounts = [exp.amount for exp in expenses]
        mean_amount = np.mean(amounts)
        std_amount = np.std(amounts)
        
        anomalies = []
        
        # Amount-based anomalies
        threshold = mean_amount + (sensitivity * std_amount)
        
        for exp in expenses:
            if exp.amount > threshold:
                anomalies.append({
                    "type": "high_amount",
                    "expense_id": exp.expense_id,
                    "merchant": exp.merchant,
                    "amount": exp.amount,
                    "date": exp.date,
                    "deviation": round((exp.amount - mean_amount) / std_amount, 2),
                    "description": f"Amount ${exp.amount:.2f} is {(exp.amount/mean_amount):.1f}x the average"
                })
        
        # Frequency-based anomalies
        merchant_frequencies = Counter(exp.merchant for exp in expenses)
        daily_counts = Counter(exp.date for exp in expenses)
        
        # Unusual merchant frequency
        avg_merchant_freq = np.mean(list(merchant_frequencies.values()))
        std_merchant_freq = np.std(list(merchant_frequencies.values()))
        
        for merchant, freq in merchant_frequencies.items():
            if freq > avg_merchant_freq + (sensitivity * std_merchant_freq):
                anomalies.append({
                    "type": "high_frequency_merchant",
                    "merchant": merchant,
                    "frequency": freq,
                    "description": f"{merchant} appears {freq} times (unusually high)"
                })
        
        # Unusual daily activity
        avg_daily_count = np.mean(list(daily_counts.values()))
        std_daily_count = np.std(list(daily_counts.values()))
        
        for date, count in daily_counts.items():
            if count > avg_daily_count + (sensitivity * std_daily_count):
                day_total = sum(exp.amount for exp in expenses if exp.date == date)
                anomalies.append({
                    "type": "high_activity_day",
                    "date": date,
                    "transaction_count": count,
                    "total_amount": round(day_total, 2),
                    "description": f"{count} transactions on {date} (unusually high activity)"
                })
        
        return sorted(anomalies, key=lambda x: x.get('amount', x.get('frequency', 0)), reverse=True)
    
    async def generate_budget_insights(self, budget_limits: Dict[str, float]) -> Dict:
        """Generate budget vs actual spending insights"""
        
        # Get current month data
        now = datetime.now()
        start_date = f"{now.year}-{now.month:02d}-01"
        
        if now.month == 12:
            end_date = f"{now.year + 1}-01-01"
        else:
            end_date = f"{now.year}-{now.month + 1:02d}-01"
        
        expenses = await self.expense_db.get_expenses_by_date_range(start_date, end_date)
        
        # Calculate actual spending by category
        actual_spending = defaultdict(float)
        for exp in expenses:
            actual_spending[exp.category] += exp.amount
        
        budget_analysis = {}
        total_budget = sum(budget_limits.values())
        total_actual = sum(actual_spending.values())
        
        for category, budget_limit in budget_limits.items():
            actual = actual_spending.get(category, 0)
            variance = actual - budget_limit
            variance_percent = (variance / budget_limit * 100) if budget_limit > 0 else 0
            
            status = "over" if variance > 0 else "under"
            days_in_month = (datetime.now() - datetime.strptime(start_date, '%Y-%m-%d')).days
            projected_monthly = (actual / days_in_month) * 30 if days_in_month > 0 else actual
            
            budget_analysis[category] = {
                "budget": budget_limit,
                "actual": round(actual, 2),
                "variance": round(variance, 2),
                "variance_percent": round(variance_percent, 2),
                "status": status,
                "projected_monthly": round(projected_monthly, 2),
                "days_analyzed": days_in_month
            }
        
        return {
            "period": f"{now.year}-{now.month:02d}",
            "overall": {
                "total_budget": round(total_budget, 2),
                "total_actual": round(total_actual, 2),
                "total_variance": round(total_actual - total_budget, 2),
                "budget_utilization": round((total_actual / total_budget * 100) if total_budget > 0 else 0, 2)
            },
            "category_analysis": budget_analysis,
            "recommendations": self._generate_budget_recommendations(budget_analysis)
        }
    
    def _generate_budget_recommendations(self, budget_analysis: Dict) -> List[str]:
        """Generate budget recommendations based on analysis"""
        
        recommendations = []
        
        for category, analysis in budget_analysis.items():
            if analysis["variance_percent"] > 20:
                recommendations.append(
                    f"🚨 {category}: {analysis['variance_percent']:.1f}% over budget. "
                    f"Consider reducing spending or adjusting budget."
                )
            elif analysis["variance_percent"] > 10:
                recommendations.append(
                    f"⚠️ {category}: {analysis['variance_percent']:.1f}% over budget. Monitor closely."
                )
            elif analysis["projected_monthly"] > analysis["budget"]:
                recommendations.append(
                    f"📈 {category}: On track to exceed budget by month end. "
                    f"Projected: ${analysis['projected_monthly']:.2f}"
                )
        
        return recommendations
    
    async def merchant_analysis(self, top_n: int = 20) -> Dict:
        """Analyze merchant spending patterns"""
        
        # Get last 6 months of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        expenses = await self.expense_db.get_expenses_by_date_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        merchant_data = defaultdict(lambda: {
            'total': 0, 'count': 0, 'amounts': [], 'dates': [], 'categories': set()
        })
        
        for exp in expenses:
            merchant_data[exp.merchant]['total'] += exp.amount
            merchant_data[exp.merchant]['count'] += 1
            merchant_data[exp.merchant]['amounts'].append(exp.amount)
            merchant_data[exp.merchant]['dates'].append(exp.date)
            merchant_data[exp.merchant]['categories'].add(exp.category)
        
        # Calculate merchant insights
        merchant_insights = []
        
        for merchant, data in merchant_data.items():
            avg_amount = data['total'] / data['count']
            amounts = data['amounts']
            
            # Calculate frequency pattern
            dates = sorted(data['dates'])
            if len(dates) > 1:
                intervals = []
                for i in range(1, len(dates)):
                    prev_date = datetime.strptime(dates[i-1], '%Y-%m-%d')
                    curr_date = datetime.strptime(dates[i], '%Y-%m-%d')
                    intervals.append((curr_date - prev_date).days)
                
                avg_interval = np.mean(intervals) if intervals else 0
                frequency_pattern = self._classify_frequency(avg_interval)
            else:
                frequency_pattern = "one-time"
            
            merchant_insights.append({
                'merchant': merchant,
                'total_spent': round(data['total'], 2),
                'transaction_count': data['count'],
                'average_amount': round(avg_amount, 2),
                'min_amount': min(amounts),
                'max_amount': max(amounts),
                'frequency_pattern': frequency_pattern,
                'categories': list(data['categories']),
                'spending_consistency': round(np.std(amounts) / avg_amount if avg_amount > 0 else 0, 2)
            })
        
        # Sort by total spent
        merchant_insights.sort(key=lambda x: x['total_spent'], reverse=True)
        
        return {
            "analysis_period": "6 months",
            "total_merchants": len(merchant_insights),
            "top_merchants": merchant_insights[:top_n],
            "spending_diversity": len(set(exp.merchant for exp in expenses)),
            "most_frequent": max(merchant_insights, key=lambda x: x['transaction_count']) if merchant_insights else None,
            "highest_average": max(merchant_insights, key=lambda x: x['average_amount']) if merchant_insights else None
        }
    
    def _classify_frequency(self, avg_days: float) -> str:
        """Classify transaction frequency based on average days between transactions"""
        
        if avg_days <= 1:
            return "daily"
        elif avg_days <= 7:
            return "weekly"
        elif avg_days <= 15:
            return "bi-weekly"
        elif avg_days <= 31:
            return "monthly"
        elif avg_days <= 93:
            return "quarterly"
        else:
            return "irregular"
    
    async def export_analytics_report(self, format: str = "json") -> str:
        """Export comprehensive analytics report"""
        
        now = datetime.now()
        
        # Gather all analytics
        monthly_report = await self.generate_monthly_report(now.year, now.month)
        trends = await self.analyze_spending_trends(12)
        anomalies = await self.detect_anomalies()
        merchant_analysis = await self.merchant_analysis()
        
        report = {
            "generated_at": now.isoformat(),
            "monthly_report": monthly_report,
            "yearly_trends": trends,
            "anomalies": anomalies,
            "merchant_analysis": merchant_analysis
        }
        
        if format == "json":
            import json
            return json.dumps(report, indent=2)
        
        elif format == "csv":
            # Export as multiple CSV sections
            import io
            output = io.StringIO()
            
            # Monthly summary
            output.write("MONTHLY SUMMARY\n")
            if "summary" in monthly_report:
                for key, value in monthly_report["summary"].items():
                    output.write(f"{key},{value}\n")
            
            output.write("\nTOP MERCHANTS\n")
            output.write("Merchant,Total,Count\n")
            for merchant in monthly_report.get("top_merchants", []):
                output.write(f"{merchant['merchant']},{merchant['total']},{merchant['count']}\n")
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported format: {format}")


# Notification System
class NotificationSystem:
    """
    Notification system for expense alerts and reports
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.notification_methods = self._load_notification_methods()
        
    def _load_notification_methods(self) -> List[str]:
        """Load available notification methods"""
        
        methods = []
        
        if self.config.get('email', {}).get('enabled', False):
            methods.append('email')
        
        if self.config.get('slack', {}).get('enabled', False):
            methods.append('slack')
        
        if self.config.get('console', {}).get('enabled', True):
            methods.append('console')
        
        return methods
    
    async def send_processing_complete_notification(self, session_data: Dict):
        """Send notification when processing is complete"""
        
        message = f"""
🎯 Expense Processing Complete!

📊 Session Summary:
• Emails processed: {session_data.get('emails_found', 0)}
• Receipts processed: {session_data.get('receipts_processed', 0)}
• Transactions matched: {session_data.get('transactions_matched', 0)}
• Processing time: {session_data.get('processing_time', 0):.1f}s
• Matching accuracy: {session_data.get('matching_accuracy', 0):.1%}

💰 Key Results:
• New merchants learned: {session_data.get('new_merchants', 0)}
• Expenses categorized: {session_data.get('expenses_categorized', 0)}
• Average AI confidence: {session_data.get('ai_confidence_avg', 0):.2f}
        """
        
        await self._send_notification("Expense Processing Complete", message)
    
    async def send_anomaly_alert(self, anomalies: List[Dict]):
        """Send alert for detected spending anomalies"""
        
        if not anomalies:
            return
        
        message = f"🚨 Spending Anomalies Detected!\n\n"
        
        for anomaly in anomalies[:5]:  # Top 5 anomalies
            if anomaly['type'] == 'high_amount':
                message += f"💰 High Amount: {anomaly['merchant']} ${anomaly['amount']:.2f} on {anomaly['date']}\n"
            elif anomaly['type'] == 'high_frequency_merchant':
                message += f"🔄 High Frequency: {anomaly['merchant']} ({anomaly['frequency']} transactions)\n"
            elif anomaly['type'] == 'high_activity_day':
                message += f"📅 High Activity: {anomaly['date']} ({anomaly['transaction_count']} transactions)\n"
        
        await self._send_notification("Spending Anomalies Detected", message)
    
    async def send_budget_alert(self, budget_analysis: Dict):
        """Send budget overage alerts"""
        
        over_budget = [cat for cat, data in budget_analysis.items() 
                      if data.get('variance', 0) > 0]
        
        if not over_budget:
            return
        
        message = f"💸 Budget Alert!\n\n"
        
        for category in over_budget:
            data = budget_analysis[category]
            message += f"• {category}: ${data['actual']:.2f} / ${data['budget']:.2f} "
            message += f"({data['variance_percent']:+.1f}%)\n"
        
        await self._send_notification("Budget Alert", message)
    
    async def _send_notification(self, title: str, message: str):
        """Send notification via all enabled methods"""
        
        for method in self.notification_methods:
            try:
                if method == 'console':
                    print(f"\n{'='*50}")
                    print(f"📢 {title}")
                    print(f"{'='*50}")
                    print(message)
                    print(f"{'='*50}\n")
                
                elif method == 'email':
                    await self._send_email(title, message)
                
                elif method == 'slack':
                    await self._send_slack(title, message)
                    
            except Exception as e:
                logging.error(f"❌ Failed to send {method} notification: {e}")
    
    async def _send_email(self, title: str, message: str):
        """Send email notification"""
        # Email implementation would go here
        logging.info(f"📧 Email notification: {title}")
    
    async def _send_slack(self, title: str, message: str):
        """Send Slack notification"""
        # Slack implementation would go here
        logging.info(f"💬 Slack notification: {title}")


# Test the analytics system
if __name__ == "__main__":
    print("📊 Expense Analytics System")
    print("Advanced analytics and insights for expense data")
    print("\n🔧 Features:")
    print("• Monthly reports with detailed breakdowns")
    print("• Spending trend analysis over time")
    print("• Anomaly detection for unusual patterns")
    print("• Budget vs actual analysis")
    print("• Merchant spending insights")
    print("• Automated notifications and alerts")
    print("\n✅ Analytics system ready!")
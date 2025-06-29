#!/usr/bin/env python3
"""
Enhanced Receipt System
Complete integration of machine learning intelligence with your existing receipt processor
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from intelligent_receipt_processor import IntelligentReceiptProcessor

logger = logging.getLogger(__name__)

class EnhancedReceiptSystem:
    """
    Enhanced receipt system that combines your existing personalized search
    with advanced machine learning intelligence
    """
    
    def __init__(self, gmail_service=None, mongo_client=None, config=None):
        self.gmail_service = gmail_service
        self.mongo_client = mongo_client
        self.config = config or {}
        
        # Initialize the intelligent processor
        self.intelligence = IntelligentReceiptProcessor()
        
        # Performance tracking
        self.performance_metrics = {
            'total_searches': 0,
            'total_receipts_found': 0,
            'total_matches': 0,
            'learning_progress': {},
            'search_improvements': []
        }
    
    async def enhanced_search(self, days_back: int = 7, 
                            transactions: Optional[List[Dict]] = None,
                            use_existing_search: bool = True) -> Dict:
        """
        Enhanced search that combines existing personalized search with intelligence
        """
        logger.info(f"🧙‍♂️ Starting enhanced receipt search for last {days_back} days")
        
        # Step 1: Learn from transaction data if provided
        if transactions:
            logger.info("📚 Learning from transaction data...")
            learning_result = self.intelligence.learn_from_transactions(transactions)
            logger.info(f"📊 Learned from {learning_result['transactions_analyzed']} transactions")
        
        # Step 2: Use existing personalized search if available
        base_results = {}
        if use_existing_search and self.gmail_service:
            try:
                from personalized_email_search import PersonalizedEmailSearchSystem
                search_system = PersonalizedEmailSearchSystem(
                    self.gmail_service, self.mongo_client, self.config
                )
                
                logger.info("🔍 Running existing personalized search...")
                base_results = await search_system.execute_personalized_search(days_back)
                logger.info(f"📧 Found {len(base_results.get('emails', []))} emails with existing search")
                
            except Exception as e:
                logger.warning(f"⚠️ Existing search failed: {e}")
                base_results = {'emails': []}
        else:
            base_results = {'emails': []}
        
        # Step 3: Enhance with intelligence
        enhanced_results = await self._enhance_with_intelligence(base_results, transactions)
        
        # Step 4: Learn from the results
        if enhanced_results.get('emails'):
            logger.info("📚 Learning from email patterns...")
            email_learning = self.intelligence.learn_from_emails(enhanced_results['emails'])
            logger.info(f"📊 Learned from {email_learning['emails_analyzed']} emails")
        
        # Step 5: Generate intelligent search strategies
        if transactions:
            intelligent_strategies = self._generate_intelligent_strategies(transactions)
            enhanced_results['intelligent_strategies'] = intelligent_strategies
        
        # Step 6: Update performance metrics
        self._update_performance_metrics(enhanced_results)
        
        # Step 7: Save intelligence
        self.intelligence._save_intelligence()
        
        logger.info("✅ Enhanced search complete!")
        
        return enhanced_results
    
    async def _enhance_with_intelligence(self, base_results: Dict, 
                                       transactions: Optional[List[Dict]]) -> Dict:
        """
        Enhance search results with machine learning intelligence
        """
        enhanced_emails = []
        intelligence_insights = []
        
        for email in base_results.get('emails', []):
            enhanced_email = email.copy()
            
            # Predict receipt likelihood
            receipt_prediction = self._predict_email_receipt_likelihood(email)
            enhanced_email['receipt_likelihood'] = receipt_prediction['likelihood']
            enhanced_email['receipt_confidence'] = receipt_prediction['confidence']
            enhanced_email['receipt_factors'] = receipt_prediction['factors']
            
            # Find potential transaction matches
            if transactions:
                transaction_matches = self.intelligence.find_receipt_candidates(email, transactions)
                enhanced_email['transaction_matches'] = transaction_matches
            
            # Generate search suggestions
            search_suggestions = self.intelligence.suggest_search_terms(email)
            enhanced_email['search_suggestions'] = search_suggestions
            
            # Add intelligence insights
            insights = self._generate_intelligence_insights(email)
            if insights:
                intelligence_insights.extend(insights)
            
            enhanced_emails.append(enhanced_email)
        
        # Sort by receipt likelihood
        enhanced_emails.sort(key=lambda x: x.get('receipt_likelihood', 0), reverse=True)
        
        return {
            **base_results,
            'emails': enhanced_emails,
            'intelligence_insights': intelligence_insights,
            'enhanced_search': True,
            'intelligence_summary': self.intelligence.get_intelligence_summary()
        }
    
    def _predict_email_receipt_likelihood(self, email: Dict) -> Dict:
        """
        Predict likelihood that an email contains a receipt
        """
        likelihood = 0.5
        confidence = 0.3
        factors = []
        
        # Check sender patterns
        sender_domain = self._extract_domain(email.get('from', ''))
        for pattern in self.intelligence.learned_patterns.values():
            if sender_domain in pattern.get('email_domains', []):
                likelihood = pattern['receipt_likelihood']
                confidence = pattern['confidence']
                factors.append(f"Learned sender pattern: {sender_domain}")
                break
        
        # Check subject keywords
        subject = email.get('subject', '').lower()
        receipt_keywords = ['receipt', 'payment', 'invoice', 'confirmation', 'order', 'purchase']
        keyword_matches = [kw for kw in receipt_keywords if kw in subject]
        if keyword_matches:
            likelihood += 0.2
            factors.append(f"Subject keywords: {', '.join(keyword_matches)}")
        
        # Check for amount patterns in body
        body = email.get('body', '')
        import re
        amount_patterns = re.findall(r'\$\d+\.?\d*', body)
        if amount_patterns:
            likelihood += 0.15
            factors.append(f"Amount patterns found: {len(amount_patterns)}")
        
        # Check for attachment
        if email.get('has_attachments', False):
            likelihood += 0.1
            factors.append("Has attachments")
        
        # Check for common receipt domains
        high_likelihood_domains = [
            'squareup.com', 'paypal.com', 'stripe.com', 'receipts.com',
            'anthropic.com', 'netflix.com', 'spotify.com', 'github.com'
        ]
        if sender_domain in high_likelihood_domains:
            likelihood += 0.2
            factors.append(f"Known receipt domain: {sender_domain}")
        
        return {
            'likelihood': min(likelihood, 1.0),
            'confidence': min(confidence, 1.0),
            'factors': factors
        }
    
    def _generate_intelligence_insights(self, email: Dict) -> List[Dict]:
        """
        Generate intelligence insights for an email
        """
        insights = []
        
        sender_domain = self._extract_domain(email.get('from', ''))
        
        # Check if this is a new sender pattern
        is_new_sender = True
        for pattern in self.intelligence.learned_patterns.values():
            if sender_domain in pattern.get('email_domains', []):
                is_new_sender = False
                break
        
        if is_new_sender:
            insights.append({
                'type': 'new_sender',
                'message': f"New email sender detected: {sender_domain}",
                'suggestion': f"Monitor emails from {sender_domain} for receipt patterns"
            })
        
        # Check for high receipt likelihood
        receipt_likelihood = email.get('receipt_likelihood', 0)
        if receipt_likelihood > 0.8:
            insights.append({
                'type': 'high_receipt_likelihood',
                'message': f"High receipt likelihood: {receipt_likelihood:.1%}",
                'suggestion': "This email likely contains a receipt"
            })
        
        # Check for transaction matches
        transaction_matches = email.get('transaction_matches', [])
        if len(transaction_matches) > 0:
            best_match = transaction_matches[0]
            insights.append({
                'type': 'transaction_match',
                'message': f"Potential transaction match: {best_match['transaction']['description']}",
                'suggestion': f"Verify match with confidence: {best_match['confidence']:.1%}"
            })
        
        return insights
    
    def _generate_intelligent_strategies(self, transactions: List[Dict]) -> List[Dict]:
        """
        Generate intelligent search strategies based on learned patterns
        """
        strategies = []
        
        # Analyze transaction patterns
        transaction_analysis = self.intelligence.learn_from_transactions(transactions)
        
        # Generate strategies based on learned patterns
        for merchant, pattern in self.intelligence.learned_patterns.items():
            if pattern.get('confidence', 0) > 0.7:  # High confidence patterns
                strategy = {
                    'name': f"intelligent_{merchant.lower().replace(' ', '_')}",
                    'description': f"Intelligent search for {merchant} receipts",
                    'query': self._build_merchant_query(merchant, pattern),
                    'expected_count': pattern.get('sample_count', 1),
                    'confidence': pattern.get('confidence', 0),
                    'receipt_likelihood': pattern.get('receipt_likelihood', 0)
                }
                strategies.append(strategy)
        
        # Generate strategies based on payment methods
        payment_methods = {}
        for tx in transactions:
            method = tx.get('payment_method', '')
            if method:
                payment_methods[method] = payment_methods.get(method, 0) + 1
        
        for method, count in payment_methods.items():
            if count >= 3:  # At least 3 transactions
                strategy = {
                    'name': f"intelligent_{method.lower()}",
                    'description': f"Intelligent search for {method} payments",
                    'query': self._build_payment_method_query(method),
                    'expected_count': count,
                    'confidence': 0.6,
                    'receipt_likelihood': self._get_payment_method_receipt_likelihood(method)
                }
                strategies.append(strategy)
        
        return strategies
    
    def _build_merchant_query(self, merchant: str, pattern: Dict) -> str:
        """Build search query for a specific merchant"""
        query_parts = []
        
        # Add merchant name
        query_parts.append(merchant)
        
        # Add common variations
        if 'SQUARE *' in merchant:
            clean_merchant = merchant.replace('SQUARE *', '')
            query_parts.append(clean_merchant)
            query_parts.append('square')
        
        if 'PAYPAL *' in merchant:
            clean_merchant = merchant.replace('PAYPAL *', '')
            query_parts.append(clean_merchant)
            query_parts.append('paypal')
        
        # Add learned search terms
        query_parts.extend(pattern.get('search_terms', []))
        
        # Add receipt keywords
        query_parts.extend(['receipt', 'payment', 'confirmation'])
        
        return ' OR '.join(query_parts)
    
    def _build_payment_method_query(self, method: str) -> str:
        """Build search query for a payment method"""
        if method.lower() == 'paypal':
            return 'paypal OR paypal.com'
        elif method.lower() == 'square':
            return 'square OR squareup.com OR receipts@square.com'
        elif method.lower() == 'stripe':
            return 'stripe OR stripe.com'
        else:
            return f'{method} OR receipt OR payment'
    
    def _get_payment_method_receipt_likelihood(self, method: str) -> float:
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
    
    def _extract_domain(self, email: str) -> str:
        """Extract domain from email address"""
        if '@' in email:
            return email.split('@')[1].lower()
        return email.lower()
    
    def _update_performance_metrics(self, results: Dict):
        """Update performance metrics"""
        self.performance_metrics['total_searches'] += 1
        self.performance_metrics['total_receipts_found'] += len(results.get('emails', []))
        
        # Count matches
        match_count = 0
        for email in results.get('emails', []):
            match_count += len(email.get('transaction_matches', []))
        self.performance_metrics['total_matches'] += match_count
        
        # Update learning progress
        intelligence_summary = results.get('intelligence_summary', {})
        self.performance_metrics['learning_progress'] = intelligence_summary.get('learning_progress', {})
        
        # Record search improvement
        if results.get('enhanced_search'):
            self.performance_metrics['search_improvements'].append({
                'timestamp': datetime.now().isoformat(),
                'emails_found': len(results.get('emails', [])),
                'matches_found': match_count,
                'intelligence_patterns': intelligence_summary.get('learned_patterns', 0)
            })
    
    def get_performance_report(self) -> Dict:
        """Get comprehensive performance report"""
        return {
            'performance_metrics': self.performance_metrics,
            'intelligence_summary': self.intelligence.get_intelligence_summary(),
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[Dict]:
        """Generate recommendations for improving the system"""
        recommendations = []
        
        metrics = self.performance_metrics
        intelligence = self.intelligence.get_intelligence_summary()
        
        # Check search frequency
        if metrics['total_searches'] < 5:
            recommendations.append({
                'type': 'more_usage',
                'message': 'System needs more usage to learn effectively',
                'suggestion': 'Run more searches to improve pattern recognition'
            })
        
        # Check match rate
        if metrics['total_searches'] > 0:
            match_rate = metrics['total_matches'] / max(metrics['total_receipts_found'], 1)
            if match_rate < 0.3:
                recommendations.append({
                    'type': 'low_match_rate',
                    'message': f'Low match rate: {match_rate:.1%}',
                    'suggestion': 'Provide more transaction data to improve matching'
                })
        
        # Check learning progress
        learning_stage = intelligence.get('learning_progress', {}).get('learning_stage', 'beginner')
        if learning_stage == 'beginner':
            recommendations.append({
                'type': 'learning_stage',
                'message': 'System is in beginner learning stage',
                'suggestion': 'Continue using the system to advance to intermediate stage'
            })
        
        return recommendations
    
    def save_performance_data(self, filepath: str = 'receipt_performance.json'):
        """Save performance data to file"""
        try:
            data = {
                'performance_metrics': self.performance_metrics,
                'intelligence_summary': self.intelligence.get_intelligence_summary(),
                'timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"💾 Saved performance data to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving performance data: {str(e)}")
            return False
    
    def load_performance_data(self, filepath: str = 'receipt_performance.json'):
        """Load performance data from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.performance_metrics = data.get('performance_metrics', self.performance_metrics)
            
            logger.info(f"📂 Loaded performance data from {filepath}")
            return True
            
        except FileNotFoundError:
            logger.info(f"📂 No performance data file found at {filepath}")
            return False
        except Exception as e:
            logger.error(f"Error loading performance data: {str(e)}")
            return False

# Convenience function for easy integration
async def run_enhanced_search(gmail_service=None, mongo_client=None, config=None,
                            days_back=7, transactions=None):
    """
    Convenience function to run enhanced search
    """
    system = EnhancedReceiptSystem(gmail_service, mongo_client, config)
    return await system.enhanced_search(days_back, transactions) 
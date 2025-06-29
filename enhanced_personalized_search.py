#!/usr/bin/env python3
"""
Enhanced Personalized Email Search with Advanced Receipt Intelligence
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from advanced_receipt_intelligence import AdvancedReceiptIntelligence
from personalized_email_search import PersonalizedEmailSearch

logger = logging.getLogger(__name__)

class EnhancedPersonalizedSearch(PersonalizedEmailSearch):
    """
    Enhanced personalized search with machine learning intelligence
    """
    
    def __init__(self):
        super().__init__()
        self.intelligence = AdvancedReceiptIntelligence()
        self.learning_enabled = True
        
        # Load existing intelligence if available
        try:
            self.intelligence.load_intelligence('receipt_intelligence.json')
            logger.info("🧠 Loaded existing receipt intelligence")
        except:
            logger.info("🧠 Starting with fresh receipt intelligence")
    
    def search_with_intelligence(self, days_back: int = 7, 
                                transactions: Optional[List[Dict]] = None) -> Dict:
        """
        Enhanced search using machine learning intelligence
        """
        logger.info(f"🧙‍♂️ Starting enhanced personalized search for last {days_back} days")
        
        # First, learn from existing data if available
        if transactions and self.learning_enabled:
            logger.info("📚 Learning from transaction data...")
            learning_result = self.intelligence.learn_from_transactions(transactions)
            logger.info(f"📊 Learned from {learning_result['transactions_analyzed']} transactions")
        
        # Get base search results
        base_results = self.search_personalized_emails(days_back)
        
        # Enhance with intelligence
        enhanced_results = self._enhance_with_intelligence(base_results, transactions)
        
        # Learn from the emails we found
        if self.learning_enabled and enhanced_results.get('emails'):
            logger.info("📚 Learning from email patterns...")
            email_learning = self.intelligence.learn_from_emails(enhanced_results['emails'])
            logger.info(f"📊 Learned from {email_learning['emails_analyzed']} emails")
            
            # Learn merchant mappings if we have transactions
            if transactions:
                mapping_learning = self.intelligence.learn_merchant_mappings(
                    transactions, enhanced_results['emails']
                )
                logger.info(f"🔗 Learned {mapping_learning['new_mappings_learned']} merchant mappings")
        
        # Save updated intelligence
        if self.learning_enabled:
            self.intelligence.save_intelligence('receipt_intelligence.json')
        
        # Add intelligence summary
        enhanced_results['intelligence_summary'] = self.intelligence.get_intelligence_summary()
        
        return enhanced_results
    
    def _enhance_with_intelligence(self, base_results: Dict, 
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
                transaction_matches = self._find_transaction_matches(email, transactions)
                enhanced_email['transaction_matches'] = transaction_matches
            
            # Generate search suggestions
            search_suggestions = self._generate_search_suggestions(email)
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
            'enhanced_search': True
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
        if sender_domain in self.intelligence.email_patterns:
            pattern = self.intelligence.email_patterns[sender_domain]
            likelihood = pattern.receipt_likelihood
            confidence = pattern.confidence
            factors.append(f"Learned sender pattern: {sender_domain}")
        
        # Check subject keywords
        subject = email.get('subject', '').lower()
        receipt_keywords = ['receipt', 'payment', 'invoice', 'confirmation', 'order', 'purchase']
        keyword_matches = [kw for kw in receipt_keywords if kw in subject]
        if keyword_matches:
            likelihood += 0.2
            factors.append(f"Subject keywords: {', '.join(keyword_matches)}")
        
        # Check for amount patterns in body
        body = email.get('body', '')
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
    
    def _find_transaction_matches(self, email: Dict, transactions: List[Dict]) -> List[Dict]:
        """
        Find potential transaction matches for an email
        """
        matches = []
        
        email_body = email.get('body', '')
        email_date = email.get('date')
        
        for transaction in transactions:
            confidence = 0.0
            reasons = []
            
            # Amount matching
            tx_amount = transaction.get('amount')
            if tx_amount and str(tx_amount) in email_body:
                confidence += 0.4
                reasons.append('amount_match')
            
            # Date matching
            tx_date = transaction.get('date')
            if email_date and tx_date and email_date == tx_date:
                confidence += 0.3
                reasons.append('date_match')
            
            # Merchant matching
            tx_merchant = transaction.get('merchant', '').strip()
            if tx_merchant:
                # Direct match
                if tx_merchant.lower() in email.get('subject', '').lower():
                    confidence += 0.3
                    reasons.append('merchant_match')
                
                # Check learned mappings
                if tx_merchant in self.intelligence.merchant_mappings:
                    mapping = self.intelligence.merchant_mappings[tx_merchant]
                    sender_domain = self._extract_domain(email.get('from', ''))
                    if sender_domain == mapping.email_sender:
                        confidence += 0.2
                        reasons.append('learned_mapping')
            
            if confidence > 0.3:
                matches.append({
                    'transaction': transaction,
                    'confidence': min(confidence, 1.0),
                    'reasons': reasons
                })
        
        # Sort by confidence
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        return matches
    
    def _generate_search_suggestions(self, email: Dict) -> List[str]:
        """
        Generate search suggestions for finding related emails
        """
        suggestions = []
        
        # Extract from subject
        subject = email.get('subject', '')
        words = re.findall(r'\b\w+\b', subject.lower())
        suggestions.extend(words[:3])  # First 3 words
        
        # Extract from sender
        sender = email.get('from', '')
        if '@' in sender:
            domain = sender.split('@')[1]
            suggestions.append(domain.split('.')[0])  # Domain name without TLD
        
        # Extract amounts
        body = email.get('body', '')
        amounts = re.findall(r'\$\d+\.?\d*', body)
        suggestions.extend(amounts[:2])  # First 2 amounts
        
        # Add common receipt terms
        suggestions.extend(['receipt', 'payment', 'confirmation'])
        
        return list(set(suggestions))  # Remove duplicates
    
    def _generate_intelligence_insights(self, email: Dict) -> List[Dict]:
        """
        Generate intelligence insights for an email
        """
        insights = []
        
        sender_domain = self._extract_domain(email.get('from', ''))
        
        # Check if this is a new sender pattern
        if sender_domain not in self.intelligence.email_patterns:
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
    
    def _extract_domain(self, email: str) -> str:
        """Extract domain from email address"""
        if '@' in email:
            return email.split('@')[1].lower()
        return email.lower()
    
    def get_intelligent_search_strategies(self, transactions: List[Dict]) -> List[Dict]:
        """
        Generate intelligent search strategies based on learned patterns
        """
        strategies = []
        
        # Analyze transaction patterns
        transaction_analysis = self.intelligence.learn_from_transactions(transactions)
        
        # Generate strategies based on learned patterns
        for merchant, pattern in self.intelligence.transaction_patterns.items():
            if pattern.confidence > 0.7:  # High confidence patterns
                strategy = {
                    'name': f"intelligent_{merchant.lower().replace(' ', '_')}",
                    'description': f"Intelligent search for {merchant} receipts",
                    'query': self._build_merchant_query(merchant, pattern),
                    'expected_count': pattern.sample_count,
                    'confidence': pattern.confidence,
                    'receipt_likelihood': pattern.receipt_likelihood
                }
                strategies.append(strategy)
        
        # Generate strategies based on payment methods
        payment_methods = defaultdict(list)
        for tx in transactions:
            method = tx.get('payment_method', '')
            if method:
                payment_methods[method].append(tx)
        
        for method, tx_list in payment_methods.items():
            if len(tx_list) >= 3:  # At least 3 transactions
                strategy = {
                    'name': f"intelligent_{method.lower()}",
                    'description': f"Intelligent search for {method} payments",
                    'query': self._build_payment_method_query(method),
                    'expected_count': len(tx_list),
                    'confidence': 0.6,
                    'receipt_likelihood': self._get_payment_method_receipt_likelihood(method)
                }
                strategies.append(strategy)
        
        return strategies
    
    def _build_merchant_query(self, merchant: str, pattern: 'TransactionPattern') -> str:
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
    
    def get_learning_recommendations(self) -> List[Dict]:
        """
        Get recommendations for improving the learning system
        """
        recommendations = []
        
        summary = self.intelligence.get_intelligence_summary()
        
        # Check pattern diversity
        if summary['transaction_patterns'] < 10:
            recommendations.append({
                'type': 'more_data',
                'message': 'Need more transaction data for better learning',
                'suggestion': 'Process more transactions to improve pattern recognition'
            })
        
        # Check confidence levels
        low_confidence_patterns = summary['transaction_patterns'] - summary['high_confidence_patterns']
        if low_confidence_patterns > summary['high_confidence_patterns']:
            recommendations.append({
                'type': 'confidence_improvement',
                'message': 'Many patterns have low confidence',
                'suggestion': 'Process more transactions for existing merchants to improve confidence'
            })
        
        # Check mapping coverage
        if summary['merchant_mappings'] < 5:
            recommendations.append({
                'type': 'mapping_coverage',
                'message': 'Limited merchant-email mappings',
                'suggestion': 'Process more transactions and emails together to learn mappings'
            })
        
        return recommendations 
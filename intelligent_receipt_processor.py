#!/usr/bin/env python3
"""
Intelligent Receipt Processor
Integrates advanced machine learning with your existing personalized email search
"""

import logging
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import numpy as np

logger = logging.getLogger(__name__)

class IntelligentReceiptProcessor:
    """
    Advanced receipt processor that learns from your transactions and emails
    to build intelligent receipt detection and matching
    """
    
    def __init__(self):
        self.learned_patterns = {}
        self.merchant_mappings = {}
        self.receipt_likelihoods = {}
        self.search_suggestions = {}
        self.confidence_threshold = 0.7
        
        # Load existing intelligence
        self._load_intelligence()
        
        # Initialize with common patterns
        self._initialize_common_patterns()
    
    def _initialize_common_patterns(self):
        """Initialize with common receipt patterns based on your data"""
        
        # Your specific merchant patterns
        self.learned_patterns.update({
            'CLAUDE': {
                'type': 'subscription',
                'parent_merchant': 'Anthropic',
                'receipt_likelihood': 0.95,
                'email_domains': ['anthropic.com', 'claude.ai'],
                'search_terms': ['claude', 'anthropic', 'subscription'],
                'confidence': 0.9
            },
            'SQUARE': {
                'type': 'payment_processor',
                'parent_merchant': 'Square',
                'receipt_likelihood': 0.98,
                'email_domains': ['square.com', 'squareup.com', 'receipts@square.com'],
                'search_terms': ['square', 'receipt', 'payment'],
                'confidence': 0.95
            },
            'PAYPAL': {
                'type': 'payment_processor',
                'parent_merchant': 'PayPal',
                'receipt_likelihood': 0.9,
                'email_domains': ['paypal.com', 'service@paypal.com'],
                'search_terms': ['paypal', 'payment', 'receipt'],
                'confidence': 0.85
            },
            'NETFLIX': {
                'type': 'subscription',
                'parent_merchant': 'Netflix',
                'receipt_likelihood': 0.8,
                'email_domains': ['netflix.com', 'service@paypal.com'],
                'search_terms': ['netflix', 'subscription', 'payment'],
                'confidence': 0.8
            },
            'APPLE': {
                'type': 'subscription',
                'parent_merchant': 'Apple',
                'receipt_likelihood': 0.9,
                'email_domains': ['apple.com', 'noreply@apple.com'],
                'search_terms': ['apple', 'billing', 'receipt'],
                'confidence': 0.9
            },
            'UBER': {
                'type': 'transportation',
                'parent_merchant': 'Uber',
                'receipt_likelihood': 0.85,
                'email_domains': ['uber.com', 'receipts@uber.com'],
                'search_terms': ['uber', 'ride', 'receipt'],
                'confidence': 0.8
            }
        })
        
        # Payment method patterns
        self.receipt_likelihoods.update({
            'credit_card': 0.8,
            'paypal': 0.9,
            'square': 0.95,
            'stripe': 0.9,
            'debit_card': 0.6,
            'cash': 0.1,
            'atm': 0.0
        })
        
        # Category patterns
        self.receipt_likelihoods.update({
            'Food & Dining': 0.9,
            'Technology': 0.8,
            'Entertainment': 0.7,
            'Transportation': 0.8,
            'Shopping': 0.6,
            'ATM': 0.0
        })
    
    def learn_from_transactions(self, transactions: List[Dict]) -> Dict:
        """
        Learn patterns from your transaction data
        """
        logger.info(f"🧠 Learning from {len(transactions)} transactions")
        
        # Group transactions by merchant
        merchant_groups = defaultdict(list)
        for tx in transactions:
            merchant = tx.get('merchant', '').strip()
            if merchant:
                merchant_groups[merchant].append(tx)
        
        new_patterns = 0
        for merchant, tx_list in merchant_groups.items():
            if len(tx_list) >= 2:  # Need at least 2 transactions to learn
                pattern = self._analyze_merchant_pattern(merchant, tx_list)
                if pattern:
                    self.learned_patterns[merchant] = pattern
                    new_patterns += 1
        
        logger.info(f"📊 Learned {new_patterns} new transaction patterns")
        self._save_intelligence()
        
        return {
            'transactions_analyzed': len(transactions),
            'merchants_analyzed': len(merchant_groups),
            'new_patterns_learned': new_patterns,
            'total_patterns': len(self.learned_patterns)
        }
    
    def learn_from_emails(self, emails: List[Dict]) -> Dict:
        """
        Learn patterns from your email data
        """
        logger.info(f"📧 Learning from {len(emails)} emails")
        
        # Group emails by sender domain
        sender_groups = defaultdict(list)
        for email in emails:
            sender = email.get('from', '')
            domain = self._extract_domain(sender)
            if domain:
                sender_groups[domain].append(email)
        
        new_patterns = 0
        for domain, email_list in sender_groups.items():
            if len(email_list) >= 2:
                pattern = self._analyze_email_pattern(domain, email_list)
                if pattern:
                    # Update existing patterns or create new ones
                    for merchant, merchant_pattern in self.learned_patterns.items():
                        if domain in merchant_pattern.get('email_domains', []):
                            merchant_pattern['confidence'] = min(0.95, merchant_pattern['confidence'] + 0.1)
                            new_patterns += 1
                            break
                    else:
                        # Create new pattern
                        self.learned_patterns[f"EMAIL_{domain}"] = pattern
                        new_patterns += 1
        
        logger.info(f"📊 Learned {new_patterns} new email patterns")
        self._save_intelligence()
        
        return {
            'emails_analyzed': len(emails),
            'senders_analyzed': len(sender_groups),
            'new_patterns_learned': new_patterns,
            'total_patterns': len(self.learned_patterns)
        }
    
    def predict_receipt_likelihood(self, transaction: Dict) -> Dict:
        """
        Predict likelihood of receipt for a transaction
        """
        merchant = transaction.get('merchant', '').strip()
        category = transaction.get('category', '')
        payment_method = transaction.get('payment_method', '')
        amount = transaction.get('amount', 0)
        has_tip = transaction.get('has_tip', False)
        
        # Base likelihood from learned patterns
        base_likelihood = 0.5
        confidence = 0.3
        factors = []
        
        # Check learned merchant pattern
        if merchant in self.learned_patterns:
            pattern = self.learned_patterns[merchant]
            base_likelihood = pattern['receipt_likelihood']
            confidence = pattern['confidence']
            factors.append(f"Learned pattern: {merchant}")
        
        # Payment method adjustment
        payment_likelihood = self.receipt_likelihoods.get(payment_method.lower(), 0.5)
        base_likelihood = (base_likelihood + payment_likelihood) / 2
        factors.append(f"Payment method: {payment_method}")
        
        # Category adjustment
        category_likelihood = self.receipt_likelihoods.get(category, 0.5)
        base_likelihood = (base_likelihood + category_likelihood) / 2
        factors.append(f"Category: {category}")
        
        # Tip adjustment
        if has_tip:
            base_likelihood += 0.15
            factors.append("Has tip")
        
        # Amount adjustment
        if amount > 100:
            base_likelihood += 0.1
            factors.append("High amount")
        elif amount < 5:
            base_likelihood -= 0.1
            factors.append("Low amount")
        
        # Description keywords
        description = transaction.get('description', '').lower()
        if any(keyword in description for keyword in ['subscription', 'monthly', 'recurring']):
            base_likelihood += 0.1
            factors.append("Subscription transaction")
        
        return {
            'likelihood': min(max(base_likelihood, 0.0), 1.0),
            'confidence': min(confidence, 1.0),
            'factors': factors
        }
    
    def find_receipt_candidates(self, transaction: Dict, emails: List[Dict]) -> List[Dict]:
        """
        Find potential receipt emails for a transaction
        """
        candidates = []
        
        merchant = transaction.get('merchant', '').strip()
        amount = transaction.get('amount')
        date = transaction.get('date')
        
        for email in emails:
            confidence = 0.0
            reasons = []
            
            # Amount matching
            email_body = email.get('body', '')
            if amount and str(amount) in email_body:
                confidence += 0.4
                reasons.append('amount_match')
            
            # Date matching
            email_date = email.get('date')
            if date and date == email_date:
                confidence += 0.3
                reasons.append('date_match')
            
            # Merchant matching
            if merchant:
                # Direct merchant match
                if merchant.lower() in email.get('subject', '').lower():
                    confidence += 0.3
                    reasons.append('merchant_match')
                
                # Check learned patterns
                if merchant in self.learned_patterns:
                    pattern = self.learned_patterns[merchant]
                    sender_domain = self._extract_domain(email.get('from', ''))
                    if sender_domain in pattern.get('email_domains', []):
                        confidence += 0.2
                        reasons.append('learned_mapping')
            
            # Sender pattern matching
            sender_domain = self._extract_domain(email.get('from', ''))
            for pattern in self.learned_patterns.values():
                if sender_domain in pattern.get('email_domains', []):
                    confidence += pattern['receipt_likelihood'] * 0.2
                    reasons.append('sender_pattern')
                    break
            
            # Subject keyword matching
            subject = email.get('subject', '').lower()
            receipt_keywords = ['receipt', 'payment', 'invoice', 'confirmation', 'order']
            if any(keyword in subject for keyword in receipt_keywords):
                confidence += 0.1
                reasons.append('subject_keywords')
            
            if confidence > 0.3:  # Minimum threshold
                candidates.append({
                    'email': email,
                    'confidence': min(confidence, 1.0),
                    'reasons': reasons
                })
        
        # Sort by confidence
        candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        return candidates
    
    def suggest_search_terms(self, transaction: Dict) -> List[str]:
        """
        Suggest search terms for finding receipt emails
        """
        suggestions = []
        
        merchant = transaction.get('merchant', '').strip()
        amount = transaction.get('amount')
        
        # Basic merchant search
        if merchant:
            suggestions.append(merchant)
            
            # Clean up merchant name
            clean_merchant = re.sub(r'[^\w\s]', ' ', merchant).strip()
            if clean_merchant != merchant:
                suggestions.append(clean_merchant)
            
            # Extract key words
            words = clean_merchant.split()
            if len(words) > 1:
                suggestions.extend(words[:2])  # First two words
        
        # Check learned patterns for additional terms
        if merchant in self.learned_patterns:
            pattern = self.learned_patterns[merchant]
            suggestions.extend(pattern.get('search_terms', []))
        
        # Amount search
        if amount:
            suggestions.append(str(amount))
            suggestions.append(f"${amount}")
        
        # Add common receipt keywords
        suggestions.extend(['receipt', 'payment', 'confirmation'])
        
        return list(set(suggestions))  # Remove duplicates
    
    def enhance_search_strategies(self, base_strategies: List[Dict]) -> List[Dict]:
        """
        Enhance existing search strategies with learned intelligence
        """
        enhanced_strategies = []
        
        for strategy in base_strategies:
            enhanced_strategy = strategy.copy()
            
            # Add learned patterns to query
            learned_terms = []
            for merchant, pattern in self.learned_patterns.items():
                if pattern['confidence'] > 0.8:  # High confidence patterns
                    learned_terms.extend(pattern.get('search_terms', []))
            
            if learned_terms:
                enhanced_strategy['query'] += f" OR {' OR '.join(learned_terms[:5])}"
                enhanced_strategy['description'] += " (Enhanced with learned patterns)"
            
            enhanced_strategies.append(enhanced_strategy)
        
        return enhanced_strategies
    
    def _analyze_merchant_pattern(self, merchant: str, transactions: List[Dict]) -> Optional[Dict]:
        """Analyze pattern for a specific merchant"""
        
        if len(transactions) < 2:
            return None
        
        # Calculate statistics
        amounts = [tx.get('amount', 0) for tx in transactions]
        categories = [tx.get('category', '') for tx in transactions]
        payment_methods = [tx.get('payment_method', '') for tx in transactions]
        has_tips = [tx.get('has_tip', False) for tx in transactions]
        
        # Most common values
        most_common_category = Counter(categories).most_common(1)[0][0] if categories else ''
        most_common_payment = Counter(payment_methods).most_common(1)[0][0] if payment_methods else ''
        
        # Calculate receipt likelihood
        receipt_likelihood = 0.5
        
        # Adjust based on payment method
        payment_likelihood = self.receipt_likelihoods.get(most_common_payment.lower(), 0.5)
        receipt_likelihood = payment_likelihood
        
        # Adjust based on tip frequency
        tip_frequency = sum(has_tips) / len(has_tips)
        if tip_frequency > 0.5:
            receipt_likelihood += 0.1
        
        # Calculate confidence based on sample size
        confidence = min(0.9, 0.3 + (len(transactions) * 0.1))
        
        # Generate search terms
        search_terms = []
        clean_merchant = re.sub(r'[^\w\s]', ' ', merchant).strip()
        words = clean_merchant.split()
        search_terms.extend(words[:3])
        
        # Add common receipt terms
        search_terms.extend(['receipt', 'payment', 'confirmation'])
        
        return {
            'type': 'learned_merchant',
            'parent_merchant': merchant,
            'receipt_likelihood': min(receipt_likelihood, 1.0),
            'email_domains': [],  # Will be learned from emails
            'search_terms': search_terms,
            'confidence': confidence,
            'sample_count': len(transactions),
            'last_seen': datetime.now().isoformat()
        }
    
    def _analyze_email_pattern(self, domain: str, emails: List[Dict]) -> Optional[Dict]:
        """Analyze pattern for a specific email sender"""
        
        if len(emails) < 2:
            return None
        
        # Extract keywords from subjects and bodies
        subjects = [email.get('subject', '') for email in emails]
        bodies = [email.get('body', '') for email in emails]
        
        # Find common keywords
        all_text = ' '.join(subjects + bodies).lower()
        words = re.findall(r'\b\w+\b', all_text)
        
        # Filter out common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if word not in common_words and len(word) > 3]
        
        # Get most common keywords
        keyword_counts = Counter(keywords)
        common_keywords = [word for word, count in keyword_counts.most_common(10) if count > 1]
        
        # Calculate receipt likelihood
        receipt_keywords = ['receipt', 'payment', 'invoice', 'confirmation', 'order', 'purchase']
        receipt_keyword_count = sum(1 for keyword in common_keywords if keyword in receipt_keywords)
        receipt_likelihood = min(0.9, 0.3 + (receipt_keyword_count * 0.15))
        
        # Calculate confidence based on sample size
        confidence = min(0.9, 0.3 + (len(emails) * 0.1))
        
        return {
            'type': 'learned_email',
            'parent_merchant': domain,
            'receipt_likelihood': receipt_likelihood,
            'email_domains': [domain],
            'search_terms': common_keywords[:5],
            'confidence': confidence,
            'sample_count': len(emails),
            'last_seen': datetime.now().isoformat()
        }
    
    def _extract_domain(self, email: str) -> str:
        """Extract domain from email address"""
        if '@' in email:
            return email.split('@')[1].lower()
        return email.lower()
    
    def _load_intelligence(self):
        """Load learned intelligence from file"""
        try:
            with open('receipt_intelligence.json', 'r') as f:
                data = json.load(f)
                self.learned_patterns.update(data.get('learned_patterns', {}))
                self.merchant_mappings.update(data.get('merchant_mappings', {}))
                logger.info("📂 Loaded existing intelligence")
        except FileNotFoundError:
            logger.info("📂 No existing intelligence file found")
        except Exception as e:
            logger.warning(f"⚠️ Error loading intelligence: {e}")
    
    def _save_intelligence(self):
        """Save learned intelligence to file"""
        try:
            data = {
                'learned_patterns': self.learned_patterns,
                'merchant_mappings': self.merchant_mappings,
                'timestamp': datetime.now().isoformat()
            }
            
            with open('receipt_intelligence.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info("💾 Saved intelligence")
        except Exception as e:
            logger.error(f"❌ Error saving intelligence: {e}")
    
    def get_intelligence_summary(self) -> Dict:
        """Get summary of learned intelligence"""
        
        high_confidence_patterns = len([p for p in self.learned_patterns.values() if p.get('confidence', 0) > 0.8])
        
        return {
            'learned_patterns': len(self.learned_patterns),
            'merchant_mappings': len(self.merchant_mappings),
            'high_confidence_patterns': high_confidence_patterns,
            'learning_progress': {
                'total_patterns': len(self.learned_patterns),
                'high_confidence_patterns': high_confidence_patterns,
                'confidence_rate': high_confidence_patterns / max(len(self.learned_patterns), 1),
                'learning_stage': 'beginner' if len(self.learned_patterns) < 10 else 'intermediate' if len(self.learned_patterns) < 50 else 'advanced'
            }
        } 
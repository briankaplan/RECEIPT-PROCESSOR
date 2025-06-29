#!/usr/bin/env python3
"""
Advanced Receipt Intelligence System
Learns from transactions and emails to build intelligent receipt detection
"""

import logging
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import numpy as np
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class TransactionPattern:
    """Pattern learned from transaction analysis"""
    merchant: str
    category: str
    payment_method: str
    amount_range: Tuple[float, float]
    has_tip: bool
    receipt_likelihood: float
    confidence: float
    sample_count: int
    last_seen: datetime
    patterns: List[str]

@dataclass
class EmailPattern:
    """Pattern learned from email analysis"""
    sender_domain: str
    subject_keywords: List[str]
    body_keywords: List[str]
    receipt_likelihood: float
    confidence: float
    sample_count: int
    last_seen: datetime

@dataclass
class MerchantMapping:
    """Mapping between transaction merchants and email senders"""
    transaction_merchant: str
    email_sender: str
    confidence: float
    sample_count: int
    last_seen: datetime
    amount_correlation: float

class AdvancedReceiptIntelligence:
    """
    Advanced machine learning system for receipt detection and matching
    """
    
    def __init__(self):
        self.transaction_patterns: Dict[str, TransactionPattern] = {}
        self.email_patterns: Dict[str, EmailPattern] = {}
        self.merchant_mappings: Dict[str, MerchantMapping] = {}
        self.learned_rules: List[Dict] = []
        self.confidence_threshold = 0.7
        
        # Initialize with common patterns
        self._initialize_common_patterns()
    
    def _initialize_common_patterns(self):
        """Initialize with common receipt patterns"""
        
        # Common payment processors that send receipts
        payment_processors = {
            'square': {'receipt_likelihood': 0.95, 'confidence': 0.9},
            'paypal': {'receipt_likelihood': 0.9, 'confidence': 0.85},
            'stripe': {'receipt_likelihood': 0.9, 'confidence': 0.85},
            'stripe.com': {'receipt_likelihood': 0.9, 'confidence': 0.85},
            'squareup.com': {'receipt_likelihood': 0.95, 'confidence': 0.9},
            'paypal.com': {'receipt_likelihood': 0.9, 'confidence': 0.85}
        }
        
        for processor, config in payment_processors.items():
            self.email_patterns[processor] = EmailPattern(
                sender_domain=processor,
                subject_keywords=['receipt', 'payment', 'confirmation'],
                body_keywords=['receipt', 'payment', 'amount', 'total'],
                receipt_likelihood=config['receipt_likelihood'],
                confidence=config['confidence'],
                sample_count=100,  # High confidence from many samples
                last_seen=datetime.now()
            )
        
        # Common subscription services
        subscription_services = {
            'claude': {'parent': 'anthropic.com', 'receipt_likelihood': 0.9},
            'netflix': {'parent': 'netflix.com', 'receipt_likelihood': 0.8},
            'spotify': {'parent': 'spotify.com', 'receipt_likelihood': 0.8},
            'github': {'parent': 'github.com', 'receipt_likelihood': 0.8},
            'zoom': {'parent': 'zoom.us', 'receipt_likelihood': 0.8},
            'slack': {'parent': 'slack.com', 'receipt_likelihood': 0.8},
            'notion': {'parent': 'notion.so', 'receipt_likelihood': 0.8},
            'figma': {'parent': 'figma.com', 'receipt_likelihood': 0.8},
            'canva': {'parent': 'canva.com', 'receipt_likelihood': 0.8}
        }
        
        for service, config in subscription_services.items():
            self.merchant_mappings[service] = MerchantMapping(
                transaction_merchant=service.upper(),
                email_sender=config['parent'],
                confidence=0.9,
                sample_count=50,
                last_seen=datetime.now(),
                amount_correlation=0.8
            )
    
    def learn_from_transactions(self, transactions: List[Dict]) -> Dict:
        """
        Learn patterns from transaction data
        """
        logger.info(f"🧠 Learning from {len(transactions)} transactions")
        
        # Group transactions by merchant
        merchant_groups = defaultdict(list)
        for tx in transactions:
            merchant = tx.get('merchant', '').strip()
            if merchant:
                merchant_groups[merchant].append(tx)
        
        # Analyze each merchant group
        new_patterns = 0
        for merchant, tx_list in merchant_groups.items():
            if len(tx_list) >= 2:  # Need at least 2 transactions to learn patterns
                pattern = self._analyze_merchant_pattern(merchant, tx_list)
                if pattern:
                    self.transaction_patterns[merchant] = pattern
                    new_patterns += 1
        
        logger.info(f"📊 Learned {new_patterns} new transaction patterns")
        
        return {
            'transactions_analyzed': len(transactions),
            'merchants_analyzed': len(merchant_groups),
            'new_patterns_learned': new_patterns,
            'total_patterns': len(self.transaction_patterns)
        }
    
    def learn_from_emails(self, emails: List[Dict]) -> Dict:
        """
        Learn patterns from email data
        """
        logger.info(f"📧 Learning from {len(emails)} emails")
        
        # Group emails by sender domain
        sender_groups = defaultdict(list)
        for email in emails:
            sender = email.get('from', '')
            domain = self._extract_domain(sender)
            if domain:
                sender_groups[domain].append(email)
        
        # Analyze each sender group
        new_patterns = 0
        for domain, email_list in sender_groups.items():
            if len(email_list) >= 2:  # Need at least 2 emails to learn patterns
                pattern = self._analyze_sender_pattern(domain, email_list)
                if pattern:
                    self.email_patterns[domain] = pattern
                    new_patterns += 1
        
        logger.info(f"📊 Learned {new_patterns} new email patterns")
        
        return {
            'emails_analyzed': len(emails),
            'senders_analyzed': len(sender_groups),
            'new_patterns_learned': new_patterns,
            'total_patterns': len(self.email_patterns)
        }
    
    def learn_merchant_mappings(self, transactions: List[Dict], emails: List[Dict]) -> Dict:
        """
        Learn mappings between transaction merchants and email senders
        """
        logger.info("🔗 Learning merchant-email mappings")
        
        # Create potential matches based on amount and date
        potential_matches = []
        
        for tx in transactions:
            tx_date = tx.get('date')
            tx_amount = tx.get('amount')
            
            if not tx_date or not tx_amount:
                continue
            
            # Find emails with matching amount and date
            for email in emails:
                email_date = email.get('date')
                if tx_date == email_date:
                    # Check if amount appears in email
                    email_body = email.get('body', '')
                    if str(tx_amount) in email_body:
                        potential_matches.append({
                            'transaction': tx,
                            'email': email,
                            'confidence': 0.8  # High confidence for amount match
                        })
        
        # Group matches by merchant-sender pairs
        mapping_groups = defaultdict(list)
        for match in potential_matches:
            tx = match['transaction']
            email = match['email']
            
            merchant = tx.get('merchant', '').strip()
            sender_domain = self._extract_domain(email.get('from', ''))
            
            if merchant and sender_domain:
                key = f"{merchant}|{sender_domain}"
                mapping_groups[key].append(match)
        
        # Create mappings for groups with multiple matches
        new_mappings = 0
        for key, matches in mapping_groups.items():
            if len(matches) >= 2:  # Need at least 2 matches to create mapping
                merchant, sender_domain = key.split('|')
                
                # Calculate confidence based on number of matches
                confidence = min(0.9, 0.5 + (len(matches) * 0.1))
                
                # Calculate amount correlation
                amounts = [m['transaction']['amount'] for m in matches]
                amount_correlation = np.std(amounts) / np.mean(amounts) if amounts else 0.5
                
                mapping = MerchantMapping(
                    transaction_merchant=merchant,
                    email_sender=sender_domain,
                    confidence=confidence,
                    sample_count=len(matches),
                    last_seen=datetime.now(),
                    amount_correlation=amount_correlation
                )
                
                self.merchant_mappings[merchant] = mapping
                new_mappings += 1
        
        logger.info(f"🔗 Learned {new_mappings} new merchant mappings")
        
        return {
            'potential_matches': len(potential_matches),
            'new_mappings_learned': new_mappings,
            'total_mappings': len(self.merchant_mappings)
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
        
        # Check if we have a learned pattern for this merchant
        if merchant in self.transaction_patterns:
            pattern = self.transaction_patterns[merchant]
            base_likelihood = pattern.receipt_likelihood
            confidence = pattern.confidence
        else:
            confidence = 0.3
        
        # Adjust based on payment method
        payment_adjustments = {
            'credit_card': 0.1,
            'paypal': 0.2,
            'square': 0.25,
            'stripe': 0.2,
            'debit_card': 0.0,
            'cash': -0.3,
            'atm': -0.5
        }
        
        payment_adjustment = payment_adjustments.get(payment_method.lower(), 0)
        base_likelihood += payment_adjustment
        
        # Adjust based on category
        category_adjustments = {
            'Food & Dining': 0.15,
            'Technology': 0.1,
            'Entertainment': 0.05,
            'Transportation': 0.1,
            'Shopping': 0.0,
            'ATM': -0.5
        }
        
        category_adjustment = category_adjustments.get(category, 0)
        base_likelihood += category_adjustment
        
        # Adjust based on tip
        if has_tip:
            base_likelihood += 0.2
        
        # Adjust based on amount
        if amount > 100:
            base_likelihood += 0.1
        elif amount < 5:
            base_likelihood -= 0.1
        
        # Ensure likelihood is between 0 and 1
        final_likelihood = max(0.0, min(1.0, base_likelihood))
        
        return {
            'likelihood': final_likelihood,
            'confidence': confidence,
            'factors': {
                'merchant_pattern': merchant in self.transaction_patterns,
                'payment_method': payment_method,
                'category': category,
                'has_tip': has_tip,
                'amount': amount
            }
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
                
                # Check learned mappings
                if merchant in self.merchant_mappings:
                    mapping = self.merchant_mappings[merchant]
                    sender_domain = self._extract_domain(email.get('from', ''))
                    if sender_domain == mapping.email_sender:
                        confidence += 0.2
                        reasons.append('learned_mapping')
            
            # Sender pattern matching
            sender_domain = self._extract_domain(email.get('from', ''))
            if sender_domain in self.email_patterns:
                pattern = self.email_patterns[sender_domain]
                confidence += pattern.receipt_likelihood * 0.2
                reasons.append('sender_pattern')
            
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
        
        # Amount search
        if amount:
            suggestions.append(str(amount))
            suggestions.append(f"${amount}")
        
        # Check learned mappings for additional terms
        if merchant in self.merchant_mappings:
            mapping = self.merchant_mappings[merchant]
            suggestions.append(mapping.email_sender)
        
        # Add common receipt keywords
        suggestions.extend(['receipt', 'payment', 'confirmation'])
        
        return list(set(suggestions))  # Remove duplicates
    
    def _analyze_merchant_pattern(self, merchant: str, transactions: List[Dict]) -> Optional[TransactionPattern]:
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
        
        # Amount range
        min_amount = min(amounts)
        max_amount = max(amounts)
        
        # Calculate receipt likelihood based on patterns
        receipt_likelihood = 0.5
        
        # Adjust based on payment method
        payment_likelihoods = {
            'credit_card': 0.8,
            'paypal': 0.9,
            'square': 0.95,
            'stripe': 0.9,
            'debit_card': 0.6,
            'cash': 0.1,
            'atm': 0.0
        }
        
        if most_common_payment in payment_likelihoods:
            receipt_likelihood = payment_likelihoods[most_common_payment]
        
        # Adjust based on tip frequency
        tip_frequency = sum(has_tips) / len(has_tips)
        if tip_frequency > 0.5:
            receipt_likelihood += 0.1
        
        # Adjust based on amount consistency
        amount_std = np.std(amounts)
        amount_mean = np.mean(amounts)
        if amount_mean > 0:
            cv = amount_std / amount_mean
            if cv < 0.5:  # Low coefficient of variation (consistent amounts)
                receipt_likelihood += 0.1
        
        # Calculate confidence based on sample size
        confidence = min(0.9, 0.3 + (len(transactions) * 0.1))
        
        # Extract patterns
        patterns = []
        if tip_frequency > 0.5:
            patterns.append('frequent_tips')
        if cv < 0.5:
            patterns.append('consistent_amounts')
        if most_common_payment in ['paypal', 'square', 'stripe']:
            patterns.append('digital_payment')
        
        return TransactionPattern(
            merchant=merchant,
            category=most_common_category,
            payment_method=most_common_payment,
            amount_range=(min_amount, max_amount),
            has_tip=tip_frequency > 0.5,
            receipt_likelihood=min(receipt_likelihood, 1.0),
            confidence=confidence,
            sample_count=len(transactions),
            last_seen=datetime.now(),
            patterns=patterns
        )
    
    def _analyze_sender_pattern(self, domain: str, emails: List[Dict]) -> Optional[EmailPattern]:
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
        
        return EmailPattern(
            sender_domain=domain,
            subject_keywords=common_keywords[:5],
            body_keywords=common_keywords[5:10],
            receipt_likelihood=receipt_likelihood,
            confidence=confidence,
            sample_count=len(emails),
            last_seen=datetime.now()
        )
    
    def _extract_domain(self, email: str) -> str:
        """Extract domain from email address"""
        if '@' in email:
            return email.split('@')[1].lower()
        return email.lower()
    
    def get_intelligence_summary(self) -> Dict:
        """Get summary of learned intelligence"""
        
        return {
            'transaction_patterns': len(self.transaction_patterns),
            'email_patterns': len(self.email_patterns),
            'merchant_mappings': len(self.merchant_mappings),
            'high_confidence_patterns': len([p for p in self.transaction_patterns.values() if p.confidence > 0.8]),
            'high_confidence_mappings': len([m for m in self.merchant_mappings.values() if m.confidence > 0.8]),
            'patterns_by_category': self._get_patterns_by_category(),
            'top_merchants': self._get_top_merchants(),
            'learning_progress': self._calculate_learning_progress()
        }
    
    def _get_patterns_by_category(self) -> Dict[str, int]:
        """Get count of patterns by category"""
        categories = defaultdict(int)
        for pattern in self.transaction_patterns.values():
            categories[pattern.category] += 1
        return dict(categories)
    
    def _get_top_merchants(self) -> List[Dict]:
        """Get top merchants by sample count"""
        merchants = []
        for merchant, pattern in self.transaction_patterns.items():
            merchants.append({
                'merchant': merchant,
                'sample_count': pattern.sample_count,
                'receipt_likelihood': pattern.receipt_likelihood,
                'confidence': pattern.confidence
            })
        
        # Sort by sample count
        merchants.sort(key=lambda x: x['sample_count'], reverse=True)
        return merchants[:10]
    
    def _calculate_learning_progress(self) -> Dict:
        """Calculate learning progress metrics"""
        total_patterns = len(self.transaction_patterns) + len(self.email_patterns)
        high_confidence_patterns = len([p for p in self.transaction_patterns.values() if p.confidence > 0.8])
        high_confidence_emails = len([p for p in self.email_patterns.values() if p.confidence > 0.8])
        
        return {
            'total_patterns': total_patterns,
            'high_confidence_patterns': high_confidence_patterns + high_confidence_emails,
            'confidence_rate': (high_confidence_patterns + high_confidence_emails) / max(total_patterns, 1),
            'learning_stage': 'beginner' if total_patterns < 10 else 'intermediate' if total_patterns < 50 else 'advanced'
        }
    
    def save_intelligence(self, filepath: str) -> bool:
        """Save learned intelligence to file"""
        try:
            data = {
                'transaction_patterns': {k: asdict(v) for k, v in self.transaction_patterns.items()},
                'email_patterns': {k: asdict(v) for k, v in self.email_patterns.items()},
                'merchant_mappings': {k: asdict(v) for k, v in self.merchant_mappings.items()},
                'learned_rules': self.learned_rules,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"💾 Saved intelligence to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving intelligence: {str(e)}")
            return False
    
    def load_intelligence(self, filepath: str) -> bool:
        """Load learned intelligence from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Load transaction patterns
            self.transaction_patterns = {}
            for k, v in data.get('transaction_patterns', {}).items():
                self.transaction_patterns[k] = TransactionPattern(**v)
            
            # Load email patterns
            self.email_patterns = {}
            for k, v in data.get('email_patterns', {}).items():
                self.email_patterns[k] = EmailPattern(**v)
            
            # Load merchant mappings
            self.merchant_mappings = {}
            for k, v in data.get('merchant_mappings', {}).items():
                self.merchant_mappings[k] = MerchantMapping(**v)
            
            self.learned_rules = data.get('learned_rules', [])
            
            logger.info(f"📂 Loaded intelligence from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading intelligence: {str(e)}")
            return False 
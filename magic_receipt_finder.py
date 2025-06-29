#!/usr/bin/env python3
"""
Magic Receipt Finder
Builds intelligent patterns to find receipts by analyzing transactions and emails
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
from dataclass import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ReceiptPattern:
    merchant: str
    email_domains: List[str]
    subject_keywords: List[str]
    body_keywords: List[str]
    common_amounts: List[float]
    billing_cycle: str  # monthly, yearly, one-off
    confidence: float

class MagicReceiptFinder:
    def __init__(self, mongo_client):
        self.mongo_client = mongo_client
        self.db = mongo_client['expense']
        
        # Known patterns for major merchants
        self.known_patterns = self._build_known_patterns()
        
    def _build_known_patterns(self) -> Dict[str, ReceiptPattern]:
        """Build known patterns for major merchants"""
        patterns = {}
        
        # Anthropic/Claude
        patterns['ANTHROPIC'] = ReceiptPattern(
            merchant='ANTHROPIC',
            email_domains=['anthropic.com', 'claude.ai', 'billing.anthropic.com'],
            subject_keywords=['claude', 'anthropic', 'subscription', 'billing', 'payment'],
            body_keywords=['claude', 'anthropic', 'subscription', 'billing', 'payment', 'charged'],
            common_amounts=[20.0, 25.0, 30.0, 50.0, 100.0],
            billing_cycle='monthly',
            confidence=0.95
        )
        
        # Apple
        patterns['APPLE'] = ReceiptPattern(
            merchant='APPLE',
            email_domains=['apple.com', 'itunes.com', 'icloud.com', 'appstore.com'],
            subject_keywords=['apple', 'itunes', 'icloud', 'app store', 'subscription', 'purchase'],
            body_keywords=['apple', 'itunes', 'icloud', 'app store', 'subscription', 'purchase', 'charged'],
            common_amounts=[0.99, 1.99, 2.99, 4.99, 9.99, 19.99, 29.99, 99.99],
            billing_cycle='mixed',
            confidence=0.95
        )
        
        # GitHub
        patterns['GITHUB'] = ReceiptPattern(
            merchant='GITHUB',
            email_domains=['github.com', 'noreply.github.com'],
            subject_keywords=['github', 'subscription', 'billing', 'payment'],
            body_keywords=['github', 'subscription', 'billing', 'payment', 'charged'],
            common_amounts=[4.0, 7.0, 10.0, 20.0, 44.0],
            billing_cycle='monthly',
            confidence=0.9
        )
        
        # Microsoft
        patterns['MICROSOFT'] = ReceiptPattern(
            merchant='MICROSOFT',
            email_domains=['microsoft.com', 'billing.microsoft.com'],
            subject_keywords=['microsoft', 'office', '365', 'subscription', 'billing'],
            body_keywords=['microsoft', 'office', '365', 'subscription', 'billing', 'charged'],
            common_amounts=[99.99, 149.99, 199.99, 299.99],
            billing_cycle='yearly',
            confidence=0.9
        )
        
        return patterns
    
    def analyze_transactions(self) -> Dict[str, Dict]:
        """Analyze transactions to find patterns"""
        logger.info("🔍 Analyzing transactions for receipt patterns...")
        
        # Get all transactions
        transactions = list(self.db.bank_transactions.find({}))
        logger.info(f"📊 Found {len(transactions)} transactions")
        
        # Group by merchant
        merchant_groups = defaultdict(list)
        for tx in transactions:
            merchant = tx.get('merchant', '').strip().upper()
            if merchant:
                merchant_groups[merchant].append(tx)
        
        # Analyze each merchant
        analysis = {}
        for merchant, txs in merchant_groups.items():
            if len(txs) >= 2:  # Need at least 2 transactions
                analysis[merchant] = self._analyze_merchant(merchant, txs)
                logger.info(f"✅ Analyzed {merchant}: {len(txs)} transactions")
        
        return analysis
    
    def _analyze_merchant(self, merchant: str, transactions: List[Dict]) -> Dict:
        """Analyze patterns for a specific merchant"""
        analysis = {
            'merchant': merchant,
            'transaction_count': len(transactions),
            'common_amounts': [],
            'billing_cycle': 'unknown',
            'email_domains': [],
            'confidence': 0.0
        }
        
        # Extract amounts
        amounts = [tx.get('amount', 0) for tx in transactions if tx.get('amount', 0) > 0]
        if amounts:
            # Find common amounts
            amount_counts = Counter(amounts)
            common_amounts = [amount for amount, count in amount_counts.most_common(10) 
                            if count >= 2]
            analysis['common_amounts'] = common_amounts
            
            # Determine billing cycle
            analysis['billing_cycle'] = self._determine_billing_cycle(transactions)
        
        # Calculate confidence based on transaction count
        analysis['confidence'] = min(len(transactions) / 10.0, 1.0)
        
        return analysis
    
    def _determine_billing_cycle(self, transactions: List[Dict]) -> str:
        """Determine billing cycle from transaction dates"""
        try:
            dates = []
            for tx in transactions:
                date_str = tx.get('date', '')
                if date_str:
                    try:
                        date = datetime.strptime(date_str, '%Y-%m-%d')
                        dates.append(date)
                    except:
                        continue
            
            if len(dates) < 2:
                return 'unknown'
            
            # Sort dates
            dates.sort()
            
            # Calculate intervals
            intervals = []
            for i in range(1, len(dates)):
                interval = (dates[i] - dates[i-1]).days
                intervals.append(interval)
            
            # Determine billing cycle
            avg_interval = sum(intervals) / len(intervals)
            
            if avg_interval <= 35:  # Monthly
                return 'monthly'
            elif avg_interval <= 370:  # Yearly
                return 'yearly'
            else:
                return 'one-off'
                
        except Exception as e:
            logger.error(f"Error determining billing cycle: {e}")
            return 'unknown'
    
    def find_receipt_emails(self, emails: List[Dict], target_merchants: List[str] = None) -> List[Dict]:
        """Find receipt emails using learned patterns"""
        logger.info(f"🔍 Finding receipt emails...")
        
        # Get transaction analysis
        transaction_analysis = self.analyze_transactions()
        
        # Combine with known patterns
        all_patterns = {**self.known_patterns}
        
        # Add learned patterns from transactions
        for merchant, analysis in transaction_analysis.items():
            if merchant not in all_patterns:
                all_patterns[merchant] = ReceiptPattern(
                    merchant=merchant,
                    email_domains=[],
                    subject_keywords=[],
                    body_keywords=[],
                    common_amounts=analysis['common_amounts'],
                    billing_cycle=analysis['billing_cycle'],
                    confidence=analysis['confidence']
                )
        
        receipt_candidates = []
        
        for email in emails:
            subject = email.get('subject', '').lower()
            body = email.get('body', '').lower()
            from_email = email.get('from_email', '').lower()
            
            # Check each merchant pattern
            for merchant, pattern in all_patterns.items():
                if target_merchants and merchant not in target_merchants:
                    continue
                
                # Check if email matches this merchant
                confidence = self._calculate_match_confidence(email, pattern)
                
                if confidence > 0.3:  # Minimum threshold
                    receipt_candidates.append({
                        'email': email,
                        'merchant': merchant,
                        'confidence': confidence,
                        'pattern': pattern
                    })
                    logger.info(f"✅ Found receipt for {merchant} (confidence: {confidence:.2f})")
        
        # Sort by confidence
        receipt_candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        logger.info(f"🎯 Found {len(receipt_candidates)} receipt candidates")
        return receipt_candidates
    
    def _calculate_match_confidence(self, email: Dict, pattern: ReceiptPattern) -> float:
        """Calculate confidence that email matches a merchant pattern"""
        confidence = 0.0
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        from_email = email.get('from_email', '').lower()
        
        # Domain match (highest confidence)
        for domain in pattern.email_domains:
            if domain.lower() in from_email:
                confidence += 0.6
                break
        
        # Subject keyword match
        subject_matches = sum(1 for keyword in pattern.subject_keywords 
                            if keyword.lower() in subject)
        confidence += min(subject_matches * 0.2, 0.4)
        
        # Body keyword match
        body_matches = sum(1 for keyword in pattern.body_keywords 
                          if keyword.lower() in body)
        confidence += min(body_matches * 0.1, 0.3)
        
        # Amount pattern match
        amount = self._extract_amount_from_email(email)
        if amount and amount in pattern.common_amounts:
            confidence += 0.3
        
        # Receipt keywords
        receipt_keywords = ['receipt', 'invoice', 'payment', 'billing', 'confirmation']
        keyword_count = sum(1 for keyword in receipt_keywords 
                           if keyword in subject or keyword in body)
        confidence += min(keyword_count * 0.1, 0.2)
        
        return min(confidence, 1.0)
    
    def _extract_amount_from_email(self, email: Dict) -> Optional[float]:
        """Extract amount from email"""
        subject = email.get('subject', '')
        body = email.get('body', '')
        text = f"{subject} {body}"
        
        amount_patterns = [
            r'\$\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*usd',
            r'amount.*?\$\s*(\d+\.?\d*)',
            r'total.*?\$\s*(\d+\.?\d*)',
            r'charged.*?\$\s*(\d+\.?\d*)'
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount = float(match)
                    if amount > 0:
                        return amount
                except:
                    continue
        
        return None
    
    def build_merchant_profiles(self) -> Dict[str, Dict]:
        """Build comprehensive merchant profiles"""
        logger.info("🏗️ Building merchant profiles...")
        
        # Get transaction analysis
        transaction_analysis = self.analyze_transactions()
        
        profiles = {}
        
        # Build profiles for each merchant
        for merchant, analysis in transaction_analysis.items():
            profile = {
                'merchant': merchant,
                'transaction_count': analysis['transaction_count'],
                'common_amounts': analysis['common_amounts'],
                'billing_cycle': analysis['billing_cycle'],
                'confidence': analysis['confidence'],
                'email_domains': [],
                'subject_keywords': [],
                'body_keywords': [],
                'subscription_amounts': [],
                'one_off_amounts': []
            }
            
            # Add known pattern data if available
            if merchant in self.known_patterns:
                known = self.known_patterns[merchant]
                profile['email_domains'] = known.email_domains
                profile['subject_keywords'] = known.subject_keywords
                profile['body_keywords'] = known.body_keywords
            
            # Categorize amounts
            if analysis['billing_cycle'] == 'monthly':
                profile['subscription_amounts'] = analysis['common_amounts']
            elif analysis['billing_cycle'] == 'one-off':
                profile['one_off_amounts'] = analysis['common_amounts']
            else:
                # Mixed - need to determine based on frequency
                amount_counts = Counter([tx.get('amount', 0) for tx in 
                                       self.db.bank_transactions.find({'merchant': merchant})])
                for amount, count in amount_counts.most_common():
                    if count >= 2:
                        profile['subscription_amounts'].append(amount)
                    else:
                        profile['one_off_amounts'].append(amount)
            
            profiles[merchant] = profile
            
            logger.info(f"📋 Built profile for {merchant}: {analysis['transaction_count']} transactions")
        
        return profiles

def main():
    """Test the magic receipt finder"""
    from mongo_client import get_mongo_client
    
    # Initialize
    mongo_client = get_mongo_client()
    finder = MagicReceiptFinder(mongo_client)
    
    # Analyze transactions
    analysis = finder.analyze_transactions()
    print(f"Transaction analysis: {len(analysis)} merchants")
    
    # Build profiles
    profiles = finder.build_merchant_profiles()
    print(f"Built {len(profiles)} merchant profiles")
    
    # Show top merchants
    for merchant, profile in sorted(profiles.items(), 
                                  key=lambda x: x[1]['transaction_count'], 
                                  reverse=True)[:10]:
        print(f"{merchant}: {profile['transaction_count']} transactions, "
              f"cycle: {profile['billing_cycle']}, "
              f"amounts: {profile['common_amounts'][:3]}")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Receipt Intelligence Engine
A magical system that learns from real receipts and builds intelligent detection patterns
"""

import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import hashlib
from email.utils import parsedate_to_datetime
import pytz

logger = logging.getLogger(__name__)

@dataclass
class ReceiptPattern:
    """Learned receipt pattern for a merchant"""
    merchant: str
    email_domains: List[str]
    subject_patterns: List[str]
    body_patterns: List[str]
    amount_patterns: List[str]
    date_patterns: List[str]
    subscription_keywords: List[str]
    one_off_keywords: List[str]
    confidence: float
    sample_count: int
    last_updated: str
    examples: List[Dict]

@dataclass
class MerchantProfile:
    """Complete merchant profile with learned patterns"""
    merchant: str
    primary_domain: str
    email_domains: List[str]
    subscription_patterns: List[ReceiptPattern]
    one_off_patterns: List[ReceiptPattern]
    common_amounts: List[float]
    billing_cycles: List[str]  # monthly, yearly, etc.
    typical_amounts: Dict[str, List[float]]  # subscription vs one-off
    confidence: float
    total_receipts: int
    last_receipt_date: str

class ReceiptIntelligenceEngine:
    """Magic receipt learning and detection system"""
    
    def __init__(self, mongo_client):
        self.mongo_client = mongo_client
        self.db = mongo_client['expense']
        self.patterns_collection = self.db['receipt_patterns']
        self.profiles_collection = self.db['merchant_profiles']
        self.learning_collection = self.db['receipt_learning']
        
        # Initialize with known patterns
        self.known_patterns = self._initialize_known_patterns()
        
    def _initialize_known_patterns(self) -> Dict[str, MerchantProfile]:
        """Initialize with known merchant patterns"""
        patterns = {}
        
        # Anthropic/Claude patterns
        patterns['ANTHROPIC'] = MerchantProfile(
            merchant='ANTHROPIC',
            primary_domain='anthropic.com',
            email_domains=['anthropic.com', 'claude.ai', 'billing.anthropic.com'],
            subscription_patterns=[],
            one_off_patterns=[],
            common_amounts=[20.0, 25.0, 30.0, 50.0, 100.0],
            billing_cycles=['monthly'],
            typical_amounts={
                'subscription': [20.0, 25.0, 30.0],
                'one_off': [50.0, 100.0]
            },
            confidence=0.9,
            total_receipts=0,
            last_receipt_date=''
        )
        
        # Apple patterns
        patterns['APPLE'] = MerchantProfile(
            merchant='APPLE',
            primary_domain='apple.com',
            email_domains=['apple.com', 'itunes.com', 'icloud.com', 'appstore.com'],
            subscription_patterns=[],
            one_off_patterns=[],
            common_amounts=[0.99, 1.99, 2.99, 4.99, 9.99, 19.99, 29.99, 99.99],
            billing_cycles=['monthly', 'yearly'],
            typical_amounts={
                'subscription': [0.99, 1.99, 2.99, 4.99, 9.99, 19.99, 29.99],
                'one_off': [0.99, 1.99, 2.99, 4.99, 9.99, 19.99, 29.99, 99.99]
            },
            confidence=0.95,
            total_receipts=0,
            last_receipt_date=''
        )
        
        # GitHub patterns
        patterns['GITHUB'] = MerchantProfile(
            merchant='GITHUB',
            primary_domain='github.com',
            email_domains=['github.com', 'noreply.github.com'],
            subscription_patterns=[],
            one_off_patterns=[],
            common_amounts=[4.0, 7.0, 10.0, 20.0, 44.0],
            billing_cycles=['monthly', 'yearly'],
            typical_amounts={
                'subscription': [4.0, 7.0, 10.0, 20.0, 44.0],
                'one_off': [4.0, 7.0, 10.0, 20.0, 44.0]
            },
            confidence=0.9,
            total_receipts=0,
            last_receipt_date=''
        )
        
        return patterns
    
    def learn_from_transactions(self) -> Dict[str, Any]:
        """Learn receipt patterns from existing transactions"""
        logger.info("🧠 Starting receipt pattern learning from transactions...")
        
        # Get all transactions
        transactions = list(self.db.bank_transactions.find({}))
        logger.info(f"📊 Found {len(transactions)} transactions to analyze")
        
        # Group by merchant
        merchant_groups = defaultdict(list)
        for tx in transactions:
            merchant = tx.get('merchant', '').strip().upper()
            if merchant:
                merchant_groups[merchant].append(tx)
        
        # Analyze each merchant
        learned_patterns = {}
        for merchant, txs in merchant_groups.items():
            if len(txs) >= 2:  # Need at least 2 transactions to learn patterns
                pattern = self._analyze_merchant_patterns(merchant, txs)
                if pattern:
                    learned_patterns[merchant] = pattern
                    logger.info(f"✅ Learned patterns for {merchant}: {len(txs)} transactions")
        
        # Save learned patterns
        self._save_learned_patterns(learned_patterns)
        
        return {
            'merchants_analyzed': len(merchant_groups),
            'patterns_learned': len(learned_patterns),
            'total_transactions': len(transactions)
        }
    
    def _analyze_merchant_patterns(self, merchant: str, transactions: List[Dict]) -> Optional[MerchantProfile]:
        """Analyze patterns for a specific merchant"""
        try:
            # Extract common amounts
            amounts = [tx.get('amount', 0) for tx in transactions if tx.get('amount', 0) > 0]
            common_amounts = self._find_common_amounts(amounts)
            
            # Analyze billing cycles
            billing_cycles = self._analyze_billing_cycles(transactions)
            
            # Determine if subscription or one-off patterns
            subscription_amounts, one_off_amounts = self._categorize_amounts(amounts, transactions)
            
            # Build merchant profile
            profile = MerchantProfile(
                merchant=merchant,
                primary_domain=self._extract_primary_domain(transactions),
                email_domains=[],  # Will be populated from email analysis
                subscription_patterns=[],
                one_off_patterns=[],
                common_amounts=common_amounts,
                billing_cycles=billing_cycles,
                typical_amounts={
                    'subscription': subscription_amounts,
                    'one_off': one_off_amounts
                },
                confidence=min(len(transactions) / 10.0, 1.0),  # More transactions = higher confidence
                total_receipts=len(transactions),
                last_receipt_date=max([tx.get('date', '') for tx in transactions], default='')
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"Error analyzing patterns for {merchant}: {e}")
            return None
    
    def _find_common_amounts(self, amounts: List[float]) -> List[float]:
        """Find common amounts in transactions"""
        if not amounts:
            return []
        
        # Count occurrences
        amount_counts = Counter(amounts)
        
        # Return amounts that appear multiple times
        common = [amount for amount, count in amount_counts.most_common() 
                 if count >= 2 and amount > 0]
        
        return common[:10]  # Top 10 common amounts
    
    def _analyze_billing_cycles(self, transactions: List[Dict]) -> List[str]:
        """Analyze billing cycles from transaction dates"""
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
                return ['unknown']
            
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
                return ['monthly']
            elif avg_interval <= 370:  # Yearly
                return ['yearly']
            else:
                return ['unknown']
                
        except Exception as e:
            logger.error(f"Error analyzing billing cycles: {e}")
            return ['unknown']
    
    def _categorize_amounts(self, amounts: List[float], transactions: List[Dict]) -> Tuple[List[float], List[float]]:
        """Categorize amounts as subscription vs one-off"""
        if not amounts:
            return [], []
        
        # Simple heuristic: amounts that appear multiple times are likely subscriptions
        amount_counts = Counter(amounts)
        
        subscription_amounts = []
        one_off_amounts = []
        
        for amount, count in amount_counts.items():
            if count >= 2:  # Appears multiple times
                subscription_amounts.append(amount)
            else:
                one_off_amounts.append(amount)
        
        return subscription_amounts, one_off_amounts
    
    def _extract_primary_domain(self, transactions: List[Dict]) -> str:
        """Extract primary domain from transactions"""
        # This would be enhanced with email analysis
        return "unknown.com"
    
    def _save_learned_patterns(self, patterns: Dict[str, MerchantProfile]):
        """Save learned patterns to database"""
        try:
            for merchant, profile in patterns.items():
                # Convert to dict for storage
                profile_dict = asdict(profile)
                profile_dict['_id'] = merchant
                
                # Upsert the pattern
                self.profiles_collection.replace_one(
                    {'_id': merchant},
                    profile_dict,
                    upsert=True
                )
            
            logger.info(f"💾 Saved {len(patterns)} learned patterns to database")
            
        except Exception as e:
            logger.error(f"Error saving learned patterns: {e}")
    
    def find_receipt_emails(self, emails: List[Dict], target_merchants: List[str] = None) -> List[Dict]:
        """Find receipt emails using learned patterns"""
        logger.info(f"🔍 Finding receipt emails using learned patterns...")
        
        # Load merchant profiles
        profiles = self._load_merchant_profiles()
        
        receipt_candidates = []
        
        for email in emails:
            subject = email.get('subject', '').lower()
            body = email.get('body', '').lower()
            from_email = email.get('from_email', '').lower()
            
            # Check each merchant profile
            for merchant, profile in profiles.items():
                if target_merchants and merchant not in target_merchants:
                    continue
                
                # Check if email matches this merchant
                if self._email_matches_merchant(email, profile):
                    confidence = self._calculate_email_confidence(email, profile)
                    
                    if confidence > 0.3:  # Minimum confidence threshold
                        receipt_candidates.append({
                            'email': email,
                            'merchant': merchant,
                            'confidence': confidence,
                            'profile': profile
                        })
                        logger.info(f"✅ Found receipt for {merchant} (confidence: {confidence:.2f})")
        
        # Sort by confidence
        receipt_candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        logger.info(f"🎯 Found {len(receipt_candidates)} receipt candidates")
        return receipt_candidates
    
    def _email_matches_merchant(self, email: Dict, profile: MerchantProfile) -> bool:
        """Check if email matches a merchant profile"""
        from_email = email.get('from_email', '').lower()
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        
        # Check email domain
        for domain in profile.email_domains:
            if domain.lower() in from_email:
                return True
        
        # Check subject patterns
        for pattern in profile.subscription_patterns:
            if any(keyword in subject for keyword in pattern.subject_patterns):
                return True
        
        # Check body patterns
        for pattern in profile.subscription_patterns:
            if any(keyword in body for keyword in pattern.body_patterns):
                return True
        
        return False
    
    def _calculate_email_confidence(self, email: Dict, profile: MerchantProfile) -> float:
        """Calculate confidence that email is a receipt for this merchant"""
        confidence = 0.0
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        from_email = email.get('from_email', '').lower()
        
        # Domain match (highest confidence)
        for domain in profile.email_domains:
            if domain.lower() in from_email:
                confidence += 0.6
                break
        
        # Amount patterns
        amount_patterns = [
            r'\$\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*usd',
            r'amount.*?\$\s*(\d+\.?\d*)',
            r'total.*?\$\s*(\d+\.?\d*)'
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, body + ' ' + subject)
            for match in matches:
                try:
                    amount = float(match)
                    if amount in profile.common_amounts:
                        confidence += 0.3
                        break
                except:
                    continue
        
        # Receipt keywords
        receipt_keywords = ['receipt', 'invoice', 'payment', 'billing', 'confirmation']
        keyword_count = sum(1 for keyword in receipt_keywords 
                           if keyword in subject or keyword in body)
        confidence += min(keyword_count * 0.1, 0.2)
        
        return min(confidence, 1.0)
    
    def _load_merchant_profiles(self) -> Dict[str, MerchantProfile]:
        """Load merchant profiles from database"""
        profiles = {}
        
        try:
            # Load from database
            db_profiles = self.profiles_collection.find({})
            for doc in db_profiles:
                merchant = doc['merchant']
                profiles[merchant] = MerchantProfile(**doc)
            
            # Add known patterns
            for merchant, profile in self.known_patterns.items():
                if merchant not in profiles:
                    profiles[merchant] = profile
            
            logger.info(f"📚 Loaded {len(profiles)} merchant profiles")
            
        except Exception as e:
            logger.error(f"Error loading merchant profiles: {e}")
            # Fall back to known patterns
            profiles = self.known_patterns.copy()
        
        return profiles
    
    def enhance_with_email_analysis(self, emails: List[Dict], transactions: List[Dict]) -> Dict[str, Any]:
        """Enhance patterns by analyzing actual receipt emails"""
        logger.info("📧 Enhancing patterns with email analysis...")
        
        # Find emails that match transactions
        matches = self._find_email_transaction_matches(emails, transactions)
        
        # Learn from successful matches
        enhanced_patterns = {}
        for match in matches:
            email = match['email']
            transaction = match['transaction']
            merchant = transaction.get('merchant', '').upper()
            
            if merchant not in enhanced_patterns:
                enhanced_patterns[merchant] = {
                    'emails': [],
                    'transactions': [],
                    'patterns': {}
                }
            
            enhanced_patterns[merchant]['emails'].append(email)
            enhanced_patterns[merchant]['transactions'].append(transaction)
        
        # Extract patterns from each merchant
        for merchant, data in enhanced_patterns.items():
            patterns = self._extract_email_patterns(data['emails'], data['transactions'])
            enhanced_patterns[merchant]['patterns'] = patterns
            
            logger.info(f"🔍 Enhanced {merchant}: {len(data['emails'])} emails, {len(patterns)} patterns")
        
        return enhanced_patterns
    
    def _find_email_transaction_matches(self, emails: List[Dict], transactions: List[Dict]) -> List[Dict]:
        """Find emails that match transactions based on amount and date"""
        matches = []
        
        for email in emails:
            # Extract amount from email
            email_amount = self._extract_amount_from_email(email)
            email_date = self._extract_date_from_email(email)
            
            if not email_amount or not email_date:
                continue
            
            # Find matching transactions
            for transaction in transactions:
                tx_amount = transaction.get('amount', 0)
                tx_date = transaction.get('date', '')
                
                # Amount match (within $0.01 tolerance)
                if abs(email_amount - tx_amount) < 0.01:
                    # Date match (within 3 days)
                    if self._dates_close(email_date, tx_date, 3):
                        matches.append({
                            'email': email,
                            'transaction': transaction,
                            'amount_match': email_amount,
                            'date_match': email_date
                        })
                        break
        
        logger.info(f"🔗 Found {len(matches)} email-transaction matches")
        return matches
    
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
    
    def _extract_date_from_email(self, email: Dict) -> Optional[str]:
        """Extract date from email"""
        # Try email date first
        email_date = email.get('date', '')
        if email_date:
            try:
                # Parse email date
                parsed_date = parsedate_to_datetime(email_date)
                return parsed_date.strftime('%Y-%m-%d')
            except:
                pass
        
        # Try to extract from subject/body
        subject = email.get('subject', '')
        body = email.get('body', '')
        text = f"{subject} {body}"
        
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
            r'(\d{2}-\d{2}-\d{4})'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        return None
    
    def _dates_close(self, date1: str, date2: str, days_threshold: int = 3) -> bool:
        """Check if two dates are close to each other"""
        try:
            d1 = datetime.strptime(date1, '%Y-%m-%d')
            d2 = datetime.strptime(date2, '%Y-%m-%d')
            diff = abs((d1 - d2).days)
            return diff <= days_threshold
        except:
            return False
    
    def _extract_email_patterns(self, emails: List[Dict], transactions: List[Dict]) -> Dict[str, Any]:
        """Extract patterns from email-transaction matches"""
        patterns = {
            'subject_patterns': [],
            'body_patterns': [],
            'amount_patterns': [],
            'email_domains': [],
            'common_amounts': []
        }
        
        # Extract email domains
        domains = set()
        for email in emails:
            from_email = email.get('from_email', '')
            if '@' in from_email:
                domain = from_email.split('@')[-1].lower()
                domains.add(domain)
        patterns['email_domains'] = list(domains)
        
        # Extract common amounts
        amounts = [tx.get('amount', 0) for tx in transactions if tx.get('amount', 0) > 0]
        patterns['common_amounts'] = self._find_common_amounts(amounts)
        
        # Extract subject patterns
        subjects = [email.get('subject', '') for email in emails]
        patterns['subject_patterns'] = self._extract_text_patterns(subjects)
        
        # Extract body patterns
        bodies = [email.get('body', '') for email in emails]
        patterns['body_patterns'] = self._extract_text_patterns(bodies)
        
        return patterns
    
    def _extract_text_patterns(self, texts: List[str]) -> List[str]:
        """Extract common patterns from text"""
        # Simple keyword extraction
        all_words = []
        for text in texts:
            words = re.findall(r'\b\w+\b', text.lower())
            all_words.extend(words)
        
        # Find common words
        word_counts = Counter(all_words)
        common_words = [word for word, count in word_counts.most_common(20) 
                       if count >= 2 and len(word) > 3]
        
        return common_words

def main():
    """Test the receipt intelligence engine"""
    from mongo_client import get_mongo_client
    
    # Initialize
    mongo_client = get_mongo_client()
    engine = ReceiptIntelligenceEngine(mongo_client)
    
    # Learn from transactions
    results = engine.learn_from_transactions()
    print(f"Learning results: {results}")
    
    # Test with some sample emails
    sample_emails = [
        {
            'subject': 'Your Anthropic Claude subscription - $20.00',
            'body': 'Thank you for your Claude.AI subscription. Amount charged: $20.00',
            'from_email': 'billing@anthropic.com',
            'date': '2025-06-28'
        }
    ]
    
    # Find receipt emails
    receipts = engine.find_receipt_emails(sample_emails)
    print(f"Found {len(receipts)} receipt candidates")

if __name__ == "__main__":
    main() 
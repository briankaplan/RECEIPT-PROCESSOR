#!/usr/bin/env python3
"""
Magic Receipt System
Comprehensive system that learns from transactions and emails to find receipts
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import json

logger = logging.getLogger(__name__)

class MagicReceiptSystem:
    """Magic receipt finding and learning system"""
    
    def __init__(self, mongo_client):
        self.mongo_client = mongo_client
        self.db = mongo_client['expense']
        
        # Initialize components
        self.merchant_profiles = {}
        self.receipt_patterns = {}
        self.learned_matches = []
        
        # Load existing data
        self._load_existing_data()
    
    def _load_existing_data(self):
        """Load existing merchant profiles and patterns"""
        try:
            # Load merchant profiles
            profiles = self.db.merchant_profiles.find({})
            for profile in profiles:
                self.merchant_profiles[profile['merchant']] = profile
            
            # Load receipt patterns
            patterns = self.db.receipt_patterns.find({})
            for pattern in patterns:
                self.receipt_patterns[pattern['merchant']] = pattern
            
            logger.info(f"📚 Loaded {len(self.merchant_profiles)} merchant profiles and {len(self.receipt_patterns)} patterns")
            
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    def learn_from_transactions(self) -> Dict[str, Any]:
        """Learn patterns from existing transactions"""
        logger.info("🧠 Learning from transactions...")
        
        # Get all transactions
        transactions = list(self.db.bank_transactions.find({}))
        logger.info(f"📊 Found {len(transactions)} transactions")
        
        # Analyze by merchant
        merchant_analysis = self._analyze_transactions_by_merchant(transactions)
        
        # Build merchant profiles
        for merchant, analysis in merchant_analysis.items():
            profile = self._build_merchant_profile(merchant, analysis)
            if profile:
                self.merchant_profiles[merchant] = profile
                self.db.merchant_profiles.replace_one(
                    {'merchant': merchant},
                    profile,
                    upsert=True
                )
        
        return {
            'merchants_analyzed': len(merchant_analysis),
            'profiles_built': len(self.merchant_profiles),
            'total_transactions': len(transactions)
        }
    
    def _analyze_transactions_by_merchant(self, transactions: List[Dict]) -> Dict[str, Dict]:
        """Analyze transactions grouped by merchant"""
        merchant_groups = defaultdict(list)
        
        for tx in transactions:
            merchant = tx.get('merchant', '').strip().upper()
            if merchant:
                merchant_groups[merchant].append(tx)
        
        analysis = {}
        for merchant, txs in merchant_groups.items():
            if len(txs) >= 2:  # Need at least 2 transactions
                analysis[merchant] = {
                    'transactions': txs,
                    'count': len(txs),
                    'amounts': [tx.get('amount', 0) for tx in txs if tx.get('amount', 0) > 0],
                    'dates': [tx.get('date', '') for tx in txs if tx.get('date', '')],
                    'billing_cycle': self._determine_billing_cycle(txs)
                }
        
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
            
            dates.sort()
            intervals = []
            for i in range(1, len(dates)):
                interval = (dates[i] - dates[i-1]).days
                intervals.append(interval)
            
            avg_interval = sum(intervals) / len(intervals)
            
            if avg_interval <= 35:
                return 'monthly'
            elif avg_interval <= 370:
                return 'yearly'
            else:
                return 'one_off'
                
        except Exception as e:
            logger.error(f"Error determining billing cycle: {e}")
            return 'unknown'
    
    def _build_merchant_profile(self, merchant: str, analysis: Dict) -> Optional[Dict]:
        """Build merchant profile from analysis"""
        try:
            amounts = analysis['amounts']
            if not amounts:
                return None
            
            # Find common amounts
            amount_counts = Counter(amounts)
            common_amounts = [amount for amount, count in amount_counts.most_common(10) 
                            if count >= 2]
            
            # Categorize amounts
            subscription_amounts = []
            one_off_amounts = []
            
            if analysis['billing_cycle'] == 'monthly':
                subscription_amounts = common_amounts
            elif analysis['billing_cycle'] == 'one_off':
                one_off_amounts = common_amounts
            else:
                # Mixed - categorize by frequency
                for amount, count in amount_counts.most_common():
                    if count >= 2:
                        subscription_amounts.append(amount)
                    else:
                        one_off_amounts.append(amount)
            
            profile = {
                'merchant': merchant,
                'transaction_count': analysis['count'],
                'common_amounts': common_amounts,
                'subscription_amounts': subscription_amounts,
                'one_off_amounts': one_off_amounts,
                'billing_cycle': analysis['billing_cycle'],
                'email_domains': [],
                'subject_keywords': [],
                'body_keywords': [],
                'confidence': min(analysis['count'] / 10.0, 1.0),
                'last_updated': datetime.now().isoformat()
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Error building profile for {merchant}: {e}")
            return None
    
    def find_receipt_emails(self, emails: List[Dict], target_merchants: List[str] = None) -> List[Dict]:
        """Find receipt emails using learned patterns"""
        logger.info(f"🔍 Finding receipt emails from {len(emails)} emails...")
        
        receipt_candidates = []
        
        for email in emails:
            # Extract basic info
            subject = email.get('subject', '').lower()
            body = email.get('body', '').lower()
            from_email = email.get('from_email', '').lower()
            
            # Check each merchant profile
            for merchant, profile in self.merchant_profiles.items():
                if target_merchants and merchant not in target_merchants:
                    continue
                
                # Check if email matches this merchant
                confidence = self._calculate_email_confidence(email, profile)
                
                if confidence > 0.3:  # Minimum threshold
                    receipt_candidates.append({
                        'email': email,
                        'merchant': merchant,
                        'confidence': confidence,
                        'profile': profile,
                        'extracted_amount': self._extract_amount_from_email(email),
                        'receipt_type': self._determine_receipt_type(email, profile)
                    })
        
        # Sort by confidence
        receipt_candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        logger.info(f"🎯 Found {len(receipt_candidates)} receipt candidates")
        return receipt_candidates
    
    def _calculate_email_confidence(self, email: Dict, profile: Dict) -> float:
        """Calculate confidence that email matches a merchant profile"""
        confidence = 0.0
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        from_email = email.get('from_email', '').lower()
        
        # Domain match
        for domain in profile.get('email_domains', []):
            if domain.lower() in from_email:
                confidence += 0.6
                break
        
        # Amount match
        amount = self._extract_amount_from_email(email)
        if amount and amount in profile.get('common_amounts', []):
            confidence += 0.3
        
        # Receipt keywords
        receipt_keywords = ['receipt', 'invoice', 'payment', 'billing', 'confirmation']
        keyword_count = sum(1 for keyword in receipt_keywords 
                           if keyword in subject or keyword in body)
        confidence += min(keyword_count * 0.1, 0.2)
        
        # Merchant-specific keywords
        merchant_keywords = profile.get('subject_keywords', []) + profile.get('body_keywords', [])
        keyword_matches = sum(1 for keyword in merchant_keywords 
                            if keyword.lower() in subject or keyword.lower() in body)
        confidence += min(keyword_matches * 0.1, 0.3)
        
        return min(confidence, 1.0)
    
    def _extract_amount_from_email(self, email: Dict) -> Optional[float]:
        """Extract amount from email"""
        subject = email.get('subject', '')
        body = email.get('body', '')
        text = f"{subject} {body}"
        
        amount_patterns = [
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*USD',
            r'total.*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'amount.*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'charged.*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        ]
        
        for pattern in amount_patterns:
            import re
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount_str = match.replace(',', '')
                    amount = float(amount_str)
                    if amount > 0:
                        return amount
                except:
                    continue
        
        return None
    
    def _determine_receipt_type(self, email: Dict, profile: Dict) -> str:
        """Determine if receipt is subscription or one-off"""
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        
        subscription_keywords = ['subscription', 'renewal', 'monthly', 'yearly', 'billing']
        subscription_matches = sum(1 for keyword in subscription_keywords 
                                 if keyword in subject or keyword in body)
        
        if subscription_matches >= 2:
            return 'subscription'
        elif subscription_matches >= 1:
            return 'likely_subscription'
        else:
            return 'one_off'
    
    def match_receipts_to_transactions(self, receipt_candidates: List[Dict]) -> List[Dict]:
        """Match receipt candidates to transactions"""
        logger.info(f"🔗 Matching {len(receipt_candidates)} receipts to transactions...")
        
        # Get all transactions
        transactions = list(self.db.bank_transactions.find({}))
        logger.info(f"📊 Found {len(transactions)} transactions for matching")
        
        matches = []
        
        for candidate in receipt_candidates:
            email = candidate['email']
            merchant = candidate['merchant']
            amount = candidate['extracted_amount']
            
            if not amount:
                continue
            
            # Find matching transactions
            matching_transactions = []
            
            for transaction in transactions:
                tx_merchant = transaction.get('merchant', '').strip().upper()
                tx_amount = transaction.get('amount', 0)
                tx_date = transaction.get('date', '')
                
                # Merchant match
                if merchant == tx_merchant:
                    # Amount match (within $0.01 tolerance)
                    if abs(amount - tx_amount) < 0.01:
                        # Date match (within 7 days)
                        if self._dates_close(email.get('date', ''), tx_date, 7):
                            matching_transactions.append(transaction)
            
            if matching_transactions:
                # Use the closest date match
                best_match = min(matching_transactions, 
                               key=lambda tx: abs(self._date_diff(email.get('date', ''), tx.get('date', ''))))
                
                matches.append({
                    'receipt_candidate': candidate,
                    'transaction': best_match,
                    'match_confidence': candidate['confidence'],
                    'match_type': 'amount_date_merchant'
                })
                
                logger.info(f"✅ Matched {merchant} - ${amount} to transaction")
        
        logger.info(f"🎯 Found {len(matches)} receipt-transaction matches")
        return matches
    
    def _dates_close(self, date1: str, date2: str, days_threshold: int = 7) -> bool:
        """Check if two dates are close to each other"""
        try:
            d1 = datetime.strptime(date1, '%Y-%m-%d')
            d2 = datetime.strptime(date2, '%Y-%m-%d')
            diff = abs((d1 - d2).days)
            return diff <= days_threshold
        except:
            return False
    
    def _date_diff(self, date1: str, date2: str) -> int:
        """Calculate difference between two dates in days"""
        try:
            d1 = datetime.strptime(date1, '%Y-%m-%d')
            d2 = datetime.strptime(date2, '%Y-%m-%d')
            return abs((d1 - d2).days)
        except:
            return 999
    
    def enhance_patterns_from_matches(self, matches: List[Dict]) -> Dict[str, Any]:
        """Enhance patterns based on successful matches"""
        logger.info(f"🚀 Enhancing patterns from {len(matches)} successful matches...")
        
        enhanced_patterns = {}
        
        for match in matches:
            receipt = match['receipt_candidate']
            transaction = match['transaction']
            merchant = receipt['merchant']
            
            if merchant not in enhanced_patterns:
                enhanced_patterns[merchant] = {
                    'emails': [],
                    'transactions': [],
                    'new_patterns': {}
                }
            
            enhanced_patterns[merchant]['emails'].append(receipt['email'])
            enhanced_patterns[merchant]['transactions'].append(transaction)
        
        # Extract new patterns
        for merchant, data in enhanced_patterns.items():
            new_patterns = self._extract_patterns_from_matches(data['emails'], data['transactions'])
            enhanced_patterns[merchant]['new_patterns'] = new_patterns
            
            # Update merchant profile
            if merchant in self.merchant_profiles:
                profile = self.merchant_profiles[merchant]
                profile['email_domains'].extend(new_patterns.get('email_domains', []))
                profile['subject_keywords'].extend(new_patterns.get('subject_keywords', []))
                profile['body_keywords'].extend(new_patterns.get('body_keywords', []))
                
                # Remove duplicates
                profile['email_domains'] = list(set(profile['email_domains']))
                profile['subject_keywords'] = list(set(profile['subject_keywords']))
                profile['body_keywords'] = list(set(profile['body_keywords']))
                
                # Update confidence
                profile['confidence'] = min(profile['confidence'] + 0.1, 1.0)
                profile['last_updated'] = datetime.now().isoformat()
                
                # Save to database
                self.db.merchant_profiles.replace_one(
                    {'merchant': merchant},
                    profile,
                    upsert=True
                )
        
        return enhanced_patterns
    
    def _extract_patterns_from_matches(self, emails: List[Dict], transactions: List[Dict]) -> Dict[str, List[str]]:
        """Extract patterns from successful email-transaction matches"""
        patterns = {
            'email_domains': [],
            'subject_keywords': [],
            'body_keywords': []
        }
        
        # Extract email domains
        domains = set()
        for email in emails:
            from_email = email.get('from_email', '')
            if '@' in from_email:
                domain = from_email.split('@')[-1].lower()
                domains.add(domain)
        patterns['email_domains'] = list(domains)
        
        # Extract keywords (simplified - would need more sophisticated NLP for better results)
        all_subject_words = []
        all_body_words = []
        
        for email in emails:
            subject = email.get('subject', '').lower()
            body = email.get('body', '').lower()
            
            # Simple word extraction
            import re
            subject_words = re.findall(r'\b\w+\b', subject)
            body_words = re.findall(r'\b\w+\b', body)
            
            all_subject_words.extend(subject_words)
            all_body_words.extend(body_words)
        
        # Find common words
        subject_counts = Counter(all_subject_words)
        body_counts = Counter(all_body_words)
        
        patterns['subject_keywords'] = [word for word, count in subject_counts.most_common(10) 
                                      if count >= 2 and len(word) > 3]
        patterns['body_keywords'] = [word for word, count in body_counts.most_common(10) 
                                   if count >= 2 and len(word) > 3]
        
        return patterns
    
    def get_merchant_summary(self) -> Dict[str, Any]:
        """Get summary of all merchant profiles"""
        summary = {
            'total_merchants': len(self.merchant_profiles),
            'merchants': []
        }
        
        for merchant, profile in self.merchant_profiles.items():
            summary['merchants'].append({
                'merchant': merchant,
                'transaction_count': profile.get('transaction_count', 0),
                'billing_cycle': profile.get('billing_cycle', 'unknown'),
                'confidence': profile.get('confidence', 0.0),
                'common_amounts': profile.get('common_amounts', [])[:5],  # Top 5
                'subscription_amounts': profile.get('subscription_amounts', [])[:3],
                'one_off_amounts': profile.get('one_off_amounts', [])[:3]
            })
        
        # Sort by transaction count
        summary['merchants'].sort(key=lambda x: x['transaction_count'], reverse=True)
        
        return summary

def main():
    """Test the magic receipt system"""
    from mongo_client import get_mongo_client
    
    # Initialize
    mongo_client = get_mongo_client()
    system = MagicReceiptSystem(mongo_client)
    
    # Learn from transactions
    results = system.learn_from_transactions()
    print(f"Learning results: {results}")
    
    # Get merchant summary
    summary = system.get_merchant_summary()
    print(f"Merchant summary: {summary['total_merchants']} merchants")
    
    # Show top merchants
    for merchant in summary['merchants'][:10]:
        print(f"{merchant['merchant']}: {merchant['transaction_count']} transactions, "
              f"cycle: {merchant['billing_cycle']}, "
              f"confidence: {merchant['confidence']:.2f}")

if __name__ == "__main__":
    main() 
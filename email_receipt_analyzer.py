#!/usr/bin/env python3
"""
Email Receipt Analyzer
Scans emails to find real receipts and build intelligent detection patterns
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class EmailReceipt:
    """Identified receipt email"""
    email_id: str
    merchant: str
    amount: float
    date: str
    subject: str
    from_email: str
    confidence: float
    receipt_type: str  # subscription, one-off, unknown
    keywords: List[str]

@dataclass
class MerchantPattern:
    """Learned pattern for a merchant"""
    merchant: str
    email_domains: List[str]
    subject_keywords: List[str]
    body_keywords: List[str]
    common_amounts: List[float]
    receipt_keywords: List[str]
    subscription_amounts: List[float]
    one_off_amounts: List[float]
    confidence: float
    sample_count: int

class EmailReceiptAnalyzer:
    """Analyzes emails to find receipts and build patterns"""
    
    def __init__(self, mongo_client):
        self.mongo_client = mongo_client
        self.db = mongo_client['expense']
        
        # Receipt keywords
        self.receipt_keywords = [
            'receipt', 'invoice', 'payment', 'billing', 'confirmation',
            'order', 'purchase', 'transaction', 'charged', 'total',
            'amount', 'subscription', 'renewal', 'billed'
        ]
        
        # Amount patterns
        self.amount_patterns = [
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*USD',  # 1,234.56 USD
            r'USD\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # USD 1,234.56
            r'total.*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # total $1,234.56
            r'amount.*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # amount $1,234.56
            r'charged.*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # charged $1,234.56
            r'payment.*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # payment $1,234.56
        ]
        
        # Known merchant patterns
        self.known_merchants = self._build_known_merchants()
    
    def _build_known_merchants(self) -> Dict[str, Dict]:
        """Build known merchant patterns"""
        return {
            'ANTHROPIC': {
                'domains': ['anthropic.com', 'claude.ai', 'billing.anthropic.com'],
                'keywords': ['claude', 'anthropic', 'subscription'],
                'amounts': [20.0, 25.0, 30.0, 50.0, 100.0]
            },
            'APPLE': {
                'domains': ['apple.com', 'itunes.com', 'icloud.com', 'appstore.com'],
                'keywords': ['apple', 'itunes', 'icloud', 'app store'],
                'amounts': [0.99, 1.99, 2.99, 4.99, 9.99, 19.99, 29.99, 99.99]
            },
            'GITHUB': {
                'domains': ['github.com', 'noreply.github.com'],
                'keywords': ['github', 'subscription'],
                'amounts': [4.0, 7.0, 10.0, 20.0, 44.0]
            },
            'MICROSOFT': {
                'domains': ['microsoft.com', 'billing.microsoft.com'],
                'keywords': ['microsoft', 'office', '365'],
                'amounts': [99.99, 149.99, 199.99, 299.99]
            },
            'GOOGLE': {
                'domains': ['google.com', 'billing.google.com', 'noreply-payments@google.com'],
                'keywords': ['google', 'workspace', 'billing'],
                'amounts': [244.87, 299.99, 599.99]
            }
        }
    
    def scan_emails_for_receipts(self, emails: List[Dict]) -> List[EmailReceipt]:
        """Scan emails to find receipts"""
        logger.info(f"🔍 Scanning {len(emails)} emails for receipts...")
        
        receipts = []
        
        for email in emails:
            receipt = self._analyze_email_for_receipt(email)
            if receipt:
                receipts.append(receipt)
                logger.info(f"✅ Found receipt: {receipt.merchant} - ${receipt.amount}")
        
        logger.info(f"🎯 Found {len(receipts)} receipts in emails")
        return receipts
    
    def _analyze_email_for_receipt(self, email: Dict) -> Optional[EmailReceipt]:
        """Analyze a single email for receipt content"""
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        from_email = email.get('from_email', '').lower()
        
        # Extract amount
        amount = self._extract_amount_from_email(email)
        if not amount or amount <= 0:
            return None
        
        # Check for receipt keywords
        receipt_keywords = self._find_receipt_keywords(subject, body)
        if not receipt_keywords:
            return None
        
        # Identify merchant
        merchant = self._identify_merchant(email)
        if not merchant:
            return None
        
        # Determine receipt type
        receipt_type = self._determine_receipt_type(email, amount, merchant)
        
        # Calculate confidence
        confidence = self._calculate_receipt_confidence(email, merchant, amount, receipt_keywords)
        
        if confidence > 0.3:  # Minimum confidence threshold
            return EmailReceipt(
                email_id=email.get('id', ''),
                merchant=merchant,
                amount=amount,
                date=email.get('date', ''),
                subject=email.get('subject', ''),
                from_email=from_email,
                confidence=confidence,
                receipt_type=receipt_type,
                keywords=receipt_keywords
            )
        
        return None
    
    def _extract_amount_from_email(self, email: Dict) -> Optional[float]:
        """Extract amount from email"""
        subject = email.get('subject', '')
        body = email.get('body', '')
        text = f"{subject} {body}"
        
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Remove commas and convert to float
                    amount_str = match.replace(',', '')
                    amount = float(amount_str)
                    if amount > 0:
                        return amount
                except:
                    continue
        
        return None
    
    def _find_receipt_keywords(self, subject: str, body: str) -> List[str]:
        """Find receipt keywords in email"""
        text = f"{subject} {body}"
        found_keywords = []
        
        for keyword in self.receipt_keywords:
            if keyword.lower() in text:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def _identify_merchant(self, email: Dict) -> Optional[str]:
        """Identify merchant from email"""
        from_email = email.get('from_email', '').lower()
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        
        # Check known merchants first
        for merchant, pattern in self.known_merchants.items():
            # Check domain
            for domain in pattern['domains']:
                if domain.lower() in from_email:
                    return merchant
            
            # Check keywords
            keyword_matches = sum(1 for keyword in pattern['keywords'] 
                                if keyword.lower() in subject or keyword.lower() in body)
            if keyword_matches >= 2:
                return merchant
        
        # Try to extract from domain
        if '@' in from_email:
            domain = from_email.split('@')[-1].lower()
            # Map common domains
            domain_mappings = {
                'anthropic.com': 'ANTHROPIC',
                'claude.ai': 'ANTHROPIC',
                'apple.com': 'APPLE',
                'itunes.com': 'APPLE',
                'github.com': 'GITHUB',
                'microsoft.com': 'MICROSOFT',
                'google.com': 'GOOGLE'
            }
            
            for domain_key, merchant in domain_mappings.items():
                if domain_key in domain or domain in domain_key:
                    return merchant
        
        return None
    
    def _determine_receipt_type(self, email: Dict, amount: float, merchant: str) -> str:
        """Determine if receipt is subscription or one-off"""
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        
        # Check for subscription keywords
        subscription_keywords = ['subscription', 'renewal', 'monthly', 'yearly', 'billing']
        subscription_matches = sum(1 for keyword in subscription_keywords 
                                 if keyword in subject or keyword in body)
        
        if subscription_matches >= 2:
            return 'subscription'
        elif subscription_matches >= 1:
            return 'likely_subscription'
        else:
            return 'one_off'
    
    def _calculate_receipt_confidence(self, email: Dict, merchant: str, amount: float, keywords: List[str]) -> float:
        """Calculate confidence that email is a receipt"""
        confidence = 0.0
        
        # Base confidence from keywords
        confidence += len(keywords) * 0.1
        
        # Amount validation
        if merchant in self.known_merchants:
            known_amounts = self.known_merchants[merchant]['amounts']
            if amount in known_amounts:
                confidence += 0.3
        
        # Domain match
        from_email = email.get('from_email', '').lower()
        if merchant in self.known_merchants:
            for domain in self.known_merchants[merchant]['domains']:
                if domain.lower() in from_email:
                    confidence += 0.4
                    break
        
        # Receipt-specific keywords
        strong_receipt_words = ['receipt', 'invoice', 'payment confirmation']
        strong_matches = sum(1 for word in strong_receipt_words 
                           if word in email.get('subject', '').lower() or 
                              word in email.get('body', '').lower())
        confidence += strong_matches * 0.2
        
        return min(confidence, 1.0)
    
    def build_merchant_patterns(self, receipts: List[EmailReceipt]) -> Dict[str, MerchantPattern]:
        """Build patterns from found receipts"""
        logger.info(f"🏗️ Building patterns from {len(receipts)} receipts...")
        
        # Group receipts by merchant
        merchant_groups = defaultdict(list)
        for receipt in receipts:
            merchant_groups[receipt.merchant].append(receipt)
        
        patterns = {}
        
        for merchant, merchant_receipts in merchant_groups.items():
            pattern = self._build_merchant_pattern(merchant, merchant_receipts)
            if pattern:
                patterns[merchant] = pattern
                logger.info(f"📋 Built pattern for {merchant}: {len(merchant_receipts)} receipts")
        
        return patterns
    
    def _build_merchant_pattern(self, merchant: str, receipts: List[EmailReceipt]) -> Optional[MerchantPattern]:
        """Build pattern for a specific merchant"""
        if len(receipts) < 2:
            return None
        
        # Extract common elements
        email_domains = set()
        subject_keywords = []
        body_keywords = []
        amounts = []
        receipt_keywords = []
        subscription_amounts = []
        one_off_amounts = []
        
        for receipt in receipts:
            # Email domains
            if '@' in receipt.from_email:
                domain = receipt.from_email.split('@')[-1].lower()
                email_domains.add(domain)
            
            # Keywords
            receipt_keywords.extend(receipt.keywords)
            
            # Amounts
            amounts.append(receipt.amount)
            if receipt.receipt_type in ['subscription', 'likely_subscription']:
                subscription_amounts.append(receipt.amount)
            else:
                one_off_amounts.append(receipt.amount)
        
        # Find common keywords (would need full email content for better analysis)
        # For now, use known patterns
        if merchant in self.known_merchants:
            subject_keywords = self.known_merchants[merchant]['keywords']
            body_keywords = self.known_merchants[merchant]['keywords']
        
        # Find common amounts
        amount_counts = Counter(amounts)
        common_amounts = [amount for amount, count in amount_counts.most_common(10) 
                         if count >= 2]
        
        # Calculate confidence
        confidence = min(len(receipts) / 10.0, 1.0)
        
        return MerchantPattern(
            merchant=merchant,
            email_domains=list(email_domains),
            subject_keywords=subject_keywords,
            body_keywords=body_keywords,
            common_amounts=common_amounts,
            receipt_keywords=list(set(receipt_keywords)),
            subscription_amounts=list(set(subscription_amounts)),
            one_off_amounts=list(set(one_off_amounts)),
            confidence=confidence,
            sample_count=len(receipts)
        )
    
    def match_receipts_to_transactions(self, receipts: List[EmailReceipt], transactions: List[Dict]) -> List[Dict]:
        """Match receipts to transactions"""
        logger.info(f"🔗 Matching {len(receipts)} receipts to {len(transactions)} transactions...")
        
        matches = []
        
        for receipt in receipts:
            # Find matching transactions
            matching_transactions = []
            
            for transaction in transactions:
                tx_merchant = transaction.get('merchant', '').strip().upper()
                tx_amount = transaction.get('amount', 0)
                tx_date = transaction.get('date', '')
                
                # Merchant match
                if receipt.merchant == tx_merchant:
                    # Amount match (within $0.01 tolerance)
                    if abs(receipt.amount - tx_amount) < 0.01:
                        # Date match (within 7 days)
                        if self._dates_close(receipt.date, tx_date, 7):
                            matching_transactions.append(transaction)
            
            if matching_transactions:
                # Use the closest date match
                best_match = min(matching_transactions, 
                               key=lambda tx: abs(self._date_diff(receipt.date, tx.get('date', ''))))
                
                matches.append({
                    'receipt': receipt,
                    'transaction': best_match,
                    'confidence': receipt.confidence,
                    'match_type': 'amount_date_merchant'
                })
                
                logger.info(f"✅ Matched {receipt.merchant} - ${receipt.amount} to transaction")
        
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
            return 999  # Large number for invalid dates

def main():
    """Test the email receipt analyzer"""
    from mongo_client import get_mongo_client
    
    # Initialize
    mongo_client = get_mongo_client()
    analyzer = EmailReceiptAnalyzer(mongo_client)
    
    # Get sample emails (you would get these from your email search)
    sample_emails = [
        {
            'id': 'test1',
            'subject': 'Your Claude.AI subscription - $20.00',
            'body': 'Thank you for your Claude.AI subscription. Amount charged: $20.00',
            'from_email': 'billing@anthropic.com',
            'date': '2025-06-28'
        },
        {
            'id': 'test2',
            'subject': 'Apple App Store Purchase - $2.99',
            'body': 'Your purchase from the App Store. Total: $2.99',
            'from_email': 'noreply@apple.com',
            'date': '2025-06-28'
        }
    ]
    
    # Scan for receipts
    receipts = analyzer.scan_emails_for_receipts(sample_emails)
    print(f"Found {len(receipts)} receipts")
    
    # Build patterns
    patterns = analyzer.build_merchant_patterns(receipts)
    print(f"Built {len(patterns)} patterns")

if __name__ == "__main__":
    main() 
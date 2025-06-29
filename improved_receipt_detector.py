
#!/usr/bin/env python3
"""
Improved Receipt Detector
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ImprovedReceiptDetector:
    """Improved receipt detection with better accuracy"""
    
    def __init__(self):
        self.receipt_keywords = [
            'receipt', 'payment', 'invoice', 'confirmation', 'order',
            'billing', 'statement', 'transaction', 'purchase'
        ]
        
        self.amount_indicators = [
            'total', 'amount', 'charged', 'payment of', 'cost',
            'price', 'fee', 'subscription', 'renewal'
        ]
    
    def is_receipt_email(self, email_data: Dict) -> Dict:
        """Determine if email contains a receipt"""
        
        confidence = 0.0
        reasons = []
        
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        sender = email_data.get('from', '').lower()
        
        # Check for receipt keywords in subject
        keyword_matches = [kw for kw in self.receipt_keywords if kw in subject]
        if keyword_matches:
            confidence += 0.3
            reasons.append(f"Receipt keywords in subject: {', '.join(keyword_matches)}")
        
        # Check for amount indicators
        amount_matches = [ind for ind in self.amount_indicators if ind in subject or ind in body]
        if amount_matches:
            confidence += 0.2
            reasons.append(f"Amount indicators: {', '.join(amount_matches)}")
        
        # Check for dollar amounts
        if re.search(r'\$\s*\d+\.?\d*', subject + ' ' + body):
            confidence += 0.2
            reasons.append("Dollar amount found")
        
        # Check sender domain
        if self._is_receipt_sender(sender):
            confidence += 0.2
            reasons.append("Known receipt sender")
        
        # Check for attachments
        if email_data.get('has_attachments', False):
            confidence += 0.1
            reasons.append("Has attachments")
        
        return {
            'is_receipt': confidence > 0.3,
            'confidence': min(confidence, 1.0),
            'reasons': reasons
        }
    
    def _is_receipt_sender(self, sender: str) -> bool:
        """Check if sender is known to send receipts"""
        receipt_domains = [
            'square.com', 'paypal.com', 'stripe.com', 'receipts.com',
            'anthropic.com', 'netflix.com', 'spotify.com', 'github.com',
            'apple.com', 'uber.com', 'microsoft.com', 'google.com'
        ]
        
        for domain in receipt_domains:
            if domain in sender:
                return True
        
        return False

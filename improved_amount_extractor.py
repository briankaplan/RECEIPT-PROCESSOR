
#!/usr/bin/env python3
"""
Improved Amount Extractor
Fixes $0.0 amount issues
"""

import re
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class ImprovedAmountExtractor:
    """Extracts amounts with multiple fallback methods"""
    
    def __init__(self):
        self.amount_patterns = [
            r'\$\s*(\d+\.?\d*)',  # $45.67
            r'(\d+\.?\d*)\s*USD',  # 45.67 USD
            r'Total:\s*\$?\s*(\d+\.?\d*)',  # Total: $45.67
            r'Amount:\s*\$?\s*(\d+\.?\d*)',  # Amount: $45.67
            r'(\d+\.?\d*)\s*dollars',  # 45.67 dollars
            r'charged\s*\$?\s*(\d+\.?\d*)',  # charged $45.67
            r'payment\s*of\s*\$?\s*(\d+\.?\d*)',  # payment of $45.67
        ]
    
    def extract_amount(self, text: str, email_data: Dict = None, transactions: List[Dict] = None) -> float:
        """Extract amount using multiple methods"""
        
        # Method 1: Direct text extraction
        amount = self._extract_from_text(text)
        if amount > 0:
            logger.info(f"💰 Extracted amount ${amount} from text")
            return amount
        
        # Method 2: Email data extraction
        if email_data:
            amount = self._extract_from_email(email_data)
            if amount > 0:
                logger.info(f"💰 Extracted amount ${amount} from email")
                return amount
        
        # Method 3: Transaction matching
        if transactions and email_data:
            amount = self._extract_from_transactions(email_data, transactions)
            if amount > 0:
                logger.info(f"💰 Extracted amount ${amount} from transaction matching")
                return amount
        
        return 0.0
    
    def _extract_from_text(self, text: str) -> float:
        """Extract amount from text using regex patterns"""
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    amount = float(matches[0])
                    if amount > 0:
                        return amount
                except ValueError:
                    continue
        
        return 0.0
    
    def _extract_from_email(self, email_data: Dict) -> float:
        """Extract amount from email data"""
        text = ''
        
        # Combine all text fields
        if email_data.get('subject'):
            text += email_data['subject'] + ' '
        if email_data.get('body'):
            text += email_data['body'] + ' '
        
        return self._extract_from_text(text)
    
    def _extract_from_transactions(self, email_data: Dict, transactions: List[Dict]) -> float:
        """Extract amount by matching with transactions"""
        email_date = email_data.get('date')
        email_subject = email_data.get('subject', '').lower()
        email_body = email_data.get('body', '').lower()
        
        if not email_date:
            return 0.0
        
        # Find transactions on the same date
        date_matches = [
            tx for tx in transactions 
            if tx.get('date') == email_date
        ]
        
        if len(date_matches) == 1:
            # Only one transaction on this date, likely a match
            return date_matches[0].get('amount', 0)
        
        # Multiple transactions, try to match by merchant keywords
        for tx in date_matches:
            tx_merchant = tx.get('merchant', '').lower()
            tx_description = tx.get('description', '').lower()
            
            # Check if merchant appears in email
            if tx_merchant in email_subject or tx_merchant in email_body:
                return tx.get('amount', 0)
            
            # Check if description keywords appear
            description_words = tx_description.split()
            for word in description_words:
                if len(word) > 3 and word in email_subject:
                    return tx.get('amount', 0)
        
        return 0.0

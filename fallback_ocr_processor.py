
#!/usr/bin/env python3
"""
Fallback OCR Processor
"""

import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class FallbackOCRProcessor:
    """Fallback OCR when HuggingFace API fails"""
    
    def __init__(self):
        self.amount_patterns = [
            r'\$\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*USD',
            r'Total:\s*\$?\s*(\d+\.?\d*)',
            r'Amount:\s*\$?\s*(\d+\.?\d*)',
        ]
    
    async def extract_receipt_data(self, image_path: str, email_data: Dict = None) -> Dict:
        """Extract receipt data using fallback methods"""
        
        # Try email parsing first
        if email_data:
            result = self._extract_from_email(email_data)
            if result and result.get('amount', 0) > 0:
                return result
        
        # Try basic image text extraction
        result = self._extract_from_image(image_path)
        if result and result.get('amount', 0) > 0:
            return result
        
        # Return default result
        return {
            'merchant': 'UNKNOWN',
            'amount': 0.0,
            'confidence': 0.1,
            'method': 'fallback'
        }
    
    def _extract_from_email(self, email_data: Dict) -> Optional[Dict]:
        """Extract from email data"""
        text = ''
        if email_data.get('subject'):
            text += email_data['subject'] + ' '
        if email_data.get('body'):
            text += email_data['body'] + ' '
        
        # Extract amount
        amount = 0.0
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    amount = float(matches[0])
                    if amount > 0:
                        break
                except ValueError:
                    continue
        
        # Extract merchant
        merchant = self._extract_merchant_from_text(text)
        
        if amount > 0:
            return {
                'merchant': merchant,
                'amount': amount,
                'confidence': 0.6,
                'method': 'email_parsing'
            }
        
        return None
    
    def _extract_from_image(self, image_path: str) -> Optional[Dict]:
        """Basic image text extraction"""
        try:
            # Try to extract any text from image
            # This is a simplified version
            return {
                'merchant': 'UNKNOWN',
                'amount': 0.0,
                'confidence': 0.2,
                'method': 'image_parsing'
            }
        except Exception as e:
            logger.warning(f"⚠️ Image extraction failed: {e}")
            return None
    
    def _extract_merchant_from_text(self, text: str) -> str:
        """Extract merchant from text"""
        text_lower = text.lower()
        
        merchants = {
            'claude': 'CLAUDE',
            'anthropic': 'ANTHROPIC',
            'netflix': 'NETFLIX',
            'spotify': 'SPOTIFY',
            'github': 'GITHUB',
            'apple': 'APPLE',
            'uber': 'UBER',
            'square': 'SQUARE',
            'paypal': 'PAYPAL'
        }
        
        for keyword, merchant in merchants.items():
            if keyword in text_lower:
                return merchant
        
        return 'UNKNOWN'

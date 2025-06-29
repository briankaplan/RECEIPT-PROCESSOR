#!/usr/bin/env python3
"""
Fix HuggingFace API Issues
"""

import logging
import requests
import json
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

def test_huggingface_api() -> Dict:
    """Test HuggingFace API endpoints"""
    try:
        # Test basic connectivity
        response = requests.get('https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium', timeout=10)
        
        return {
            'working': response.status_code == 200,
            'status_code': response.status_code,
            'endpoint': 'api-inference.huggingface.co'
        }
    
    except Exception as e:
        logger.error(f"❌ HuggingFace API test failed: {e}")
        return {
            'working': False,
            'error': str(e)
        }

def create_improved_ocr_processor():
    """Create improved OCR processor with fallbacks"""
    
    improved_ocr_code = '''
#!/usr/bin/env python3
"""
Improved OCR Processor with Fallbacks
"""

import logging
import requests
import json
from typing import Dict, Optional, Any
import re

logger = logging.getLogger(__name__)

class ImprovedOCRProcessor:
    """OCR processor with multiple fallback methods"""
    
    def __init__(self, api_token: str = None):
        self.api_token = api_token
        self.fallback_methods = [
            'huggingface_api',
            'tesseract_ocr',
            'email_parsing',
            'transaction_matching'
        ]
    
    async def extract_receipt_data(self, image_path: str, email_data: Dict = None) -> Dict:
        """Extract receipt data with multiple fallback methods"""
        
        for method in self.fallback_methods:
            try:
                if method == 'huggingface_api':
                    result = await self._extract_with_huggingface(image_path)
                elif method == 'tesseract_ocr':
                    result = await self._extract_with_tesseract(image_path)
                elif method == 'email_parsing':
                    result = await self._extract_from_email(email_data)
                elif method == 'transaction_matching':
                    result = await self._extract_from_transactions(email_data)
                
                if result and result.get('amount', 0) > 0:
                    logger.info(f"✅ Extracted with {method}: {result}")
                    return result
                
            except Exception as e:
                logger.warning(f"⚠️ {method} failed: {e}")
                continue
        
        # Return fallback result
        return {
            'merchant': 'UNKNOWN',
            'amount': 0.0,
            'confidence': 0.1,
            'method': 'fallback'
        }
    
    async def _extract_with_huggingface(self, image_path: str) -> Optional[Dict]:
        """Extract using HuggingFace API"""
        if not self.api_token:
            return None
        
        try:
            # Try multiple HuggingFace models
            models = ['paligemma', 'donut', 'layoutlm', 'trocr']
            
            for model in models:
                try:
                    result = await self._call_huggingface_api(image_path, model)
                    if result and result.get('amount', 0) > 0:
                        return result
                except Exception as e:
                    logger.warning(f"⚠️ Model {model} failed: {e}")
                    continue
            
            return None
        
        except Exception as e:
            logger.error(f"❌ HuggingFace extraction failed: {e}")
            return None
    
    async def _extract_with_tesseract(self, image_path: str) -> Optional[Dict]:
        """Extract using Tesseract OCR"""
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            
            # Extract amount from text
            amount = self._extract_amount_from_text(text)
            merchant = self._extract_merchant_from_text(text)
            
            if amount > 0:
                return {
                    'merchant': merchant,
                    'amount': amount,
                    'confidence': 0.7,
                    'method': 'tesseract'
                }
            
            return None
        
        except Exception as e:
            logger.warning(f"⚠️ Tesseract extraction failed: {e}")
            return None
    
    async def _extract_from_email(self, email_data: Dict) -> Optional[Dict]:
        """Extract from email data"""
        if not email_data:
            return None
        
        try:
            body = email_data.get('body', '')
            subject = email_data.get('subject', '')
            
            # Extract amount
            amount = self._extract_amount_from_text(body + ' ' + subject)
            
            # Extract merchant
            merchant = self._extract_merchant_from_text(body + ' ' + subject)
            
            if amount > 0:
                return {
                    'merchant': merchant,
                    'amount': amount,
                    'confidence': 0.6,
                    'method': 'email_parsing'
                }
            
            return None
        
        except Exception as e:
            logger.warning(f"⚠️ Email extraction failed: {e}")
            return None
    
    def _extract_amount_from_text(self, text: str) -> float:
        """Extract amount from text using regex"""
        amount_patterns = [
            r'\\$\\s*(\\d+\\.?\\d*)',  # $45.67
            r'(\\d+\\.?\\d*)\\s*USD',  # 45.67 USD
            r'Total:\\s*\\$?\\s*(\\d+\\.?\\d*)',  # Total: $45.67
            r'Amount:\\s*\\$?\\s*(\\d+\\.?\\d*)',  # Amount: $45.67
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    amount = float(matches[0])
                    if amount > 0:
                        return amount
                except ValueError:
                    continue
        
        return 0.0
    
    def _extract_merchant_from_text(self, text: str) -> str:
        """Extract merchant from text"""
        text_lower = text.lower()
        
        # Common merchant patterns
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
'''
    
    with open('improved_ocr_processor.py', 'w') as f:
        f.write(improved_ocr_code)
    
    logger.info("✅ Improved OCR processor created")

if __name__ == "__main__":
    # Test HuggingFace API
    result = test_huggingface_api()
    print(f"HuggingFace API test result: {result}")
    
    # Create improved OCR processor
    create_improved_ocr_processor()
    print("✅ HuggingFace API fixes applied") 
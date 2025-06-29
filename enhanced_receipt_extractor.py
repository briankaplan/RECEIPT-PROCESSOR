#!/usr/bin/env python3
"""
Enhanced Receipt Extractor
Uses multiple methods to extract receipt data without relying on external OCR APIs
"""

import re
import logging
import base64
import subprocess
import tempfile
import os
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class ExtractedReceiptData:
    """Extracted receipt data"""
    merchant: str = ""
    amount: float = 0.0
    date: str = ""
    category: str = ""
    confidence: float = 0.0
    extraction_method: str = ""
    raw_text: str = ""

class EnhancedReceiptExtractor:
    """Enhanced receipt extractor with multiple fallback methods"""
    
    def __init__(self):
        # Check if Tesseract is available
        self.tesseract_available = self._check_tesseract()
        if self.tesseract_available:
            logger.info("✅ Tesseract OCR available for image processing")
        else:
            logger.info("⚠️ Tesseract OCR not available, using email extraction only")
        
        # Common merchant patterns and variations
        self.merchant_patterns = {
            # Tech subscriptions
            'claude': ['claude.ai', 'claude', 'anthropic'],
            'midjourney': ['midjourney', 'midjourney inc', 'midjourney.com'],
            'expensify': ['expensify', 'expensify inc', 'expensify.com'],
            'huggingface': ['huggingface', 'huggingface.co', 'hf'],
            'sourcegraph': ['sourcegraph', 'sourcegraph.com'],
            'anthropic': ['anthropic', 'anthropic.com'],
            
            # Google services
            'google': ['google', 'google *gsuite', 'google workspace', 'gsuite'],
            
            # Hotels
            'cambria': ['cambria', 'cambria hotel', 'cambria hotel nashville'],
            
            # Professional services
            'hive': ['hive', 'hive co', 'hiveco.com'],
            
            # E-commerce
            'bestbuy': ['bestbuy', 'bestbuy.com', 'best buy'],
            'elementor': ['elementor', 'elementor.com'],
            'fyxer': ['fyxer', 'ai.fyxer.com'],
            'retrosupply': ['retrosupply', 'retrosupply.co'],
            
            # Creative tools
            'dashlane': ['dashlane', 'dashlane u* dashlane p'],
            'myfonts': ['myfonts', 'sp myfonts inc'],
            'every': ['every', 'every studio'],
            'taskade': ['taskade', 'taskade.com'],
            
            # Restaurants
            'tst': ['tst', 'tst*green hills grille', 'tst* tn731 - cambria'],
            'toast': ['toast', 'toast pos'],
            
            # Other
            'cowboy': ['cowboy', 'cowboy channel'],
            'gruhn': ['gruhn', 'gruhn guitars'],
            'valet': ['valet', 'valet tips']
        }
        
        # Brand mappings for better merchant extraction
        self.brand_mappings = {
            'claude': 'anthropic',
            'claude ai': 'anthropic',
            'anthropic claude': 'anthropic',
            'openai': 'openai',
            'chatgpt': 'openai',
            'gpt': 'openai',
            'github': 'github',
            'github copilot': 'github',
            'copilot': 'github',
            'microsoft': 'microsoft',
            'azure': 'microsoft',
            'office 365': 'microsoft',
            'google': 'google',
            'google workspace': 'google',
            'gmail': 'google',
            'amazon': 'amazon',
            'aws': 'amazon',
            'amazon web services': 'amazon',
            'stripe': 'stripe',
            'square': 'square',
            'paypal': 'paypal',
            'every': 'every.com',
            'every.com': 'every.com'
        }
        
        # Amount extraction patterns
        self.amount_patterns = [
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*USD',  # 1,234.56 USD
            r'USD\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # USD 1,234.56
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*dollars',  # 1,234.56 dollars
            r'total.*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # total $1,234.56
            r'amount.*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # amount $1,234.56
            r'charged.*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # charged $1,234.56
            r'payment.*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # payment $1,234.56
        ]
        
        # Date patterns
        self.date_patterns = [
            r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',
            r'(\d{1,2})\s+(\w+)\s+(\d{4})'
        ]
        
        # Receipt keywords for confidence scoring
        self.receipt_keywords = [
            'receipt', 'invoice', 'bill', 'payment', 'transaction', 'order',
            'confirmation', 'purchase', 'total', 'amount', 'charged', 'subtotal',
            'tax', 'total amount', 'payment confirmation', 'order summary'
        ]
    
    def _check_tesseract(self) -> bool:
        """Check if Tesseract is available"""
        try:
            result = subprocess.run(['tesseract', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def extract_from_email(self, email_data: Dict) -> ExtractedReceiptData:
        """Extract receipt data from email using multiple methods"""
        try:
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')
            from_email = email_data.get('from_email', '')
            date = email_data.get('date', '')

            # Method 1: Extract from subject
            subject_data = self._extract_from_subject(subject)
            
            # Method 2: Extract from body
            body_data = self._extract_from_body(body)
            
            # Method 3: Extract from sender
            sender_data = self._extract_from_sender(from_email)
            
            # Combine all methods
            combined_data = self._combine_extraction_results([
                subject_data, body_data, sender_data
            ])
            
            # Add metadata
            combined_data.date = date
            combined_data.from_email = from_email
            combined_data.subject = subject
            
            return combined_data
            
        except Exception as e:
            logger.error(f"Error extracting from email: {e}")
            return ExtractedReceiptData()
    
    def extract_from_image(self, image_path: str, email_data: Dict) -> ExtractedReceiptData:
        """Extract receipt data from image using Tesseract OCR"""
        try:
            if not self.tesseract_available:
                logger.info("Tesseract not available, using email fallback")
                return self.extract_from_email(email_data)
            
            # Use Tesseract to extract text from image
            ocr_text = self._extract_text_with_tesseract(image_path)
            
            if ocr_text:
                # Extract data from OCR text
                extracted_data = self._extract_from_text(ocr_text)
                extracted_data.extraction_method = "tesseract_ocr"
                extracted_data.raw_text = ocr_text
                
                # If OCR didn't find much, fall back to email extraction
                if not extracted_data.merchant and not extracted_data.amount:
                    logger.info("OCR didn't find useful data, using email fallback")
                    return self.extract_from_email(email_data)
                
                return extracted_data
            else:
                logger.info("OCR failed, using email fallback")
                return self.extract_from_email(email_data)
            
        except Exception as e:
            logger.error(f"Error extracting from image: {e}")
            return self.extract_from_email(email_data)
    
    def extract_from_file(self, file_path: str, email_data: Dict) -> ExtractedReceiptData:
        """Extract receipt data from file using Tesseract OCR"""
        try:
            # Check if it's an image file
            image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in image_extensions:
                return self.extract_from_image(file_path, email_data)
            else:
                logger.info(f"File type {file_ext} not supported for OCR, using email fallback")
                return self.extract_from_email(email_data)
            
        except Exception as e:
            logger.error(f"Error extracting from file: {e}")
            return self.extract_from_email(email_data)
    
    def _extract_text_with_tesseract(self, image_path: str) -> str:
        """Extract text from image using Tesseract"""
        try:
            # Run Tesseract OCR
            result = subprocess.run([
                'tesseract', 
                image_path, 
                'stdout', 
                '--psm', '6',  # Assume uniform block of text
                '--oem', '3'   # Default OCR Engine Mode
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"Tesseract failed: {result.stderr}")
                return ""
                
        except subprocess.TimeoutExpired:
            logger.error("Tesseract OCR timed out")
            return ""
        except Exception as e:
            logger.error(f"Error running Tesseract: {e}")
            return ""
    
    def _extract_from_text(self, text: str) -> ExtractedReceiptData:
        """Extract receipt data from text"""
        try:
            data = ExtractedReceiptData(extraction_method="text_analysis")
            
            # Extract merchant
            merchant = self._extract_merchant_from_text(text)
            if merchant:
                data.merchant = merchant
                data.confidence += 0.3
            
            # Extract amount
            amount = self._extract_amount_from_text(text)
            if amount > 0:
                data.amount = amount
                data.confidence += 0.3
            
            # Extract date
            date = self._extract_date_from_text(text)
            if date:
                data.date = date
                data.confidence += 0.1
            
            # Check for receipt keywords
            receipt_keywords_found = sum(1 for keyword in self.receipt_keywords 
                                       if keyword.lower() in text.lower())
            if receipt_keywords_found > 0:
                data.confidence += min(receipt_keywords_found * 0.05, 0.3)
            
            return data
            
        except Exception as e:
            logger.error(f"Error extracting from text: {e}")
            return ExtractedReceiptData()
    
    def _extract_from_subject(self, subject: str) -> ExtractedReceiptData:
        """Extract receipt data from email subject"""
        try:
            data = ExtractedReceiptData(extraction_method="subject")
            
            # Extract merchant
            merchant = self._extract_merchant_from_text(subject)
            if merchant:
                data.merchant = merchant
                data.confidence += 0.3
            
            # Extract amount
            amount = self._extract_amount_from_text(subject)
            if amount > 0:
                data.amount = amount
                data.confidence += 0.3
            
            # Extract date
            date = self._extract_date_from_text(subject)
            if date:
                data.date = date
                data.confidence += 0.1
            
            return data
            
        except Exception as e:
            logger.error(f"Error extracting from subject: {e}")
            return ExtractedReceiptData()
    
    def _extract_from_body(self, body: str) -> ExtractedReceiptData:
        """Extract receipt data from email body"""
        try:
            data = ExtractedReceiptData(extraction_method="body")
            
            # Extract merchant
            merchant = self._extract_merchant_from_text(body)
            if merchant:
                data.merchant = merchant
                data.confidence += 0.2
            
            # Extract amount
            amount = self._extract_amount_from_text(body)
            if amount > 0:
                data.amount = amount
                data.confidence += 0.2
            
            # Extract date
            date = self._extract_date_from_text(body)
            if date:
                data.date = date
                data.confidence += 0.1
            
            # Check for receipt keywords
            receipt_keywords_found = sum(1 for keyword in self.receipt_keywords 
                                       if keyword.lower() in body.lower())
            if receipt_keywords_found > 0:
                data.confidence += min(receipt_keywords_found * 0.05, 0.3)
            
            return data
            
        except Exception as e:
            logger.error(f"Error extracting from body: {e}")
            return ExtractedReceiptData()
    
    def _extract_from_sender(self, from_email: str) -> ExtractedReceiptData:
        """Extract receipt data from sender email"""
        try:
            data = ExtractedReceiptData(extraction_method="sender")
            
            # Extract domain
            domain = from_email.split('@')[-1].lower() if '@' in from_email else ''
            
            # Match domain to known merchants
            for merchant_name, patterns in self.merchant_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in domain or domain in pattern.lower():
                        data.merchant = merchant_name.upper()
                        data.confidence += 0.4
                        return data
            
            return data
            
        except Exception as e:
            logger.error(f"Error extracting from sender: {e}")
            return ExtractedReceiptData()
    
    def _extract_merchant_from_text(self, text: str) -> str:
        """Extract merchant name from text"""
        try:
            text_lower = text.lower()
            
            # First check brand mappings for exact matches
            for brand_key, brand_name in self.brand_mappings.items():
                if brand_key in text_lower:
                    return brand_name.upper()
            
            # Check merchant patterns
            for merchant_name, patterns in self.merchant_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in text_lower:
                        return merchant_name.upper()
            
            # Look for common receipt patterns
            receipt_patterns = [
                r'from\s+([a-zA-Z0-9\s&]+?)(?:\s+receipt|\s+invoice|\s+confirmation)',
                r'receipt\s+from\s+([a-zA-Z0-9\s&]+)',
                r'invoice\s+from\s+([a-zA-Z0-9\s&]+)',
                r'payment\s+to\s+([a-zA-Z0-9\s&]+)',
                r'charged\s+by\s+([a-zA-Z0-9\s&]+)',
                r'order\s+from\s+([a-zA-Z0-9\s&]+)',
                r'purchase\s+from\s+([a-zA-Z0-9\s&]+)'
            ]
            
            for pattern in receipt_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    merchant = match.group(1).strip()
                    if len(merchant) > 2:  # Avoid very short matches
                        return merchant.upper()
            
            # Look for domain-based extraction
            domain_pattern = r'@([a-zA-Z0-9.-]+)'
            domain_match = re.search(domain_pattern, text)
            if domain_match:
                domain = domain_match.group(1).lower()
                # Map common domains to merchant names
                domain_mappings = {
                    'anthropic.com': 'ANTHROPIC',
                    'openai.com': 'OPENAI',
                    'github.com': 'GITHUB',
                    'microsoft.com': 'MICROSOFT',
                    'google.com': 'GOOGLE',
                    'amazon.com': 'AMAZON',
                    'stripe.com': 'STRIPE',
                    'square.com': 'SQUARE',
                    'paypal.com': 'PAYPAL',
                    'every.com': 'EVERY.COM'
                }
                
                for domain_key, merchant_name in domain_mappings.items():
                    if domain_key in domain or domain in domain_key:
                        return merchant_name
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting merchant: {e}")
            return ""
    
    def _extract_amount_from_text(self, text: str) -> float:
        """Extract amount from text"""
        try:
            for pattern in self.amount_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    amount = float(amount_str)
                    if amount > 0:
                        return amount
            return 0.0
        except Exception as e:
            logger.warning(f"Error extracting amount from text: {e}")
            return 0.0
    
    def _extract_date_from_text(self, text: str) -> str:
        """Extract date from text"""
        try:
            for pattern in self.date_patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(0)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting date: {e}")
            return ""
    
    def _combine_extraction_results(self, results: List[ExtractedReceiptData]) -> ExtractedReceiptData:
        """Combine extraction results from multiple methods"""
        try:
            combined = ExtractedReceiptData(extraction_method="combined")
            
            # Combine merchants (prefer subject, then sender, then body)
            for result in results:
                if result.merchant:
                    combined.merchant = result.merchant
                    combined.confidence += result.confidence
            
            # Combine amounts (prefer subject, then body)
            for result in results:
                if result.amount > 0:
                    combined.amount = result.amount
                    combined.confidence += result.confidence
            
            # Combine dates
            for result in results:
                if result.date:
                    combined.date = result.date
            
            # Additional confidence based on overall content
            combined.confidence = min(combined.confidence, 1.0)
            
            # Check for receipt-like content
            receipt_keywords_found = sum(1 for keyword in self.receipt_keywords 
                                       if keyword.lower() in (getattr(combined, 'subject', '') + ' ' + getattr(combined, 'body', '')).lower())
            if receipt_keywords_found > 0:
                combined.confidence += min(receipt_keywords_found * 0.05, 0.2)
            
            return combined
            
        except Exception as e:
            logger.error(f"Error combining extraction results: {e}")
            return ExtractedReceiptData()

# Test the enhanced extractor
def test_enhanced_extractor():
    """Test the enhanced receipt extractor"""
    extractor = EnhancedReceiptExtractor()
    
    test_emails = [
        {
            'subject': 'Receipt from Claude.AI - $20.00',
            'body': 'Thank you for your Claude.AI subscription. Amount: $20.00',
            'from_email': 'receipts@claude.ai',
            'date': '2025-06-28'
        },
        {
            'subject': 'Your Midjourney subscription - $10.00',
            'body': 'Midjourney subscription payment confirmed. Total: $10.00',
            'from_email': 'billing@midjourney.com',
            'date': '2025-06-28'
        },
        {
            'subject': 'Google Workspace payment - $244.87',
            'body': 'Google Workspace billing confirmation. Amount charged: $244.87',
            'from_email': 'noreply-payments@google.com',
            'date': '2025-06-28'
        }
    ]
    
    for i, email in enumerate(test_emails, 1):
        result = extractor.extract_from_email(email)
        print(f"\nTest {i}:")
        print(f"  Merchant: {result.merchant}")
        print(f"  Amount: ${result.amount}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Method: {result.extraction_method}")

if __name__ == "__main__":
    test_enhanced_extractor() 
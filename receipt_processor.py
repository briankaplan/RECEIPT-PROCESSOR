import os
import re
import logging
from datetime import datetime, timedelta
import pytesseract
from PIL import Image
import PyPDF2
import json
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class EnhancedReceiptProcessor:
    """Advanced receipt processor with enhanced parsing algorithms"""
    
    def __init__(self):
        self.receipt_keywords = [
            'receipt', 'invoice', 'bill', 'payment', 'purchase',
            'total', 'subtotal', 'tax', 'amount', 'due'
        ]
        
        self.receipt_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp']
        
        # Enhanced merchant patterns
        self.merchant_patterns = {
            'starbucks': ['starbucks', 'sbux'],
            'amazon': ['amazon', 'amzn'],
            'walmart': ['walmart', 'wal-mart'],
            'target': ['target'],
            'costco': ['costco'],
            'kroger': ['kroger'],
            'shell': ['shell'],
            'exxon': ['exxon'],
            'chevron': ['chevron'],
            'mcdonalds': ['mcdonald', 'mcdonalds'],
            'subway': ['subway'],
            'chipotle': ['chipotle']
        }
        
        # Enhanced date patterns with context
        self.date_patterns = [
            (r'(\d{1,2}/\d{1,2}/\d{4})', '%m/%d/%Y'),
            (r'(\d{1,2}-\d{1,2}-\d{4})', '%m-%d-%Y'),
            (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),
            (r'(\w{3}\s+\d{1,2},\s+\d{4})', '%b %d, %Y'),
            (r'(\d{1,2}\s+\w{3}\s+\d{4})', '%d %b %Y'),
            (r'(\d{2}/\d{2}/\d{2})', '%m/%d/%y')
        ]
        
        # Enhanced amount patterns
        self.amount_patterns = [
            (r'total[\s:]*\$?(\d+\.?\d*)', 'total'),
            (r'amount\s+due[\s:]*\$?(\d+\.?\d*)', 'total'),
            (r'balance[\s:]*\$?(\d+\.?\d*)', 'total'),
            (r'grand\s+total[\s:]*\$?(\d+\.?\d*)', 'total'),
            (r'tax[\s:]*\$?(\d+\.?\d*)', 'tax'),
            (r'subtotal[\s:]*\$?(\d+\.?\d*)', 'subtotal')
        ]
        
        # Line item patterns
        self.line_item_patterns = [
            r'(\d+\.?\d*)\s*x\s*(.+?)\s*\$(\d+\.?\d*)',  # Qty x Item $Price
            r'(.+?)\s*\$(\d+\.?\d*)\s*$',  # Item $Price
            r'(\d+)\s+(.+?)\s+(\d+\.?\d*)',  # Qty Item Price
        ]
        
        logger.info("🧾 Enhanced Receipt Processor initialized")
    
    def extract_receipt_data(self, filepath: str) -> Optional[Dict]:
        """Extract comprehensive receipt data using enhanced algorithms"""
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return None
        
        try:
            # Extract raw text
            raw_text = self._extract_raw_text(filepath)
            if not raw_text:
                logger.warning(f"No text extracted from {filepath}")
                return None
            
            # Enhanced parsing
            receipt_data = self._enhanced_parse_receipt(raw_text)
            receipt_data.update({
                'source_file': os.path.basename(filepath),
                'processed_at': datetime.now().isoformat(),
                'extraction_method': 'enhanced_parser',
                'raw_text': raw_text,
                'file_size': os.path.getsize(filepath)
            })
            
            logger.info(f"✨ Enhanced extraction completed for {filepath}")
            return receipt_data
            
        except Exception as e:
            logger.error(f"Enhanced processing failed for {filepath}: {str(e)}")
            return None
    
    def _extract_raw_text(self, filepath: str) -> str:
        """Extract raw text from file using appropriate method"""
        file_ext = os.path.splitext(filepath)[1].lower()
        
        if file_ext == '.pdf':
            return self._extract_text_from_pdf(filepath)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            return self._extract_text_from_image(filepath)
        else:
            logger.warning(f"Unsupported file type: {file_ext}")
            return ""
    
    def _enhanced_parse_receipt(self, text: str) -> Dict:
        """Enhanced parsing with improved pattern recognition"""
        
        # Clean and normalize text
        cleaned_text = self._clean_text(text)
        lines = cleaned_text.split('\n')
        
        receipt_data = {
            'merchant': None,
            'merchant_confidence': 0.0,
            'date': None,
            'date_confidence': 0.0,
            'total_amount': None,
            'total_confidence': 0.0,
            'subtotal': None,
            'tax_amount': None,
            'items': [],
            'payment_method': None,
            'receipt_number': None,
            'phone_number': None,
            'address': None,
            'processing_quality': 'enhanced'
        }
        
        # Extract merchant with enhanced matching
        receipt_data.update(self._extract_merchant_enhanced(lines))
        
        # Extract date with context awareness
        receipt_data.update(self._extract_date_enhanced(lines))
        
        # Extract amounts with validation
        receipt_data.update(self._extract_amounts_enhanced(lines))
        
        # Extract line items with intelligent parsing
        receipt_data['items'] = self._extract_items_enhanced(lines)
        
        # Extract additional fields
        receipt_data.update(self._extract_additional_fields(lines))
        
        # Calculate overall confidence
        receipt_data['overall_confidence'] = self._calculate_overall_confidence(receipt_data)
        
        return receipt_data
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize OCR text for better parsing"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR errors
        ocr_corrections = {
            r'\bO\b': '0',  # O to 0
            r'\bl\b': '1',  # l to 1
            r'\bS\b(?=\d)': '5',  # S to 5 before numbers
        }
        
        for pattern, replacement in ocr_corrections.items():
            text = re.sub(pattern, replacement, text)
        
        return text.strip()
    
    def _extract_merchant_enhanced(self, lines: List[str]) -> Dict:
        """Enhanced merchant extraction with pattern matching and confidence scoring"""
        merchant_data = {'merchant': None, 'merchant_confidence': 0.0}
        
        # Check first few lines for merchant name (common location)
        for i, line in enumerate(lines[:5]):
            line_clean = line.strip().upper()
            
            if not line_clean or len(line_clean) < 3:
                continue
            
            # Check against known merchant patterns
            for merchant, patterns in self.merchant_patterns.items():
                for pattern in patterns:
                    if pattern.upper() in line_clean:
                        merchant_data['merchant'] = merchant.title()
                        merchant_data['merchant_confidence'] = 0.9 - (i * 0.1)  # Higher confidence for earlier lines
                        return merchant_data
            
            # Generic merchant detection (business-like names)
            if (len(line_clean.split()) <= 4 and 
                not any(word in line_clean for word in ['RECEIPT', 'INVOICE', 'THANK', 'STORE']) and
                any(c.isalpha() for c in line_clean)):
                
                merchant_data['merchant'] = line.strip().title()
                merchant_data['merchant_confidence'] = 0.7 - (i * 0.1)
                return merchant_data
        
        return merchant_data
    
    def _extract_date_enhanced(self, lines: List[str]) -> Dict:
        """Enhanced date extraction with context validation"""
        date_data = {'date': None, 'date_confidence': 0.0}
        
        current_date = datetime.now()
        best_date = None
        best_confidence = 0.0
        
        for line in lines:
            for pattern, date_format in self.date_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    try:
                        parsed_date = datetime.strptime(match.group(1), date_format)
                        
                        # Validate date reasonableness (not future, not too old)
                        days_diff = (current_date - parsed_date).days
                        if -1 <= days_diff <= 365:  # Allow 1 day future, up to 1 year old
                            confidence = 0.9 - (days_diff / 365 * 0.3)  # Reduce confidence for older dates
                            
                            if confidence > best_confidence:
                                best_date = parsed_date.strftime('%Y-%m-%d')
                                best_confidence = confidence
                    
                    except ValueError:
                        continue
        
        if best_date:
            date_data['date'] = best_date
            date_data['date_confidence'] = best_confidence
        
        return date_data
    
    def _extract_amounts_enhanced(self, lines: List[str]) -> Dict:
        """Enhanced amount extraction with validation and context"""
        amount_data = {
            'total_amount': None,
            'total_confidence': 0.0,
            'subtotal': None,
            'tax_amount': None
        }
        
        amounts_found = {'total': [], 'tax': [], 'subtotal': []}
        
        for line in lines:
            line_lower = line.lower()
            
            for pattern, amount_type in self.amount_patterns:
                matches = re.finditer(pattern, line_lower)
                for match in matches:
                    try:
                        amount = float(match.group(1))
                        
                        # Validate amount reasonableness
                        if 0.01 <= amount <= 10000:  # Reasonable receipt amounts
                            amounts_found[amount_type].append(amount)
                    
                    except ValueError:
                        continue
        
        # Process found amounts
        if amounts_found['total']:
            # Use the largest total amount (most likely to be correct)
            amount_data['total_amount'] = max(amounts_found['total'])
            amount_data['total_confidence'] = 0.8
        
        if amounts_found['subtotal']:
            amount_data['subtotal'] = max(amounts_found['subtotal'])
        
        if amounts_found['tax']:
            amount_data['tax_amount'] = max(amounts_found['tax'])
        
        # Validate total vs subtotal + tax
        if (amount_data['subtotal'] and amount_data['tax_amount'] and 
            amount_data['total_amount']):
            calculated_total = amount_data['subtotal'] + amount_data['tax_amount']
            if abs(calculated_total - amount_data['total_amount']) < 0.02:
                amount_data['total_confidence'] = 0.95
        
        return amount_data
    
    def _extract_items_enhanced(self, lines: List[str]) -> List[Dict]:
        """Enhanced line item extraction with intelligent parsing"""
        items = []
        
        for line in lines:
            line = line.strip()
            
            if not line or len(line) < 5:
                continue
            
            # Skip lines that are clearly not items
            skip_keywords = ['total', 'subtotal', 'tax', 'change', 'receipt', 'thank', 'store']
            if any(keyword in line.lower() for keyword in skip_keywords):
                continue
            
            # Try different line item patterns
            for pattern in self.line_item_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        if len(match.groups()) == 3:  # Qty x Item $Price or Qty Item Price
                            if 'x' in line.lower():
                                qty, name, price = match.groups()
                            else:
                                qty, name, price = match.groups()
                            
                            items.append({
                                'name': name.strip(),
                                'quantity': float(qty),
                                'price': float(price),
                                'total': float(qty) * float(price)
                            })
                        elif len(match.groups()) == 2:  # Item $Price
                            name, price = match.groups()
                            items.append({
                                'name': name.strip(),
                                'quantity': 1.0,
                                'price': float(price),
                                'total': float(price)
                            })
                        break
                    
                    except (ValueError, IndexError):
                        continue
        
        return items
    
    def _extract_additional_fields(self, lines: List[str]) -> Dict:
        """Extract additional receipt fields"""
        additional_data = {
            'payment_method': None,
            'receipt_number': None,
            'phone_number': None,
            'address': None
        }
        
        for line in lines:
            line_lower = line.lower()
            
            # Payment method
            if not additional_data['payment_method']:
                payment_methods = ['cash', 'credit', 'debit', 'visa', 'mastercard', 'amex', 'discover']
                for method in payment_methods:
                    if method in line_lower:
                        additional_data['payment_method'] = method
                        break
            
            # Receipt number
            if not additional_data['receipt_number']:
                receipt_patterns = [
                    r'receipt\s*#?\s*(\w+)',
                    r'transaction\s*#?\s*(\w+)',
                    r'order\s*#?\s*(\w+)',
                    r'ref\s*#?\s*(\w+)'
                ]
                
                for pattern in receipt_patterns:
                    match = re.search(pattern, line_lower)
                    if match:
                        additional_data['receipt_number'] = match.group(1).upper()
                        break
            
            # Phone number
            if not additional_data['phone_number']:
                phone_match = re.search(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', line)
                if phone_match:
                    additional_data['phone_number'] = phone_match.group(1)
            
            # Address (simple detection)
            if not additional_data['address']:
                # Look for address patterns (street number + street name)
                address_match = re.search(r'(\d+\s+\w+\s+(?:st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|way|ct|court))', line, re.IGNORECASE)
                if address_match:
                    additional_data['address'] = address_match.group(1)
        
        return additional_data
    
    def _calculate_overall_confidence(self, receipt_data: Dict) -> float:
        """Calculate overall confidence score for the receipt parsing"""
        confidence_factors = []
        
        if receipt_data.get('merchant_confidence'):
            confidence_factors.append(receipt_data['merchant_confidence'])
        
        if receipt_data.get('date_confidence'):
            confidence_factors.append(receipt_data['date_confidence'])
        
        if receipt_data.get('total_confidence'):
            confidence_factors.append(receipt_data['total_confidence'])
        
        # Bonus for having items
        if receipt_data.get('items'):
            confidence_factors.append(0.8)
        
        # Bonus for additional fields
        additional_fields = sum(1 for field in ['payment_method', 'receipt_number', 'phone_number'] 
                              if receipt_data.get(field))
        if additional_fields > 0:
            confidence_factors.append(0.6 + (additional_fields * 0.1))
        
        return round(sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0, 2)
    
    def _extract_text_from_pdf(self, filepath: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with open(filepath, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from PDF {filepath}: {str(e)}")
            return ""
    
    def _extract_text_from_image(self, filepath: str) -> str:
        """Extract text from image using OCR"""
        try:
            image = Image.open(filepath)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from image {filepath}: {str(e)}")
            return ""
    
    def get_processing_stats(self) -> Dict:
        """Get processing capabilities and statistics"""
        return {
            'processor_type': 'enhanced_internal',
            'supported_extensions': self.receipt_extensions,
            'features': [
                'Enhanced merchant recognition',
                'Intelligent date parsing',
                'Validated amount extraction',
                'Line item detection',
                'Confidence scoring',
                'Additional field extraction'
            ],
            'merchant_patterns': len(self.merchant_patterns),
            'date_patterns': len(self.date_patterns),
            'amount_patterns': len(self.amount_patterns)
        }


# Backward compatibility
class ReceiptProcessor(EnhancedReceiptProcessor):
    """Backward compatible receipt processor with enhanced capabilities"""
    pass

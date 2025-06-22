import os
import re
import logging
from datetime import datetime
import pytesseract
from PIL import Image
import PyPDF2
import json

logger = logging.getLogger(__name__)

class ReceiptProcessor:
    """Process receipt files and extract relevant data"""
    
    def __init__(self):
        self.receipt_keywords = [
            'receipt', 'invoice', 'bill', 'payment', 'purchase',
            'total', 'subtotal', 'tax', 'amount', 'due'
        ]
        
        self.receipt_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp']
    
    def is_receipt_file(self, filename):
        """Check if file is likely a receipt based on name and extension"""
        if not filename:
            return False
        
        filename_lower = filename.lower()
        
        # Check extension
        has_valid_ext = any(filename_lower.endswith(ext) for ext in self.receipt_extensions)
        
        # Check for receipt keywords in filename
        has_receipt_keyword = any(keyword in filename_lower for keyword in self.receipt_keywords)
        
        return has_valid_ext and (has_receipt_keyword or self._looks_like_receipt_name(filename_lower))
    
    def _looks_like_receipt_name(self, filename):
        """Additional heuristics to identify receipt files"""
        # Common receipt patterns
        patterns = [
            r'receipt',
            r'invoice',
            r'\d{4}-\d{2}-\d{2}',  # Date patterns
            r'bill',
            r'payment',
            r'purchase'
        ]
        
        return any(re.search(pattern, filename, re.IGNORECASE) for pattern in patterns)
    
    def extract_receipt_data(self, filepath):
        """Extract data from receipt file"""
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return None
        
        try:
            file_ext = os.path.splitext(filepath)[1].lower()
            
            if file_ext == '.pdf':
                text = self._extract_text_from_pdf(filepath)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                text = self._extract_text_from_image(filepath)
            else:
                logger.warning(f"Unsupported file type: {file_ext}")
                return None
            
            if not text:
                logger.warning(f"No text extracted from {filepath}")
                return None
            
            # Parse extracted text
            receipt_data = self._parse_receipt_text(text)
            receipt_data['source_file'] = os.path.basename(filepath)
            receipt_data['processed_at'] = datetime.now().isoformat()
            
            logger.info(f"Extracted receipt data from {filepath}")
            return receipt_data
            
        except Exception as e:
            logger.error(f"Error processing receipt {filepath}: {str(e)}")
            return None
    
    def _extract_text_from_pdf(self, filepath):
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
    
    def _extract_text_from_image(self, filepath):
        """Extract text from image using OCR"""
        try:
            # Configure tesseract if needed
            # pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
            
            image = Image.open(filepath)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from image {filepath}: {str(e)}")
            return ""
    
    def _parse_receipt_text(self, text):
        """Parse receipt text to extract structured data"""
        data = {
            'raw_text': text,
            'merchant': None,
            'date': None,
            'total_amount': None,
            'items': [],
            'tax_amount': None,
            'payment_method': None
        }
        
        lines = text.split('\n')
        
        # Extract merchant (usually first non-empty line)
        for line in lines:
            if line.strip():
                data['merchant'] = line.strip()
                break
        
        # Extract date
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\w+ \d{1,2}, \d{4}'
        ]
        
        for line in lines:
            for pattern in date_patterns:
                match = re.search(pattern, line)
                if match:
                    data['date'] = match.group()
                    break
            if data['date']:
                break
        
        # Extract amounts
        amount_patterns = [
            r'total[\s:]*\$?(\d+\.?\d*)',
            r'amount[\s:]*\$?(\d+\.?\d*)',
            r'due[\s:]*\$?(\d+\.?\d*)',
            r'\$(\d+\.\d{2})'
        ]
        
        amounts = []
        for line in lines:
            line_lower = line.lower()
            
            # Look for total amount
            if any(word in line_lower for word in ['total', 'amount due', 'balance']):
                for pattern in amount_patterns:
                    matches = re.findall(pattern, line_lower)
                    if matches:
                        try:
                            amount = float(matches[-1])  # Take the last match
                            amounts.append(amount)
                        except ValueError:
                            continue
            
            # Look for tax
            if 'tax' in line_lower:
                tax_match = re.search(r'\$?(\d+\.?\d*)', line)
                if tax_match:
                    try:
                        data['tax_amount'] = float(tax_match.group(1))
                    except ValueError:
                        pass
        
        # Set total amount (largest amount found, assuming it's the total)
        if amounts:
            data['total_amount'] = max(amounts)
        
        # Extract payment method
        payment_methods = ['cash', 'credit', 'debit', 'card', 'visa', 'mastercard', 'amex']
        for line in lines:
            line_lower = line.lower()
            for method in payment_methods:
                if method in line_lower:
                    data['payment_method'] = method
                    break
            if data['payment_method']:
                break
        
        # Extract line items (simplified)
        for line in lines:
            # Look for lines with item name and price
            if '$' in line and not any(word in line.lower() for word in ['total', 'tax', 'subtotal']):
                price_match = re.search(r'\$(\d+\.?\d*)', line)
                if price_match:
                    item_name = re.sub(r'\$\d+\.?\d*', '', line).strip()
                    if item_name and len(item_name) > 2:
                        data['items'].append({
                            'name': item_name,
                            'price': float(price_match.group(1))
                        })
        
        return data

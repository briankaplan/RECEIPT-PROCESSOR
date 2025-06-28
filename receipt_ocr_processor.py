#!/usr/bin/env python3
"""
Advanced OCR Receipt Processor
Extracts real receipt data from PDF and image attachments
"""

import os
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import requests
from io import BytesIO
import json

logger = logging.getLogger(__name__)

class ReceiptOCRProcessor:
    """Advanced OCR processor for receipt data extraction"""
    
    def __init__(self, r2_client=None):
        self.r2_client = r2_client
        self.date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # MM/DD/YYYY or MM-DD-YYYY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',    # YYYY/MM/DD or YYYY-MM-DD
            r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})',      # Jan 15, 2024
            r'(\d{1,2})\s+(\w{3})\s+(\d{4})',        # 15 Jan 2024
        ]
        
        self.amount_patterns = [
            r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56 or 1234.56
            r'total[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # Total: $123.45
            r'amount[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # Amount: $123.45
        ]
        
        self.merchant_patterns = [
            r'^([A-Z][A-Z\s&]+(?:LLC|INC|CORP|CO|LTD)?)',  # Uppercase merchant names
            r'from[:\s]*([A-Z][A-Z\s&]+)',  # From: MERCHANT NAME
            r'merchant[:\s]*([A-Z][A-Z\s&]+)',  # Merchant: NAME
        ]

    def download_from_r2(self, r2_url: str) -> Optional[bytes]:
        """Download file from R2 storage"""
        try:
            if not self.r2_client:
                logger.warning("R2 client not available")
                return None
                
            response = requests.get(r2_url)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Failed to download from R2: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading from R2: {e}")
            return None

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content"""
        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""

    def extract_text_from_image(self, image_content: bytes) -> str:
        """Extract text from image using OCR"""
        try:
            image = Image.open(BytesIO(image_content))
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return ""

    def parse_date(self, text: str) -> Optional[datetime]:
        """Parse date from text using multiple patterns"""
        text_upper = text.upper()
        
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text_upper)
            if matches:
                try:
                    if len(matches[0]) == 3:
                        if len(matches[0][2]) == 2:  # YY format
                            year = int(matches[0][2])
                            if year < 50:
                                year += 2000
                            else:
                                year += 1900
                        else:
                            year = int(matches[0][2])
                        
                        month = int(matches[0][0])
                        day = int(matches[0][1])
                        
                        # Handle different date formats
                        if month > 12:  # DD/MM format
                            month, day = day, month
                        
                        return datetime(year, month, day)
                except (ValueError, IndexError):
                    continue
        
        return None

    def parse_amount(self, text: str) -> Optional[float]:
        """Parse amount from text"""
        text_upper = text.upper()
        
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text_upper)
            if matches:
                try:
                    amount_str = matches[0].replace(',', '')
                    return float(amount_str)
                except ValueError:
                    continue
        
        return None

    def parse_merchant(self, text: str) -> Optional[str]:
        """Parse merchant name from text"""
        text_upper = text.upper()
        
        for pattern in self.merchant_patterns:
            matches = re.findall(pattern, text_upper)
            if matches:
                merchant = matches[0].strip()
                if len(merchant) > 2:  # Filter out very short matches
                    return merchant
        
        return None

    def extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items from receipt text"""
        lines = text.split('\n')
        items = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for patterns like "Item Name $XX.XX"
            item_match = re.search(r'^([^$]+?)\s+\$?\s*(\d+\.\d{2})$', line)
            if item_match:
                item_name = item_match.group(1).strip()
                item_price = float(item_match.group(2))
                
                if len(item_name) > 2 and item_price > 0:
                    items.append({
                        'name': item_name,
                        'price': item_price
                    })
        
        return items

    def process_receipt(self, receipt_data: Dict) -> Dict:
        """Process a receipt and extract real data"""
        try:
            receipt_id = receipt_data.get('_id')
            r2_urls = receipt_data.get('r2_urls', [])
            
            if not r2_urls:
                logger.warning(f"No R2 URLs found for receipt {receipt_id}")
                return receipt_data
            
            # Download and process the first attachment
            r2_url = r2_urls[0]
            file_content = self.download_from_r2(r2_url)
            
            if not file_content:
                logger.warning(f"Failed to download content for receipt {receipt_id}")
                return receipt_data
            
            # Extract text based on file type
            filename = receipt_data.get('attachments', [{}])[0].get('filename', '').lower()
            
            if filename.endswith('.pdf'):
                text = self.extract_text_from_pdf(file_content)
            elif filename.endswith(('.jpg', '.jpeg', '.png', '.tiff')):
                text = self.extract_text_from_image(file_content)
            else:
                logger.warning(f"Unsupported file type: {filename}")
                return receipt_data
            
            if not text:
                logger.warning(f"No text extracted from receipt {receipt_id}")
                return receipt_data
            
            # Extract real receipt data
            extracted_data = {
                'ocr_text': text,
                'ocr_processed': True,
                'ocr_confidence': 0.8
            }
            
            # Parse date
            receipt_date = self.parse_date(text)
            if receipt_date:
                extracted_data['receipt_date'] = receipt_date.isoformat()
                extracted_data['date_source'] = 'ocr'
            
            # Parse amount
            receipt_amount = self.parse_amount(text)
            if receipt_amount:
                extracted_data['receipt_amount'] = receipt_amount
                extracted_data['amount_source'] = 'ocr'
            
            # Parse merchant
            receipt_merchant = self.parse_merchant(text)
            if receipt_merchant:
                extracted_data['receipt_merchant'] = receipt_merchant
                extracted_data['merchant_source'] = 'ocr'
            
            # Extract line items
            line_items = self.extract_line_items(text)
            if line_items:
                extracted_data['line_items'] = line_items
            
            # Update receipt data
            receipt_data.update(extracted_data)
            
            # Convert ObjectId to string for JSON serialization
            if '_id' in receipt_data and hasattr(receipt_data['_id'], '__str__'):
                receipt_data['_id'] = str(receipt_data['_id'])
            
            logger.info(f"✅ OCR processed receipt {receipt_id}: "
                       f"merchant={receipt_merchant}, "
                       f"amount={receipt_amount}, "
                       f"date={receipt_date}")
            
            return receipt_data
            
        except Exception as e:
            logger.error(f"Error processing receipt {receipt_id}: {e}")
            return receipt_data

    def batch_process_receipts(self, receipts: List[Dict]) -> List[Dict]:
        """Process multiple receipts in batch"""
        processed_receipts = []
        
        for receipt in receipts:
            processed = self.process_receipt(receipt)
            processed_receipts.append(processed)
        
        return processed_receipts 
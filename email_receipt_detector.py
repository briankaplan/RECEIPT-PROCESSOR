"""
Advanced Email Receipt Detection & Download System
Automatically finds receipts in emails and extracts from links
"""

import os
import re
import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urljoin
from bs4 import BeautifulSoup
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import tempfile

logger = logging.getLogger(__name__)

@dataclass
class EmailReceipt:
    """Detected receipt in email"""
    email_subject: str
    email_from: str
    email_date: datetime
    receipt_type: str  # "attachment", "link", "embedded"
    download_url: Optional[str] = None
    attachment_name: Optional[str] = None
    confidence: float = 0.0
    merchant_detected: Optional[str] = None
    amount_detected: Optional[float] = None
    receipt_data: Optional[bytes] = None

class EmailReceiptDetector:
    """
    Advanced email receipt detection system
    
    Features:
    1. Scans emails for receipt indicators
    2. Extracts receipt download links from major retailers
    3. Handles attachments automatically
    4. Understands different receipt formats (PDF, images, HTML)
    5. Learns from merchant patterns
    """
    
    def __init__(self):
        self.receipt_patterns = self._initialize_patterns()
        self.merchant_patterns = self._load_merchant_patterns()
        
        # Email connection settings
        self.gmail_settings = {
            'server': 'imap.gmail.com',
            'port': 993,
            'use_ssl': True
        }
        
        logger.info("📧 Email Receipt Detector initialized")
    
    def _initialize_patterns(self) -> Dict:
        """Initialize receipt detection patterns"""
        return {
            "subject_patterns": [
                r"receipt",
                r"invoice", 
                r"purchase.*confirmation",
                r"order.*confirmation",
                r"payment.*confirmation",
                r"transaction.*complete",
                r"your.*order",
                r"billing.*statement",
                r"expense.*report"
            ],
            "sender_patterns": [
                r".*receipt.*",
                r".*billing.*",
                r".*order.*", 
                r".*payment.*",
                r".*invoice.*",
                r"noreply.*",
                r".*support.*"
            ],
            "content_patterns": [
                r"view.*receipt",
                r"download.*receipt",
                r"receipt.*available",
                r"view.*invoice", 
                r"download.*invoice",
                r"order.*summary",
                r"transaction.*details",
                r"payment.*summary"
            ],
            "link_patterns": [
                r"href=['\"]([^'\"]*receipt[^'\"]*)['\"]",
                r"href=['\"]([^'\"]*invoice[^'\"]*)['\"]",
                r"href=['\"]([^'\"]*order[^'\"]*)['\"]",
                r"href=['\"]([^'\"]*billing[^'\"]*)['\"]"
            ],
            "amount_patterns": [
                r"\$(\d+(?:\.\d{2})?)",
                r"total:?\s*\$?(\d+(?:\.\d{2})?)",
                r"amount:?\s*\$?(\d+(?:\.\d{2})?)",
                r"charge:?\s*\$?(\d+(?:\.\d{2})?)"
            ]
        }
    
    def _load_merchant_patterns(self) -> Dict:
        """Load known merchant receipt patterns"""
        return {
            "amazon": {
                "domains": ["amazon.com", "amazon.ca"],
                "subject_contains": ["your order", "amazon.com order"],
                "link_patterns": [r"order-details", r"your-account/order-history"],
                "receipt_class": "AmazonReceiptExtractor"
            },
            "apple": {
                "domains": ["apple.com"],
                "subject_contains": ["your receipt from apple"],
                "link_patterns": [r"reportaproblem.apple.com", r"finance-app.itunes.apple.com"],
                "receipt_class": "AppleReceiptExtractor"
            },
            "uber": {
                "domains": ["uber.com"],
                "subject_contains": ["trip receipt", "your uber receipt"],
                "link_patterns": [r"riders.uber.com"],
                "receipt_class": "UberReceiptExtractor"
            },
            "lyft": {
                "domains": ["lyft.com"],
                "subject_contains": ["ride receipt", "your lyft receipt"],
                "link_patterns": [r"lyft.com/ride"],
                "receipt_class": "LyftReceiptExtractor"
            },
            "airbnb": {
                "domains": ["airbnb.com"],
                "subject_contains": ["receipt", "confirmation"],
                "link_patterns": [r"airbnb.com/reservation"],
                "receipt_class": "AirbnbReceiptExtractor"
            },
            "expensify": {
                "domains": ["expensify.com"],
                "subject_contains": ["expense report", "receipt"],
                "link_patterns": [r"expensify.com"],
                "receipt_class": "ExpensifyReceiptExtractor"
            }
        }
    
    def scan_emails_for_receipts(self, email_account: str, password: str, 
                                days_back: int = 30) -> List[EmailReceipt]:
        """
        Scan Gmail account for receipt emails
        """
        receipts_found = []
        
        try:
            # Connect to Gmail
            mail = imaplib.IMAP4_SSL(self.gmail_settings['server'], self.gmail_settings['port'])
            mail.login(email_account, password)
            mail.select('inbox')
            
            # Search for recent emails with receipt indicators
            since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            
            # Search patterns for receipts
            search_terms = [
                f'(SINCE "{since_date}" SUBJECT "receipt")',
                f'(SINCE "{since_date}" SUBJECT "invoice")', 
                f'(SINCE "{since_date}" SUBJECT "order confirmation")',
                f'(SINCE "{since_date}" SUBJECT "purchase")',
                f'(SINCE "{since_date}" FROM "amazon")',
                f'(SINCE "{since_date}" FROM "apple")',
                f'(SINCE "{since_date}" FROM "uber")',
                f'(SINCE "{since_date}" FROM "airbnb")'
            ]
            
            email_ids = set()
            for search_term in search_terms:
                try:
                    _, messages = mail.search(None, search_term)
                    email_ids.update(messages[0].split())
                except Exception as e:
                    logger.debug(f"Search term failed: {search_term} - {e}")
            
            logger.info(f"📧 Found {len(email_ids)} potential receipt emails")
            
            # Process each email
            for email_id in list(email_ids)[:50]:  # Limit to 50 most recent
                try:
                    receipt = self._process_email(mail, email_id)
                    if receipt:
                        receipts_found.append(receipt)
                except Exception as e:
                    logger.error(f"Failed to process email {email_id}: {e}")
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            logger.error(f"Gmail scanning failed: {e}")
        
        return receipts_found
    
    def _process_email(self, mail, email_id: str) -> Optional[EmailReceipt]:
        """Process individual email for receipt detection"""
        try:
            _, msg_data = mail.fetch(email_id, '(RFC822)')
            email_message = email.message_from_bytes(msg_data[0][1])
            
            # Extract email metadata
            subject = self._decode_header(email_message['Subject'])
            from_addr = self._decode_header(email_message['From'])
            date_str = email_message['Date']
            email_date = email.utils.parsedate_to_datetime(date_str)
            
            # Check if this looks like a receipt
            receipt_confidence = self._calculate_receipt_confidence(subject, from_addr)
            
            if receipt_confidence < 0.3:
                return None
            
            logger.info(f"📧 Processing potential receipt: {subject[:50]}...")
            
            # Extract email content
            email_content = self._extract_email_content(email_message)
            
            # Detect merchant and amount
            merchant = self._detect_merchant(subject, from_addr, email_content)
            amount = self._detect_amount(email_content)
            
            # Check for attachments
            attachments = self._extract_attachments(email_message)
            if attachments:
                return EmailReceipt(
                    email_subject=subject,
                    email_from=from_addr,
                    email_date=email_date,
                    receipt_type="attachment",
                    attachment_name=attachments[0]['name'],
                    confidence=receipt_confidence + 0.2,
                    merchant_detected=merchant,
                    amount_detected=amount,
                    receipt_data=attachments[0]['data']
                )
            
            # Look for receipt links
            receipt_links = self._extract_receipt_links(email_content, from_addr)
            if receipt_links:
                return EmailReceipt(
                    email_subject=subject,
                    email_from=from_addr,
                    email_date=email_date,
                    receipt_type="link",
                    download_url=receipt_links[0],
                    confidence=receipt_confidence + 0.1,
                    merchant_detected=merchant,
                    amount_detected=amount
                )
            
            # Check for embedded receipt data
            if self._has_embedded_receipt(email_content):
                return EmailReceipt(
                    email_subject=subject,
                    email_from=from_addr,
                    email_date=email_date,
                    receipt_type="embedded",
                    confidence=receipt_confidence,
                    merchant_detected=merchant,
                    amount_detected=amount,
                    receipt_data=email_content.encode('utf-8')
                )
            
        except Exception as e:
            logger.error(f"Email processing failed: {e}")
        
        return None
    
    def download_receipt_from_link(self, receipt_url: str, merchant: str = None) -> Optional[bytes]:
        """
        Download receipt from URL with merchant-specific handling
        """
        try:
            # Determine merchant-specific extractor
            if merchant:
                merchant_config = self.merchant_patterns.get(merchant.lower())
                if merchant_config:
                    return self._extract_with_merchant_handler(receipt_url, merchant_config)
            
            # Generic receipt download
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(receipt_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                
                if 'pdf' in content_type:
                    logger.info(f"📄 Downloaded PDF receipt from {receipt_url}")
                    return response.content
                elif 'image' in content_type:
                    logger.info(f"🖼️ Downloaded image receipt from {receipt_url}")
                    return response.content
                elif 'html' in content_type:
                    # Extract receipt from HTML page
                    return self._extract_receipt_from_html(response.text, receipt_url)
                
        except Exception as e:
            logger.error(f"Receipt download failed from {receipt_url}: {e}")
        
        return None
    
    def _calculate_receipt_confidence(self, subject: str, from_addr: str) -> float:
        """Calculate confidence that email contains a receipt"""
        confidence = 0.0
        
        subject_lower = subject.lower() if subject else ""
        from_lower = from_addr.lower() if from_addr else ""
        
        # Check subject patterns
        for pattern in self.receipt_patterns["subject_patterns"]:
            if re.search(pattern, subject_lower):
                confidence += 0.3
        
        # Check sender patterns
        for pattern in self.receipt_patterns["sender_patterns"]:
            if re.search(pattern, from_lower):
                confidence += 0.2
        
        # Known merchant senders
        known_merchants = ["amazon", "apple", "uber", "lyft", "airbnb", "expensify"]
        for merchant in known_merchants:
            if merchant in from_lower:
                confidence += 0.4
                break
        
        return min(confidence, 1.0)
    
    def _detect_merchant(self, subject: str, from_addr: str, content: str) -> Optional[str]:
        """Detect merchant from email"""
        combined_text = f"{subject} {from_addr} {content}".lower()
        
        # Check known merchants
        for merchant, config in self.merchant_patterns.items():
            for domain in config["domains"]:
                if domain in combined_text:
                    return merchant
            
            for subject_pattern in config["subject_contains"]:
                if subject_pattern in combined_text:
                    return merchant
        
        # Extract merchant from email domain
        if "@" in from_addr:
            domain = from_addr.split("@")[1].lower()
            # Clean domain (remove common email service indicators)
            domain = re.sub(r'\.(com|net|org|co).*', '', domain)
            domain = re.sub(r'^(mail|email|noreply|no-reply)\.', '', domain)
            return domain
        
        return None
    
    def _detect_amount(self, content: str) -> Optional[float]:
        """Detect transaction amount from email content"""
        for pattern in self.receipt_patterns["amount_patterns"]:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    return float(amount_str)
                except ValueError:
                    continue
        return None
    
    def _extract_receipt_links(self, content: str, from_addr: str) -> List[str]:
        """Extract receipt download links from email content"""
        links = []
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                link_text = link.get_text().lower()
                
                # Check if link looks like a receipt link
                receipt_indicators = [
                    "receipt", "invoice", "order", "billing", "statement",
                    "view", "download", "details"
                ]
                
                if any(indicator in link_text for indicator in receipt_indicators):
                    if href.startswith('http'):
                        links.append(href)
                    elif href.startswith('/'):
                        # Relative URL - need to construct full URL
                        domain = self._extract_domain_from_email(from_addr)
                        if domain:
                            links.append(f"https://{domain}{href}")
            
        except Exception as e:
            logger.error(f"Link extraction failed: {e}")
        
        return links[:3]  # Return top 3 links
    
    def _has_embedded_receipt(self, content: str) -> bool:
        """Check if email has embedded receipt data"""
        receipt_indicators = [
            "order summary", "transaction details", "payment summary",
            "subtotal", "tax", "total amount", "order total"
        ]
        
        content_lower = content.lower()
        indicator_count = sum(1 for indicator in receipt_indicators 
                            if indicator in content_lower)
        
        return indicator_count >= 2
    
    def _extract_attachments(self, email_message) -> List[Dict]:
        """Extract attachments from email"""
        attachments = []
        
        for part in email_message.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    # Check if attachment looks like a receipt
                    if any(ext in filename.lower() for ext in ['.pdf', '.png', '.jpg', '.jpeg']):
                        try:
                            attachment_data = part.get_payload(decode=True)
                            attachments.append({
                                'name': filename,
                                'data': attachment_data
                            })
                        except Exception as e:
                            logger.error(f"Attachment extraction failed: {e}")
        
        return attachments
    
    def _extract_email_content(self, email_message) -> str:
        """Extract text content from email"""
        content = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/html":
                    try:
                        content = part.get_payload(decode=True).decode('utf-8')
                        break
                    except:
                        pass
                elif part.get_content_type() == "text/plain":
                    try:
                        content = part.get_payload(decode=True).decode('utf-8')
                    except:
                        pass
        else:
            try:
                content = email_message.get_payload(decode=True).decode('utf-8')
            except:
                pass
        
        return content
    
    def _decode_header(self, header) -> str:
        """Decode email header"""
        if not header:
            return ""
        
        try:
            decoded = email.header.decode_header(header)
            return ''.join([
                text.decode(encoding or 'utf-8') if isinstance(text, bytes) else text
                for text, encoding in decoded
            ])
        except:
            return str(header)
    
    def _extract_domain_from_email(self, email_addr: str) -> Optional[str]:
        """Extract domain from email address"""
        if "@" in email_addr:
            return email_addr.split("@")[1].lower()
        return None
    
    def _extract_with_merchant_handler(self, url: str, merchant_config: Dict) -> Optional[bytes]:
        """Use merchant-specific extraction logic"""
        # This would implement specific logic for each merchant
        # For now, fall back to generic download
        return self.download_receipt_from_link(url)
    
    def _extract_receipt_from_html(self, html_content: str, url: str) -> Optional[bytes]:
        """Extract receipt data from HTML page"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for receipt-specific content
            receipt_sections = soup.find_all(['div', 'table'], 
                                           class_=re.compile(r'.*receipt.*|.*invoice.*|.*order.*', re.I))
            
            if receipt_sections:
                # Convert relevant sections to clean HTML/text
                receipt_html = str(receipt_sections[0])
                return receipt_html.encode('utf-8')
            
        except Exception as e:
            logger.error(f"HTML receipt extraction failed: {e}")
        
        return None

def main():
    """Test the email receipt detector"""
    detector = EmailReceiptDetector()
    
    # Test with sample email data
    print("🧪 Email Receipt Detector initialized")
    
    # In real usage, you would call:
    # receipts = detector.scan_emails_for_receipts("your_email@gmail.com", "your_password")
    # print(f"Found {len(receipts)} receipts")

if __name__ == "__main__":
    main() 
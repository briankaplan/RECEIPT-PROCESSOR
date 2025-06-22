#!/usr/bin/env python3
"""
URL extraction and receipt download system
Finds receipt URLs in emails and downloads receipt images/PDFs
"""

import os
import re
import logging
import requests
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Optional
import mimetypes
from datetime import datetime

logger = logging.getLogger(__name__)

class URLExtractor:
    """Extract and download receipts from URLs found in emails"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Common receipt URL patterns
        self.receipt_patterns = [
            r'https?://[^\s]+receipt[^\s]*',
            r'https?://[^\s]+invoice[^\s]*',
            r'https?://[^\s]+bill[^\s]*',
            r'https?://[^\s]+purchase[^\s]*',
            r'https?://[^\s]+order[^\s]*',
            r'https?://[^\s]+transaction[^\s]*',
            r'https?://[^\s]+\.pdf[^\s]*',
            r'https?://receipts\.[^\s]+',
            r'https?://[^\s]*receipt[^\s]*\.pdf',
            r'https?://[^\s]*invoice[^\s]*\.pdf'
        ]
        
        # Receipt hosting domains
        self.receipt_domains = [
            'receipts.uber.com',
            'receipts.lyft.com',
            'account.venmo.com',
            'paypal.com',
            'square.com',
            'stripe.com',
            'quickbooks.com',
            'freshbooks.com',
            'invoicely.com',
            'wave.com',
            'xero.com'
        ]
    
    def extract_urls_from_email(self, email_content: str) -> List[str]:
        """Extract potential receipt URLs from email content"""
        urls = []
        
        # Find all URLs in email content
        url_pattern = r'https?://[^\s<>"\']+[^\s<>"\'.,)]'
        found_urls = re.findall(url_pattern, email_content, re.IGNORECASE)
        
        for url in found_urls:
            if self._is_potential_receipt_url(url):
                urls.append(url)
        
        logger.info(f"Found {len(urls)} potential receipt URLs")
        return urls
    
    def _is_potential_receipt_url(self, url: str) -> bool:
        """Check if URL is likely to contain a receipt"""
        url_lower = url.lower()
        
        # Check domain patterns
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if any(receipt_domain in domain for receipt_domain in self.receipt_domains):
            return True
        
        # Check URL path patterns
        receipt_keywords = [
            'receipt', 'invoice', 'bill', 'purchase', 'order', 
            'transaction', 'payment', 'confirmation', 'summary'
        ]
        
        if any(keyword in url_lower for keyword in receipt_keywords):
            return True
        
        # Check file extensions
        if url_lower.endswith(('.pdf', '.png', '.jpg', '.jpeg')):
            return True
        
        return False
    
    def download_receipt_from_url(self, url: str, save_dir: str = 'downloads') -> Optional[Dict]:
        """Download receipt from URL and return file info"""
        try:
            os.makedirs(save_dir, exist_ok=True)
            
            # Make request with proper headers
            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Determine file extension from content type or URL
            content_type = response.headers.get('content-type', '').lower()
            extension = self._get_file_extension(url, content_type)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"url_receipt_{timestamp}{extension}"
            filepath = os.path.join(save_dir, filename)
            
            # Save file
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            file_info = {
                'url': url,
                'filepath': filepath,
                'filename': filename,
                'content_type': content_type,
                'size': len(response.content),
                'downloaded_at': datetime.utcnow(),
                'source_type': 'url_download'
            }
            
            logger.info(f"Downloaded receipt from {url} to {filepath}")
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to download receipt from {url}: {e}")
            return None
    
    def _get_file_extension(self, url: str, content_type: str) -> str:
        """Determine file extension from URL or content type"""
        # First try to get extension from URL
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        if path.endswith('.pdf'):
            return '.pdf'
        elif path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            return os.path.splitext(path)[1]
        
        # Try to determine from content type
        if 'pdf' in content_type:
            return '.pdf'
        elif 'image' in content_type:
            if 'jpeg' in content_type or 'jpg' in content_type:
                return '.jpg'
            elif 'png' in content_type:
                return '.png'
            elif 'gif' in content_type:
                return '.gif'
            else:
                return '.jpg'  # Default for images
        
        # Default to PDF for unknown types (many receipts are PDFs)
        return '.pdf'
    
    def extract_and_download_from_email(self, email_content: str, email_id: str, save_dir: str = 'downloads') -> List[Dict]:
        """Extract URLs from email and download all receipt files"""
        downloaded_files = []
        
        urls = self.extract_urls_from_email(email_content)
        
        for url in urls:
            file_info = self.download_receipt_from_url(url, save_dir)
            if file_info:
                file_info['email_id'] = email_id
                file_info['extracted_from_email'] = True
                downloaded_files.append(file_info)
        
        logger.info(f"Downloaded {len(downloaded_files)} receipts from URLs in email {email_id}")
        return downloaded_files
    
    def process_receipt_urls(self, urls: List[str], receipt_processor) -> List[Dict]:
        """Download and process receipts from a list of URLs"""
        processed_receipts = []
        
        for url in urls:
            try:
                # Download file
                file_info = self.download_receipt_from_url(url)
                
                if file_info:
                    # Process the receipt
                    receipt_data = receipt_processor.extract_receipt_data(file_info['filepath'])
                    
                    if receipt_data:
                        # Add URL metadata
                        receipt_data['source_type'] = 'url_download'
                        receipt_data['source_url'] = url
                        receipt_data['downloaded_at'] = file_info['downloaded_at']
                        receipt_data['content_type'] = file_info['content_type']
                        processed_receipts.append(receipt_data)
                    
                    # Clean up downloaded file
                    if os.path.exists(file_info['filepath']):
                        os.remove(file_info['filepath'])
                        
            except Exception as e:
                logger.error(f"Failed to process receipt URL {url}: {e}")
        
        logger.info(f"Processed {len(processed_receipts)} receipts from URLs")
        return processed_receipts
    
    def scan_email_for_screenshots(self, email_content: str) -> List[str]:
        """Find screenshot URLs or image attachments that might be receipts"""
        screenshot_patterns = [
            r'https?://[^\s]+screenshot[^\s]*',
            r'https?://[^\s]+capture[^\s]*',
            r'https?://[^\s]+image[^\s]*',
            r'https?://[^\s]+photo[^\s]*',
            r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+',  # Base64 images
        ]
        
        screenshot_urls = []
        for pattern in screenshot_patterns:
            matches = re.findall(pattern, email_content, re.IGNORECASE)
            screenshot_urls.extend(matches)
        
        return screenshot_urls
    
    def get_stats(self) -> Dict:
        """Get URL extractor statistics"""
        return {
            'receipt_patterns_count': len(self.receipt_patterns),
            'receipt_domains_count': len(self.receipt_domains),
            'session_active': self.session is not None
        }
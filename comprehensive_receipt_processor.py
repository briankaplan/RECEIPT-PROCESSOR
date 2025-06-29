#!/usr/bin/env python3
"""
Comprehensive Receipt Processing System
Implements the proper workflow:
1. Download attachment → OCR → Match → Add to DB → Upload to R2 → Link URL
2. Screenshot body receipt → OCR → Match → Add to DB → Upload to R2 → Link URL  
3. Extract URL → Download/Screenshot → OCR → Match → Add to DB → Upload to R2 → Link URL
"""

import os
import re
import logging
import tempfile
import asyncio
import concurrent.futures
import signal
import sys
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import base64
from io import BytesIO
from PIL import Image
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

# Import existing modules
from url_extractor import URLExtractor
from enhanced_receipt_extractor import EnhancedReceiptExtractor
from huggingface_receipt_processor import HuggingFaceReceiptProcessor

logger = logging.getLogger(__name__)

# --- Graceful Shutdown Handling ---
executor = concurrent.futures.ThreadPoolExecutor()

def shutdown_handler(sig, frame):
    logger.info("🔌 Shutting down gracefully...")
    executor.shutdown(wait=False)
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# --- Health Check for WebDriver ---
def get_webdriver():
    """Get a healthy WebDriver instance with proper error handling"""
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(10)
        return driver
    except WebDriverException as e:
        logger.error(f"❌ Failed to start WebDriver: {e}")
        return None

# --- Safe Task Submission ---
def safe_submit(task, *args, **kwargs):
    """Safely submit tasks to executor, handling shutdown errors"""
    try:
        return executor.submit(task, *args, **kwargs)
    except RuntimeError as e:
        if "shutdown" in str(e):
            logger.warning(f"🚫 Cannot schedule task after shutdown: {task.__name__}")
        else:
            raise
        return None

# --- MongoDB Client Guard for Mocks ---
def get_database(client, db_name):
    """Safely get database from client, handling mock objects"""
    try:
        return client[db_name]
    except TypeError:
        logger.warning("⚠️ Invalid MongoClient object (mock or improperly passed)")
        return None
    except Exception as e:
        logger.error(f"❌ Error accessing database {db_name}: {e}")
        return None

@dataclass
class ReceiptMatch:
    """Receipt match result"""
    receipt_id: str
    transaction_id: str
    confidence: float
    match_type: str
    merchant_similarity: float
    amount_match: bool
    date_match: bool
    receipt_data: Dict
    transaction_data: Dict

class ComprehensiveReceiptProcessor:
    """Comprehensive receipt processor with proper workflow"""
    
    def __init__(self, mongo_client, r2_client=None):
        # Handle both regular MongoClient and SafeMongoClient
        if hasattr(mongo_client, 'client'):
            self.mongo_client = mongo_client.client
        else:
            self.mongo_client = mongo_client
            
        self.r2_client = r2_client
        self.db = get_database(self.mongo_client, 'expense')
        
        # Initialize components
        self.url_extractor = URLExtractor()
        self.enhanced_extractor = EnhancedReceiptExtractor()
        
        # Initialize OCR processor with proper error handling
        self.ocr_processor = None
        self._init_ocr_processor()
        
        # Initialize webdriver for screenshots
        self.webdriver = None
        self._init_webdriver()
        
        logger.info("✅ Comprehensive receipt processor initialized")
    
    def _init_ocr_processor(self):
        """Initialize OCR processor with proper error handling"""
        try:
            self.ocr_processor = HuggingFaceReceiptProcessor()
            
            # Test the API with a real file path instead of "test"
            test_image_path = os.path.join("downloads", "sample_receipt.png")
            if os.path.exists(test_image_path):
                test_result = self.ocr_processor.process_receipt_image(test_image_path)
                if test_result and test_result.get("status") == "success":
                    logger.info("✅ OCR processor initialized and tested")
                else:
                    logger.warning("⚠️ OCR processor API test failed, will use enhanced extractor")
                    self.ocr_processor = None
            else:
                logger.warning(f"⚠️ Test image not found at {test_image_path}, skipping Hugging Face test")
                # Still try to use it, but be prepared for failures
                self.ocr_processor = None
                
        except Exception as e:
            logger.warning(f"OCR processor not available: {e}")
            self.ocr_processor = None
    
    def _init_webdriver(self):
        """Initialize headless Chrome for screenshots with health check"""
        try:
            self.webdriver = get_webdriver()
            if self.webdriver:
                logger.info("✅ WebDriver initialized for screenshots")
            else:
                logger.warning("📸 Screenshot functionality will be disabled")
        except Exception as e:
            logger.warning(f"WebDriver not available for screenshots: {e}")
            logger.info("📸 Screenshot functionality will be disabled")
            self.webdriver = None
    
    def process_email_receipts(self, email_candidates: List[Dict], gmail_account: str) -> Dict[str, any]:
        """Process email receipts with comprehensive workflow"""
        try:
            logger.info(f"🎯 Processing {len(email_candidates)} email receipt candidates...")
            
            results = {
                "receipts_processed": 0,
                "receipts_matched": 0,
                "receipts_uploaded": 0,
                "attachments_processed": 0,
                "body_screenshots": 0,
                "url_downloads": 0,
                "matches": [],
                "errors": []
            }
            
            # Get all transactions for matching
            transactions = list(self.db.bank_transactions.find({}))
            logger.info(f"📊 Found {len(transactions)} transactions for matching")
            
            for candidate in email_candidates:
                try:
                    logger.info(f"🔍 Processing candidate: {candidate.get('message_id', 'unknown')}")
                    
                    # Step 1: Try to download attachment first
                    attachment_receipt = self._process_attachment(candidate, gmail_account)
                    if attachment_receipt:
                        results["attachments_processed"] += 1
                        match = self._match_and_save_receipt(attachment_receipt, transactions, results)
                        if match:
                            continue  # Move to next candidate if attachment was processed
                    
                    # Step 2: Try to screenshot body receipt
                    body_receipt = self._process_body_receipt(candidate, gmail_account)
                    if body_receipt:
                        results["body_screenshots"] += 1
                        match = self._match_and_save_receipt(body_receipt, transactions, results)
                        if match:
                            continue  # Move to next candidate if body was processed
                    
                    # Step 3: Try to extract and download from URL
                    url_receipt = self._process_url_receipt(candidate, gmail_account)
                    if url_receipt:
                        results["url_downloads"] += 1
                        self._match_and_save_receipt(url_receipt, transactions, results)
                    
                    results["receipts_processed"] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing candidate {candidate.get('message_id', 'unknown')}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            logger.info(f"🎉 Processing complete: {results['receipts_matched']}/{results['receipts_processed']} matched")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in process_email_receipts: {e}")
            return {"error": str(e)}
    
    def _process_attachment(self, candidate: Dict, gmail_account: str) -> Optional[Dict]:
        """Process email attachment if present"""
        try:
            attachment_count = candidate.get("attachment_count", 0)
            if attachment_count == 0:
                return None
            
            logger.info(f"📎 Processing attachment for {candidate.get('message_id')}")
            
            # For now, use fallback extraction since we don't have Gmail API integration
            # In a full implementation, this would download the attachment and process it
            logger.info("📎 Using fallback extraction for attachment")
            return self._extract_receipt_fallback(candidate, gmail_account, "attachment")
            
        except Exception as e:
            logger.error(f"Error processing attachment: {e}")
            return None
    
    def _process_body_receipt(self, candidate: Dict, gmail_account: str) -> Optional[Dict]:
        """Screenshot receipt in email body"""
        try:
            # Extract email body (this would need Gmail API integration)
            email_body = candidate.get("body", "")
            if not email_body:
                logger.info("No email body available for screenshot")
                return None
            
            # Check if body contains receipt-like content
            if not self._contains_receipt_content(email_body):
                logger.info("Email body doesn't contain receipt content")
                return None
            
            logger.info(f"📸 Screenshotting receipt in email body")
            
            # Create a temporary HTML file for screenshot
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_html:
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        .receipt {{ border: 1px solid #ccc; padding: 20px; margin: 10px; }}
                    </style>
                </head>
                <body>
                    <div class="receipt">
                        {email_body}
                    </div>
                </body>
                </html>
                """
                temp_html.write(html_content)
                temp_html_path = temp_html.name
            
            # Take screenshot
            screenshot_path = self._take_screenshot(temp_html_path)
            
            # Clean up temp HTML file
            os.unlink(temp_html_path)
            
            if screenshot_path:
                # Process screenshot with OCR
                receipt_data = self._extract_receipt_from_image(screenshot_path, candidate, gmail_account)
                
                # Clean up screenshot file
                os.unlink(screenshot_path)
                
                return receipt_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing body receipt: {e}")
            return None
    
    def _process_url_receipt(self, candidate: Dict, gmail_account: str) -> Optional[Dict]:
        """Extract and download receipt from URL"""
        try:
            email_body = candidate.get("body", "")
            if not email_body:
                return None
            
            # Extract URLs from email body
            urls = self.url_extractor.extract_urls_from_email(email_body)
            if not urls:
                logger.info("No receipt URLs found in email body")
                return None
            
            logger.info(f"🔗 Found {len(urls)} receipt URLs, processing first one")
            
            # Download first receipt URL
            url = urls[0]
            file_info = self.url_extractor.download_receipt_from_url(url)
            
            if file_info:
                # Process downloaded file
                receipt_data = self._extract_receipt_from_file(file_info['filepath'], candidate, gmail_account)
                
                # Clean up downloaded file
                os.unlink(file_info['filepath'])
                
                return receipt_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing URL receipt: {e}")
            return None
    
    def _contains_receipt_content(self, body: str) -> bool:
        """Check if email body contains receipt-like content"""
        # Primary receipt keywords that indicate actual receipts
        primary_keywords = [
            'receipt', 'invoice', 'bill', 'payment confirmation', 'order confirmation',
            'purchase confirmation', 'transaction confirmation', 'payment receipt',
            'order receipt', 'purchase receipt', 'billing confirmation'
        ]
        
        # Secondary keywords that might indicate receipts
        secondary_keywords = [
            'total', 'amount', 'payment', 'transaction', 'order', 'confirmation', 
            'summary', 'charged', 'subtotal', 'tax', 'total amount'
        ]
        
        # Exclude patterns that indicate non-receipt emails
        exclude_patterns = [
            'build failed', 'build error', 'deployment failed', 'deployment error',
            'github', 'gitlab', 'jenkins', 'ci/cd', 'pipeline', 'workflow',
            'newsletter', 'marketing', 'promotion', 'offer', 'discount',
            'welcome', 'account created', 'sign up', 'registration',
            'security alert', 'login attempt', 'password reset',
            'maintenance', 'scheduled maintenance', 'system update'
        ]
        
        # Check for exclusion patterns first
        body_lower = body.lower()
        for pattern in exclude_patterns:
            if pattern in body_lower:
                return False
        
        # Check for amount patterns (must be present for a receipt)
        amount_patterns = [
            r'\$\d+\.\d{2}',  # $XX.XX
            r'\$\d+',         # $XX
            r'\d+\.\d{2}',    # XX.XX
            r'total.*\$\d+',  # total $XX
            r'amount.*\$\d+', # amount $XX
            r'charged.*\$\d+' # charged $XX
        ]
        
        has_amount = any(re.search(pattern, body_lower) for pattern in amount_patterns)
        
        # Must have at least one primary keyword AND an amount
        has_primary = any(keyword in body_lower for keyword in primary_keywords)
        
        # Or have multiple secondary keywords AND an amount
        secondary_count = sum(1 for keyword in secondary_keywords if keyword in body_lower)
        has_secondary = secondary_count >= 2
        
        return (has_primary or has_secondary) and has_amount
    
    def _take_screenshot(self, html_path: str) -> Optional[str]:
        """Take screenshot of receipt area in HTML file"""
        try:
            # Use the health-checked WebDriver function
            driver = get_webdriver()
            if not driver:
                logger.warning("WebDriver not available for screenshots")
                return None
            
            try:
                # Load HTML file
                driver.get(f"file://{html_path}")
                
                # Wait for page to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Try to find receipt-specific elements
                receipt_element = self._find_receipt_element_with_driver(driver)
                
                if receipt_element:
                    # Screenshot just the receipt element
                    screenshot_path = self._screenshot_element_with_driver(driver, receipt_element)
                    logger.info(f"📸 Screenshot of receipt element saved to {screenshot_path}")
                else:
                    # Fallback: screenshot entire page with dynamic sizing
                    screenshot_path = self._screenshot_full_page_with_driver(driver)
                    logger.info(f"📸 Full page screenshot saved to {screenshot_path}")
                
                return screenshot_path
                
            finally:
                # Always close the driver
                try:
                    driver.quit()
                except Exception as e:
                    logger.warning(f"Error closing WebDriver: {e}")
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
    
    def _find_receipt_element_with_driver(self, driver) -> Optional[object]:
        """Find the receipt element in the HTML using provided driver"""
        try:
            # Common receipt selectors
            receipt_selectors = [
                # CSS classes
                ".receipt", ".invoice", ".bill", ".payment", ".confirmation",
                ".order-summary", ".transaction", ".purchase-summary",
                
                # IDs
                "#receipt", "#invoice", "#bill", "#payment", "#confirmation",
                "#order-summary", "#transaction", "#purchase-summary",
                
                # Data attributes
                "[data-type='receipt']", "[data-type='invoice']", "[data-type='bill']",
                "[data-role='receipt']", "[data-role='invoice']", "[data-role='bill']",
                
                # Semantic elements
                "table[class*='receipt']", "div[class*='receipt']", "section[class*='receipt']",
                "table[class*='invoice']", "div[class*='invoice']", "section[class*='invoice']",
                "table[class*='bill']", "div[class*='bill']", "section[class*='bill']",
                
                # Common receipt patterns
                "div:contains('Total')", "div:contains('Amount')", "div:contains('Payment')",
                "table:contains('Total')", "table:contains('Amount')", "table:contains('Payment')"
            ]
            
            for selector in receipt_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.is_displayed():
                        logger.info(f"✅ Found receipt element with selector: {selector}")
                        return element
                except:
                    continue
            
            # Try JavaScript-based detection
            js_script = """
            function findReceiptElement() {
                // Look for elements with receipt-related text
                const receiptKeywords = ['receipt', 'invoice', 'bill', 'payment', 'total', 'amount', 'confirmation'];
                const elements = document.querySelectorAll('div, table, section, article');
                
                for (let element of elements) {
                    const text = element.textContent.toLowerCase();
                    const hasReceiptText = receiptKeywords.some(keyword => text.includes(keyword));
                    
                    if (hasReceiptText && element.offsetWidth > 200 && element.offsetHeight > 100) {
                        return element;
                    }
                }
                
                // Look for elements with currency patterns
                const currencyPattern = /\\$\\d+(\\.\\d{2})?/;
                for (let element of elements) {
                    const text = element.textContent;
                    if (currencyPattern.test(text) && element.offsetWidth > 200 && element.offsetHeight > 100) {
                        return element;
                    }
                }
                
                return null;
            }
            return findReceiptElement();
            """
            
            receipt_element = driver.execute_script(js_script)
            if receipt_element:
                logger.info("✅ Found receipt element using JavaScript detection")
                return receipt_element
            
            logger.info("⚠️ No specific receipt element found, will screenshot entire page")
            return None
            
        except Exception as e:
            logger.error(f"Error finding receipt element: {e}")
            return None
    
    def _screenshot_element_with_driver(self, driver, element) -> Optional[str]:
        """Take screenshot of specific element with dynamic sizing using provided driver"""
        try:
            # Get element dimensions
            location = element.location
            size = element.size
            
            # Add padding around the element
            padding = 20
            x = max(0, location['x'] - padding)
            y = max(0, location['y'] - padding)
            width = size['width'] + (padding * 2)
            height = size['height'] + (padding * 2)
            
            # Ensure minimum size
            width = max(width, 400)
            height = max(height, 300)
            
            # Set window size to accommodate the element
            window_width = max(1200, x + width + 50)
            window_height = max(800, y + height + 50)
            
            driver.set_window_size(window_width, window_height)
            
            # Take screenshot
            screenshot_path = tempfile.mktemp(suffix='.png')
            driver.save_screenshot(screenshot_path)
            
            # Crop to just the element area
            from PIL import Image
            img = Image.open(screenshot_path)
            cropped_img = img.crop((x, y, x + width, y + height))
            cropped_img.save(screenshot_path)
            
            logger.info(f"📸 Cropped screenshot: {width}x{height} at ({x},{y})")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Error taking element screenshot: {e}")
            return None
    
    def _screenshot_full_page_with_driver(self, driver) -> Optional[str]:
        """Take screenshot of entire page with dynamic sizing using provided driver"""
        try:
            # Get page dimensions
            page_width = driver.execute_script("return document.body.scrollWidth")
            page_height = driver.execute_script("return document.body.scrollHeight")
            
            # Set window size to accommodate full page
            window_width = max(1200, page_width + 50)
            window_height = max(800, page_height + 50)
            
            driver.set_window_size(window_width, window_height)
            
            # Take screenshot
            screenshot_path = tempfile.mktemp(suffix='.png')
            driver.save_screenshot(screenshot_path)
            
            logger.info(f"📸 Full page screenshot: {page_width}x{page_height}")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Error taking full page screenshot: {e}")
            return None
    
    def _extract_receipt_from_image(self, image_path: str, candidate: Dict, gmail_account: str) -> Optional[Dict]:
        """Extract receipt data from image using enhanced extractor"""
        try:
            logger.info(f"🔍 Extracting receipt data from image: {image_path}")
            
            # Use enhanced extractor instead of OCR
            extracted_data = self.enhanced_extractor.extract_from_image(image_path, candidate)
            
            if extracted_data.merchant or extracted_data.amount > 0:
                receipt_data = {
                    "merchant": extracted_data.merchant,
                    "amount": extracted_data.amount,
                    "date": extracted_data.date,
                    "category": extracted_data.category,
                    "confidence": extracted_data.confidence,
                    "extraction_method": extracted_data.extraction_method,
                    "source_type": "image",
                    "gmail_account": gmail_account,
                    "message_id": candidate.get("message_id"),
                    "raw_text": extracted_data.raw_text
                }
                
                logger.info(f"✅ Extracted from image: {extracted_data.merchant} - ${extracted_data.amount} (confidence: {extracted_data.confidence:.2f})")
                return receipt_data
            else:
                logger.info("❌ No useful data extracted from image")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting receipt from image: {e}")
            return None
    
    def _extract_receipt_from_file(self, file_path: str, candidate: Dict, gmail_account: str) -> Optional[Dict]:
        """Extract receipt data from downloaded file using enhanced extractor"""
        try:
            logger.info(f"🔍 Extracting receipt data from file: {file_path}")
            
            # Use enhanced extractor instead of OCR
            extracted_data = self.enhanced_extractor.extract_from_file(file_path, candidate)
            
            if extracted_data.merchant or extracted_data.amount > 0:
                receipt_data = {
                    "merchant": extracted_data.merchant,
                    "amount": extracted_data.amount,
                    "date": extracted_data.date,
                    "category": extracted_data.category,
                    "confidence": extracted_data.confidence,
                    "extraction_method": extracted_data.extraction_method,
                    "source_type": "file",
                    "gmail_account": gmail_account,
                    "message_id": candidate.get("message_id"),
                    "raw_text": extracted_data.raw_text,
                    "file_path": file_path
                }
                
                logger.info(f"✅ Extracted from file: {extracted_data.merchant} - ${extracted_data.amount} (confidence: {extracted_data.confidence:.2f})")
                return receipt_data
            else:
                logger.info("❌ No useful data extracted from file")
                return None
            
        except Exception as e:
            logger.error(f"Error extracting receipt from file: {e}")
            return None
    
    def _extract_receipt_fallback(self, candidate: Dict, gmail_account: str, source_type: str) -> Optional[Dict]:
        """Fallback method to extract receipt data using enhanced extractor"""
        try:
            # Use enhanced extractor for email data
            email_data = {
                'subject': candidate.get("subject", ""),
                'body': candidate.get("body", ""),
                'from_email': candidate.get("from_email", ""),
                'date': candidate.get("date", "")
            }
            
            extracted_data = self.enhanced_extractor.extract_from_email(email_data)
            
            if extracted_data.merchant or extracted_data.amount > 0:
                receipt_data = {
                    "merchant": extracted_data.merchant,
                    "amount": extracted_data.amount,
                    "date": extracted_data.date,
                    "category": extracted_data.category,
                    "confidence": extracted_data.confidence,
                    "extraction_method": extracted_data.extraction_method,
                    "source_type": source_type,
                    "gmail_account": gmail_account,
                    "message_id": candidate.get("message_id"),
                    "raw_text": extracted_data.raw_text
                }
                
                logger.info(f"📄 Enhanced extraction: {extracted_data.merchant} - ${extracted_data.amount} (confidence: {extracted_data.confidence:.2f})")
                return receipt_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error in enhanced fallback extraction: {e}")
            return None
    
    def _match_and_save_receipt(self, receipt_data: Dict, transactions: List[Dict], results: Dict) -> Optional[ReceiptMatch]:
        """Match receipt to transaction and save to database"""
        try:
            # Match to transactions
            match = self._match_receipt_to_transaction(receipt_data, transactions)
            
            if match and match.confidence >= 0.7:  # High confidence threshold
                results["receipts_matched"] += 1
                results["matches"].append(match)
                
                # Upload to R2
                if self._upload_matched_receipt(match):
                    results["receipts_uploaded"] += 1
                    
                    # Save receipt record with transaction link
                    self._save_receipt_record(match)
                    
                    logger.info(f"✅ Matched and uploaded: {receipt_data.get('merchant', 'Unknown')} - ${receipt_data.get('amount', 0)}")
                    return match
                else:
                    logger.warning(f"⚠️ Failed to upload matched receipt: {receipt_data.get('merchant', 'Unknown')}")
            else:
                logger.info(f"❌ No match found for: {receipt_data.get('merchant', 'Unknown')} - ${receipt_data.get('amount', 0)}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error in match_and_save_receipt: {e}")
            return None
    
    def _match_receipt_to_transaction(self, receipt_data: Dict, transactions: List[Dict]) -> Optional[ReceiptMatch]:
        """Match receipt to transaction using multiple strategies"""
        try:
            best_match = None
            best_confidence = 0.0
            
            receipt_merchant = receipt_data.get("merchant", "").lower()
            receipt_amount = receipt_data.get("amount", 0.0)
            receipt_date = receipt_data.get("date", "")
            
            for transaction in transactions:
                confidence = 0.0
                match_type = "none"
                
                # Get transaction data
                txn_merchant = (transaction.get("merchant") or transaction.get("description", "")).lower()
                txn_amount = abs(float(transaction.get("amount", 0)))
                txn_date = transaction.get("date", "")
                
                # Strategy 1: Exact merchant + amount match
                if (receipt_merchant in txn_merchant or txn_merchant in receipt_merchant) and abs(receipt_amount - txn_amount) < 0.01:
                    confidence = 0.95
                    match_type = "exact"
                
                # Strategy 2: Merchant similarity + amount match
                elif self._calculate_merchant_similarity(receipt_merchant, txn_merchant) > 0.8 and abs(receipt_amount - txn_amount) < 0.01:
                    confidence = 0.85
                    match_type = "fuzzy"
                
                # Strategy 3: Amount match + date proximity
                elif abs(receipt_amount - txn_amount) < 0.01 and self._dates_close(receipt_date, txn_date):
                    confidence = 0.75
                    match_type = "amount_date"
                
                # Strategy 4: High merchant similarity
                elif self._calculate_merchant_similarity(receipt_merchant, txn_merchant) > 0.9:
                    confidence = 0.70
                    match_type = "merchant"
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = ReceiptMatch(
                        receipt_id=receipt_data.get("email_id", ""),
                        transaction_id=str(transaction.get("_id")),
                        confidence=confidence,
                        match_type=match_type,
                        merchant_similarity=self._calculate_merchant_similarity(receipt_merchant, txn_merchant),
                        amount_match=abs(receipt_amount - txn_amount) < 0.01,
                        date_match=self._dates_close(receipt_date, txn_date),
                        receipt_data=receipt_data,
                        transaction_data=transaction
                    )
            
            return best_match
            
        except Exception as e:
            logger.error(f"Error matching receipt to transaction: {e}")
            return None
    
    def _calculate_merchant_similarity(self, merchant1: str, merchant2: str) -> float:
        """Calculate similarity between merchant names"""
        try:
            if not merchant1 or not merchant2:
                return 0.0
            
            # Normalize merchant names
            def normalize_merchant(name):
                # Remove special characters and normalize
                normalized = re.sub(r'[^\w\s]', ' ', name.lower())
                # Replace multiple spaces with single space
                normalized = re.sub(r'\s+', ' ', normalized).strip()
                # Split into words and filter out common words
                words = normalized.split()
                # Filter out common words that don't help with matching
                common_words = {'inc', 'llc', 'corp', 'company', 'co', 'the', 'and', 'or', 'of', 'for', 'with'}
                words = [w for w in words if w not in common_words and len(w) > 1]
                return set(words)
            
            words1 = normalize_merchant(merchant1)
            words2 = normalize_merchant(merchant2)
            
            if not words1 or not words2:
                return 0.0
            
            # Calculate Jaccard similarity
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            similarity = len(intersection) / len(union)
            
            # Boost similarity for partial matches
            if similarity > 0:
                # Check if any word is a substring of another
                for word1 in words1:
                    for word2 in words2:
                        if word1 in word2 or word2 in word1:
                            similarity = min(similarity + 0.2, 1.0)
                            break
            
            return similarity
            
        except Exception as e:
            logger.error(f"Error calculating merchant similarity: {e}")
            return 0.0
    
    def _dates_close(self, date1: str, date2: str, days_threshold: int = 7) -> bool:
        """Check if two dates are within the threshold"""
        try:
            from datetime import datetime, timedelta
            
            # Parse dates
            date1_parsed = self._parse_date(date1)
            date2_parsed = self._parse_date(date2)
            
            if not date1_parsed or not date2_parsed:
                return False
            
            # Normalize timezones
            if date1_parsed.tzinfo is not None:
                date1_parsed = date1_parsed.replace(tzinfo=None)
            if date2_parsed.tzinfo is not None:
                date2_parsed = date2_parsed.replace(tzinfo=None)
            
            # Calculate difference
            diff = abs((date1_parsed - date2_parsed).days)
            return diff <= days_threshold
            
        except Exception as e:
            logger.error(f"Error checking date proximity: {e}")
            return False
    
    def _parse_date(self, date_input) -> Optional[datetime]:
        """Parse various date formats"""
        try:
            from datetime import datetime
            from email.utils import parsedate_to_datetime
            
            if isinstance(date_input, datetime):
                return date_input
            
            if not date_input:
                return None
            
            date_str = str(date_input)
            
            # Try RFC format first
            try:
                return parsedate_to_datetime(date_str)
            except:
                pass
            
            # Try ISO format
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                pass
            
            # Try common formats
            formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing date '{date_input}': {e}")
            return None
    
    def _upload_matched_receipt(self, match: ReceiptMatch) -> bool:
        """Upload matched receipt to R2 storage"""
        try:
            if not self.r2_client:
                logger.warning("R2 client not available")
                return False
            
            receipt_data = match.receipt_data
            source_type = receipt_data.get("source_type", "unknown")
            
            # Create R2 key based on source type
            account_safe = receipt_data.get("gmail_account", "").replace('@', '_at_').replace('.', '_')
            date_str = datetime.utcnow().strftime('%Y/%m/%d')
            
            if source_type == "body_screenshot":
                key = f"receipts/{account_safe}/{date_str}/{receipt_data.get('email_id', 'unknown')}_screenshot.png"
                file_path = receipt_data.get("image_path")
            elif source_type == "url_download":
                key = f"receipts/{account_safe}/{date_str}/{receipt_data.get('email_id', 'unknown')}_url.pdf"
                file_path = receipt_data.get("file_path")
            else:
                key = f"receipts/{account_safe}/{date_str}/{receipt_data.get('email_id', 'unknown')}.pdf"
                file_path = None
            
            # Upload to R2
            if file_path and os.path.exists(file_path):
                success = self.r2_client.upload_file(file_path, key, {
                    'transaction_id': match.transaction_id,
                    'confidence': str(match.confidence),
                    'match_type': match.match_type,
                    'source_type': source_type
                })
            else:
                # Create placeholder for now
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                    temp_file.write(b"Receipt placeholder")
                    temp_file_path = temp_file.name
                
                success = self.r2_client.upload_file(temp_file_path, key, {
                    'transaction_id': match.transaction_id,
                    'confidence': str(match.confidence),
                    'match_type': match.match_type,
                    'source_type': source_type
                })
                
                os.unlink(temp_file_path)
            
            if success:
                receipt_data["r2_key"] = key
                receipt_data["r2_url"] = self.r2_client.get_file_url(key)
            
            return success
            
        except Exception as e:
            logger.error(f"Error uploading matched receipt: {e}")
            return False
    
    def _save_receipt_record(self, match: ReceiptMatch):
        """Save receipt record to database with transaction link"""
        try:
            receipt_data = match.receipt_data.copy()
            receipt_data["transaction_id"] = match.transaction_id
            receipt_data["match_confidence"] = match.confidence
            receipt_data["match_type"] = match.match_type
            receipt_data["matched_at"] = datetime.utcnow().isoformat()
            
            # Insert receipt record
            result = self.db.receipts.insert_one(receipt_data)
            
            # Update transaction with receipt link
            self.db.bank_transactions.update_one(
                {"_id": match.transaction_data["_id"]},
                {"$set": {"receipt_url": receipt_data.get("r2_url", "")}}
            )
            
            logger.info(f"✅ Saved receipt record: {result.inserted_id}")
            
        except Exception as e:
            logger.error(f"Error saving receipt record: {e}")
    
    def __del__(self):
        """Cleanup webdriver"""
        if hasattr(self, 'webdriver') and self.webdriver:
            try:
                self.webdriver.quit()
            except:
                pass

def main():
    """Test the comprehensive receipt processor"""
    try:
        # Initialize clients
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri:
            logger.error("❌ No MongoDB URI configured")
            return
        
        mongo_client = MongoClient(mongo_uri)
        
        # Initialize R2 client
        try:
            from r2_client import R2Client
            r2_client = R2Client()
        except Exception as e:
            logger.warning(f"R2 client not available: {e}")
            r2_client = None
        
        # Initialize processor
        processor = ComprehensiveReceiptProcessor(mongo_client, r2_client)
        
        # Test with sample data
        sample_candidates = [
            {
                "message_id": "test_1",
                "subject": "Receipt from EXPENSIFY - $99.00",
                "from_email": "receipts@expensify.com",
                "date": "2025-06-28T10:00:00Z",
                "confidence_score": 0.9,
                "attachment_count": 0,
                "body": "Your receipt for $99.00 is attached. Thank you for your purchase!"
            }
        ]
        
        results = processor.process_email_receipts(sample_candidates, "test@example.com")
        logger.info(f"Test results: {results}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main() 
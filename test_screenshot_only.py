#!/usr/bin/env python3
"""
Test Screenshot Functionality Only
Demonstrates receipt-specific screenshot capture with dynamic sizing
"""

import os
import tempfile
import json
from datetime import datetime
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScreenshotTester:
    """Test class for screenshot functionality"""
    
    def __init__(self):
        self.webdriver = None
        self._init_webdriver()
    
    def _init_webdriver(self):
        """Initialize headless Chrome for screenshots"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            
            self.webdriver = webdriver.Chrome(options=chrome_options)
            logger.info("✅ WebDriver initialized for screenshots")
        except Exception as e:
            logger.warning(f"WebDriver not available for screenshots: {e}")
            logger.info("📸 Screenshot functionality will be disabled")
            self.webdriver = None
    
    def _find_receipt_element(self) -> Optional[object]:
        """Find the receipt element in the HTML"""
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
                "table[class*='bill']", "div[class*='bill']", "section[class*='bill']"
            ]
            
            for selector in receipt_selectors:
                try:
                    element = self.webdriver.find_element(By.CSS_SELECTOR, selector)
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
            
            receipt_element = self.webdriver.execute_script(js_script)
            if receipt_element:
                logger.info("✅ Found receipt element using JavaScript detection")
                return receipt_element
            
            logger.info("⚠️ No specific receipt element found, will screenshot entire page")
            return None
            
        except Exception as e:
            logger.error(f"Error finding receipt element: {e}")
            return None
    
    def _screenshot_element(self, element) -> Optional[str]:
        """Take screenshot of specific element with dynamic sizing"""
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
            
            self.webdriver.set_window_size(window_width, window_height)
            
            # Take screenshot
            screenshot_path = tempfile.mktemp(suffix='.png')
            self.webdriver.save_screenshot(screenshot_path)
            
            # Crop to just the element area
            img = Image.open(screenshot_path)
            cropped_img = img.crop((x, y, x + width, y + height))
            cropped_img.save(screenshot_path)
            
            logger.info(f"📸 Cropped screenshot: {width}x{height} at ({x},{y})")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Error taking element screenshot: {e}")
            return None
    
    def _screenshot_full_page(self) -> Optional[str]:
        """Take screenshot of entire page with dynamic sizing"""
        try:
            # Get page dimensions
            page_width = self.webdriver.execute_script("return document.body.scrollWidth")
            page_height = self.webdriver.execute_script("return document.body.scrollHeight")
            
            # Set window size to accommodate full page
            window_width = max(1200, page_width + 50)
            window_height = max(800, page_height + 50)
            
            self.webdriver.set_window_size(window_width, window_height)
            
            # Take screenshot
            screenshot_path = tempfile.mktemp(suffix='.png')
            self.webdriver.save_screenshot(screenshot_path)
            
            logger.info(f"📸 Full page screenshot: {page_width}x{page_height}")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Error taking full page screenshot: {e}")
            return None
    
    def _take_screenshot(self, html_path: str) -> Optional[str]:
        """Take screenshot of receipt area in HTML file"""
        try:
            if not self.webdriver:
                logger.warning("WebDriver not available for screenshots")
                return None
            
            # Load HTML file
            self.webdriver.get(f"file://{html_path}")
            
            # Wait for page to load
            WebDriverWait(self.webdriver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Try to find receipt-specific elements
            receipt_element = self._find_receipt_element()
            
            if receipt_element:
                # Screenshot just the receipt element
                screenshot_path = self._screenshot_element(receipt_element)
                logger.info(f"📸 Screenshot of receipt element saved to {screenshot_path}")
            else:
                # Fallback: screenshot entire page with dynamic sizing
                screenshot_path = self._screenshot_full_page()
                logger.info(f"📸 Full page screenshot saved to {screenshot_path}")
            
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
    
    def __del__(self):
        """Clean up webdriver"""
        if self.webdriver:
            try:
                self.webdriver.quit()
            except:
                pass

def create_test_html_files():
    """Create test HTML files with different receipt layouts"""
    test_files = {}
    
    # Test 1: Simple receipt with clear structure
    simple_receipt = """
    <!DOCTYPE html>
    <html>
    <head><title>Simple Receipt</title></head>
    <body>
        <div class="receipt">
            <h2>STARBUCKS</h2>
            <p>Date: 2025-06-28</p>
            <p>Order #: 12345</p>
            <table>
                <tr><td>Latte</td><td>$4.50</td></tr>
                <tr><td>Muffin</td><td>$3.25</td></tr>
                <tr><td><strong>Total</strong></td><td><strong>$7.75</strong></td></tr>
            </table>
        </div>
    </body>
    </html>
    """
    
    # Test 2: Elongated receipt with lots of content
    elongated_receipt = """
    <!DOCTYPE html>
    <html>
    <head><title>Elongated Receipt</title></head>
    <body>
        <div class="header">Company Header</div>
        <div class="navigation">Navigation Menu</div>
        <div class="sidebar">Sidebar Content</div>
        
        <div class="main-content">
            <div class="receipt" id="invoice">
                <h1>AMAZON.COM</h1>
                <p>Order Date: 2025-06-28</p>
                <p>Order #: AMZ-123456789</p>
                
                <table class="items">
                    <tr><th>Item</th><th>Price</th></tr>
                    <tr><td>Wireless Headphones</td><td>$89.99</td></tr>
                    <tr><td>Phone Case</td><td>$19.99</td></tr>
                    <tr><td>Screen Protector</td><td>$12.99</td></tr>
                    <tr><td>USB Cable</td><td>$8.99</td></tr>
                    <tr><td>Power Bank</td><td>$45.99</td></tr>
                </table>
                
                <div class="totals">
                    <p>Subtotal: $177.95</p>
                    <p>Tax: $14.24</p>
                    <p>Shipping: $0.00</p>
                    <p><strong>Total Amount: $192.19</strong></p>
                </div>
                
                <div class="footer">
                    <p>Thank you for your purchase!</p>
                    <p>Customer Service: 1-800-AMAZON</p>
                </div>
            </div>
        </div>
        
        <div class="footer">Page Footer</div>
        <div class="ads">Advertisement Content</div>
    </body>
    </html>
    """
    
    # Test 3: Receipt embedded in email body
    email_receipt = """
    <!DOCTYPE html>
    <html>
    <head><title>Email Receipt</title></head>
    <body>
        <div class="email-header">
            <p>From: noreply@uber.com</p>
            <p>Subject: Your Uber Receipt</p>
            <p>Date: 2025-06-28</p>
        </div>
        
        <div class="email-body">
            <p>Hi Brian,</p>
            <p>Here's your receipt for your recent Uber ride:</p>
            
            <div class="receipt" data-type="receipt">
                <h3>UBER</h3>
                <p>Trip Date: 2025-06-28</p>
                <p>Driver: John Smith</p>
                <p>From: Downtown Nashville</p>
                <p>To: Music Row</p>
                <p>Distance: 2.3 miles</p>
                <p>Duration: 8 minutes</p>
                <p><strong>Total: $12.50</strong></p>
            </div>
            
            <p>Thank you for using Uber!</p>
            <p>Best regards,<br>The Uber Team</p>
        </div>
        
        <div class="email-footer">
            <p>This is an automated message</p>
        </div>
    </body>
    </html>
    """
    
    # Test 4: Receipt with currency patterns but no clear structure
    currency_receipt = """
    <!DOCTYPE html>
    <html>
    <head><title>Currency Receipt</title></head>
    <body>
        <div class="page-content">
            <h1>Welcome to our website</h1>
            <p>Here's some general content...</p>
            
            <div class="transaction-details">
                <h2>Transaction Summary</h2>
                <p>Merchant: WALMART</p>
                <p>Date: 2025-06-28</p>
                <p>Items purchased:</p>
                <ul>
                    <li>Groceries: $45.67</li>
                    <li>Household items: $23.45</li>
                    <li>Electronics: $89.99</li>
                </ul>
                <p>Subtotal: $159.11</p>
                <p>Tax: $12.73</p>
                <p><strong>Total: $171.84</strong></p>
            </div>
            
            <p>More content below...</p>
        </div>
    </body>
    </html>
    """
    
    # Create temporary files
    test_cases = {
        "simple": simple_receipt,
        "elongated": elongated_receipt,
        "email": email_receipt,
        "currency": currency_receipt
    }
    
    for name, content in test_cases.items():
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(content)
            test_files[name] = f.name
    
    return test_files

def test_screenshot_functionality():
    """Test the enhanced screenshot functionality"""
    try:
        # Initialize screenshot tester
        tester = ScreenshotTester()
        
        # Create test HTML files
        test_files = create_test_html_files()
        
        logger.info("🧪 Testing Enhanced Screenshot Functionality")
        logger.info("=" * 50)
        
        results = {}
        
        for test_name, html_path in test_files.items():
            logger.info(f"\n📸 Testing: {test_name.upper()} receipt")
            logger.info("-" * 30)
            
            try:
                # Take screenshot
                screenshot_path = tester._take_screenshot(html_path)
                
                if screenshot_path:
                    # Get file size
                    file_size = os.path.getsize(screenshot_path)
                    
                    # Get image dimensions
                    with Image.open(screenshot_path) as img:
                        width, height = img.size
                        dimensions = f"{width}x{height}"
                    
                    results[test_name] = {
                        "success": True,
                        "screenshot_path": screenshot_path,
                        "file_size": file_size,
                        "dimensions": dimensions
                    }
                    
                    logger.info(f"✅ Screenshot created: {screenshot_path}")
                    logger.info(f"   Size: {file_size} bytes")
                    logger.info(f"   Dimensions: {dimensions}")
                    
                    # Clean up screenshot
                    os.unlink(screenshot_path)
                else:
                    results[test_name] = {"success": False, "error": "No screenshot created"}
                    logger.error(f"❌ Failed to create screenshot for {test_name}")
                    
            except Exception as e:
                results[test_name] = {"success": False, "error": str(e)}
                logger.error(f"❌ Error testing {test_name}: {e}")
            
            # Clean up HTML file
            os.unlink(html_path)
        
        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("=" * 50)
        
        successful = sum(1 for r in results.values() if r.get("success"))
        total = len(results)
        
        logger.info(f"✅ Successful: {successful}/{total}")
        
        for test_name, result in results.items():
            status = "✅ PASS" if result.get("success") else "❌ FAIL"
            logger.info(f"{status} {test_name}: {result.get('dimensions', 'N/A')} ({result.get('file_size', 0)} bytes)")
            if not result.get("success"):
                logger.info(f"   Error: {result.get('error', 'Unknown error')}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return None

def main():
    """Main test function"""
    logger.info("🚀 Starting Enhanced Screenshot Test")
    
    results = test_screenshot_functionality()
    
    if results:
        logger.info("\n🎉 Test completed successfully!")
        
        # Save results to file
        with open("screenshot_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info("📄 Results saved to screenshot_test_results.json")
    else:
        logger.error("❌ Test failed")

if __name__ == "__main__":
    main() 
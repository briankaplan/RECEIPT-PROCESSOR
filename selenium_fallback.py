
#!/usr/bin/env python3
"""
Selenium Fallback System
"""

import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class SeleniumFallback:
    """Selenium fallback for screenshot functionality"""
    
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver with fallback options"""
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(options=options)
            logger.info("✅ Selenium driver setup successful")
        
        except Exception as e:
            logger.warning(f"⚠️ Selenium driver setup failed: {e}")
            self.driver = None
    
    def take_screenshot(self, url: str, selector: str = None) -> str:
        """Take screenshot with fallback"""
        if not self.driver:
            return None
        
        try:
            self.driver.get(url)
            
            if selector:
                # Wait for element and take screenshot
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                screenshot_path = f"screenshot_{int(time.time())}.png"
                element.screenshot(screenshot_path)
            else:
                # Take full page screenshot
                screenshot_path = f"screenshot_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot_path)
            
            logger.info(f"📸 Screenshot saved: {screenshot_path}")
            return screenshot_path
        
        except Exception as e:
            logger.error(f"❌ Screenshot failed: {e}")
            return None
    
    def close(self):
        """Close driver"""
        if self.driver:
            self.driver.quit()

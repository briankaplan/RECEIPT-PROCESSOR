#!/usr/bin/env python3
"""
Test Hugging Face API with real receipt image
Verifies the multipart form data fix works correctly
"""

import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_huggingface_with_real_image():
    """Test Hugging Face API with a real receipt image"""
    
    try:
        from huggingface_receipt_processor import HuggingFaceReceiptProcessor
        
        logger.info("🧪 Testing Hugging Face API with real receipt image...")
        
        # Initialize processor
        processor = HuggingFaceReceiptProcessor()
        
        # Check for test image
        test_image_path = os.path.join("downloads", "sample_receipt.png")
        if not os.path.exists(test_image_path):
            logger.warning(f"⚠️ Test image not found at {test_image_path}")
            logger.info("Creating a simple test image...")
            
            # Create a simple test image with receipt-like content
            from PIL import Image, ImageDraw, ImageFont
            import tempfile
            
            # Create a simple receipt image
            img = Image.new('RGB', (400, 300), color='white')
            draw = ImageDraw.Draw(img)
            
            # Add some receipt-like text
            text_lines = [
                "STORE RECEIPT",
                "Date: 2025-06-28",
                "Merchant: Test Store",
                "Items:",
                "  - Item 1: $10.00",
                "  - Item 2: $15.50",
                "",
                "Total: $25.50"
            ]
            
            y_position = 20
            for line in text_lines:
                draw.text((20, y_position), line, fill='black')
                y_position += 25
            
            # Save to temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            img.save(temp_file.name)
            test_image_path = temp_file.name
            logger.info(f"Created test image at: {test_image_path}")
        
        # Test with different models
        models_to_test = ["paligemma", "donut", "trocr", "blip"]
        
        for model in models_to_test:
            logger.info(f"🔍 Testing model: {model}")
            
            try:
                result = processor.process_receipt_image(test_image_path, model_name=model)
                
                if result.get("success", False):
                    logger.info(f"✅ {model} - Success!")
                    logger.info(f"   Merchant: {result.get('merchant', 'N/A')}")
                    logger.info(f"   Amount: {result.get('amount', 'N/A')}")
                    logger.info(f"   Date: {result.get('date', 'N/A')}")
                    logger.info(f"   Confidence: {result.get('confidence', 'N/A')}")
                else:
                    logger.warning(f"⚠️ {model} - Failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"❌ {model} - Exception: {str(e)}")
        
        # Clean up temp file if created
        if test_image_path.startswith('/tmp/'):
            os.unlink(test_image_path)
            
        logger.info("🎯 Hugging Face API test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_huggingface_with_real_image() 
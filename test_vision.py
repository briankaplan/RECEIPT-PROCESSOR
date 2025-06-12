#!/usr/bin/env python3
"""
Test Google Vision API
Verifies OCR (text detection) using the configured service account
"""
import os
import json
import logging
from google.cloud import vision
from google.oauth2 import service_account
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join('config', 'expense_config.json')
SAMPLE_IMAGE = 'test_vision_sample.png'


def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return None

def generate_sample_image(path):
    img = Image.new('RGB', (200, 60), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    text = "Hello Vision API!"
    d.text((10, 20), text, fill=(0, 0, 0))
    img.save(path)
    return path

def test_vision():
    config = load_config()
    if not config:
        return False
    service_account_path = config.get('service_account_path')
    if not service_account_path or not os.path.exists(service_account_path):
        logger.error("Service account credentials not found in config or file missing.")
        return False
    # Generate a sample image if not present
    if not os.path.exists(SAMPLE_IMAGE):
        generate_sample_image(SAMPLE_IMAGE)
    try:
        creds = service_account.Credentials.from_service_account_file(service_account_path)
        client = vision.ImageAnnotatorClient(credentials=creds)
        with open(SAMPLE_IMAGE, 'rb') as image_file:
            content = image_file.read()
        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        texts = response.text_annotations
        if texts:
            logger.info(f"Detected text: {texts[0].description.strip()}")
            logger.info("🎉 Google Vision API test completed successfully")
            return True
        else:
            logger.error("❌ No text detected in sample image.")
            return False
    except Exception as e:
        logger.error(f"❌ Google Vision API test failed: {e}")
        return False

if __name__ == "__main__":
    test_vision() 
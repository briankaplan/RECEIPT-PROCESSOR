#!/usr/bin/env python3
"""
Test Hugging Face API with text processing
Since the processor is configured for text models, not image models
"""

import os
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_huggingface_text_models():
    """Test Hugging Face text models that are actually available"""
    
    hf_api_token = os.getenv("HUGGINGFACE_API_KEY")
    if not hf_api_token:
        logger.error("❌ No HuggingFace API token found")
        return
    
    headers = {
        "Authorization": f"Bearer {hf_api_token}"
    }
    
    # Test with a simple text model that should work
    test_models = [
        "microsoft/DialoGPT-medium",
        "gpt2",
        "distilgpt2"
    ]
    
    logger.info("🔍 Testing Hugging Face text models...")
    
    for model in test_models:
        endpoint = f"https://api-inference.huggingface.co/models/{model}"
        
        try:
            # Test with text input
            payload = {"inputs": "Hello, how are you?"}
            response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ {model} - Working!")
                result = response.json()
                logger.info(f"   Response: {result[:100]}...")  # First 100 chars
            elif response.status_code == 404:
                logger.warning(f"⚠️ {model} - Not found (404)")
            else:
                logger.warning(f"⚠️ {model} - Status {response.status_code}: {response.text[:100]}")
                
        except Exception as e:
            logger.error(f"❌ {model} - Error: {str(e)}")
    
    logger.info("🎯 Text model test completed!")

if __name__ == "__main__":
    test_huggingface_text_models() 
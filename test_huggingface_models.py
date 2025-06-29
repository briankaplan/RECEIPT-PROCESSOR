#!/usr/bin/env python3
"""
Test which Hugging Face models are available and working
"""

import os
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_available_models():
    """Test which Hugging Face models are available"""
    
    hf_api_token = os.getenv("HUGGINGFACE_API_KEY")
    if not hf_api_token:
        logger.error("❌ No HuggingFace API token found")
        return
    
    headers = {
        "Authorization": f"Bearer {hf_api_token}"
    }
    
    # Test different model endpoints
    models_to_test = [
        "microsoft/DialoGPT-medium",  # Simple text model for connectivity test
        "google/paligemma-3b-mix-224",  # PaliGemma model
        "naver-clova-ix/donut-base-finetuned-cord-v2",  # Donut model
        "microsoft/trocr-base-handwritten",  # TrOCR model
        "Salesforce/blip-image-captioning-base",  # BLIP model
    ]
    
    logger.info("🔍 Testing Hugging Face model availability...")
    
    for model in models_to_test:
        endpoint = f"https://api-inference.huggingface.co/models/{model}"
        
        try:
            # Test with a simple text input for text models
            if "DialoGPT" in model:
                payload = {"inputs": "Hello, how are you?"}
                response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
            else:
                # For image models, just test if the endpoint exists
                response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ {model} - Available")
            elif response.status_code == 404:
                logger.warning(f"⚠️ {model} - Not found (404)")
            else:
                logger.warning(f"⚠️ {model} - Status {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ {model} - Error: {str(e)}")
    
    logger.info("🎯 Model availability test completed!")

if __name__ == "__main__":
    test_available_models() 
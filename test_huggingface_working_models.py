#!/usr/bin/env python3
"""
Find working Hugging Face models that are actually available
"""

import os
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_working_models():
    """Find Hugging Face models that are actually working"""
    
    hf_api_token = os.getenv("HUGGINGFACE_API_KEY")
    if not hf_api_token:
        logger.error("❌ No HuggingFace API token found")
        return
    
    headers = {
        "Authorization": f"Bearer {hf_api_token}"
    }
    
    # Test popular models that are commonly deployed
    test_models = [
        # Text models
        "microsoft/DialoGPT-medium",
        "gpt2",
        "distilgpt2",
        "microsoft/DialoGPT-small",
        
        # Image models that should work
        "Salesforce/blip-image-captioning-base",
        "Salesforce/blip-image-captioning-large",
        "microsoft/git-base",
        "microsoft/git-large",
        
        # OCR models
        "microsoft/trocr-base-handwritten",
        "microsoft/trocr-large-handwritten",
        
        # Document models
        "microsoft/layoutlm-base-uncased",
        "microsoft/layoutlm-large-uncased",
        
        # Donut models
        "naver-clova-ix/donut-base-finetuned-cord-v2",
        "naver-clova-ix/donut-base-finetuned-docvqa",
        
        # PaliGemma models
        "google/paligemma-3b-mix-224",
        "google/paligemma-3b-mix-448",
    ]
    
    logger.info("🔍 Finding working Hugging Face models...")
    working_models = []
    
    for model in test_models:
        endpoint = f"https://api-inference.huggingface.co/models/{model}"
        
        try:
            # Test if model exists
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ {model} - Available!")
                working_models.append(model)
                
                # Try a simple test if it's a text model
                if any(text_model in model.lower() for text_model in ['dialogpt', 'gpt2', 'distilgpt2']):
                    try:
                        payload = {"inputs": "Hello"}
                        test_response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
                        if test_response.status_code == 200:
                            logger.info(f"   ✅ {model} - Text generation working")
                        else:
                            logger.warning(f"   ⚠️ {model} - Text generation failed: {test_response.status_code}")
                    except Exception as e:
                        logger.warning(f"   ⚠️ {model} - Text test failed: {str(e)}")
                        
            elif response.status_code == 404:
                logger.warning(f"⚠️ {model} - Not found (404)")
            else:
                logger.warning(f"⚠️ {model} - Status {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ {model} - Error: {str(e)}")
    
    logger.info(f"🎯 Found {len(working_models)} working models:")
    for model in working_models:
        logger.info(f"   - {model}")
    
    return working_models

if __name__ == "__main__":
    find_working_models() 
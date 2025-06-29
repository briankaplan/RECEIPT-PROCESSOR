#!/usr/bin/env python3
"""
Test Hugging Face API token access and available models
"""

import os
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_hf_token_access():
    """Test what Hugging Face API access you have"""
    
    hf_api_token = os.getenv("HUGGINGFACE_API_KEY")
    if not hf_api_token:
        logger.error("❌ No HuggingFace API token found")
        return
    
    headers = {
        "Authorization": f"Bearer {hf_api_token}"
    }
    
    logger.info("🔍 Testing Hugging Face API token access...")
    
    # Test 1: Check if token is valid
    try:
        response = requests.get("https://huggingface.co/api/whoami", headers=headers, timeout=10)
        if response.status_code == 200:
            user_info = response.json()
            logger.info(f"✅ Token is valid for user: {user_info.get('name', 'Unknown')}")
        else:
            logger.error(f"❌ Invalid token: {response.status_code}")
            return
    except Exception as e:
        logger.error(f"❌ Token validation failed: {str(e)}")
        return
    
    # Test 2: Check what models you have access to
    try:
        response = requests.get("https://huggingface.co/api/models", headers=headers, timeout=10)
        if response.status_code == 200:
            models = response.json()
            logger.info(f"✅ Found {len(models)} models you have access to")
            
            # Show first few models
            for i, model in enumerate(models[:5]):
                logger.info(f"   - {model.get('id', 'Unknown')}")
            if len(models) > 5:
                logger.info(f"   ... and {len(models) - 5} more")
        else:
            logger.warning(f"⚠️ Could not fetch models: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Model fetch failed: {str(e)}")
    
    # Test 3: Try to find any working inference endpoint
    logger.info("🔍 Looking for any working inference endpoints...")
    
    # Try some very basic models that should always be available
    basic_models = [
        "bert-base-uncased",
        "distilbert-base-uncased", 
        "roberta-base",
        "microsoft/DialoGPT-small",
        "gpt2"
    ]
    
    for model in basic_models:
        endpoint = f"https://api-inference.huggingface.co/models/{model}"
        try:
            response = requests.get(endpoint, headers=headers, timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ {model} - Inference endpoint available!")
                break
            elif response.status_code == 404:
                logger.warning(f"⚠️ {model} - Not found")
            else:
                logger.warning(f"⚠️ {model} - Status {response.status_code}")
        except Exception as e:
            logger.error(f"❌ {model} - Error: {str(e)}")
    
    logger.info("🎯 Hugging Face access test completed!")

if __name__ == "__main__":
    test_hf_token_access() 
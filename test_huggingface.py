#!/usr/bin/env python3
"""
Test Hugging Face Integration
Loads a model and encodes a sample sentence
"""
from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_huggingface():
    try:
        model_name = 'sentence-transformers/all-MiniLM-L6-v2'
        logger.info(f"Loading model: {model_name}")
        model = SentenceTransformer(model_name)
        sample = "This is a test sentence for Hugging Face embeddings."
        logger.info(f"Encoding sample: {sample}")
        embedding = model.encode(sample)
        logger.info(f"Embedding shape: {embedding.shape}")
        logger.info(f"Embedding (first 5 values): {embedding[:5]}")
        logger.info("🎉 Hugging Face test completed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Hugging Face test failed: {e}")
        return False

if __name__ == "__main__":
    test_huggingface() 
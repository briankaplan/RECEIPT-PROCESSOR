"""
AI service for handling HuggingFace and other AI integrations
"""

import logging
from typing import Dict, Optional
from ..config import Config

logger = logging.getLogger(__name__)

class AIService:
    """Service for AI-powered receipt processing"""
    
    def __init__(self):
        self.hf_api_key = Config.HUGGINGFACE_API_KEY
        self.available = bool(self.hf_api_key)
        
        if self.available:
            logger.info("✅ AI Service initialized with HuggingFace")
        else:
            logger.warning("⚠️ AI Service not available - no HuggingFace API key")
    
    def extract_receipt_data(self, file_data: bytes) -> Dict:
        """Extract receipt data using AI"""
        try:
            if not self.available:
                return self._fallback_extraction()
            
            # Use HuggingFace for receipt processing
            from huggingface_receipt_processor import HuggingFaceReceiptProcessor
            
            processor = HuggingFaceReceiptProcessor()
            result = processor.process_receipt(file_data)
            
            if result and result.get('success'):
                return {
                    'merchant': result.get('merchant', 'Unknown'),
                    'date': result.get('date'),
                    'total_amount': result.get('total_amount', 0.0),
                    'items': result.get('items', []),
                    'confidence': result.get('confidence', 0.0),
                    'extraction_method': 'huggingface'
                }
            else:
                logger.warning("HuggingFace extraction failed, using fallback")
                return self._fallback_extraction()
                
        except Exception as e:
            logger.error(f"AI extraction error: {e}")
            return self._fallback_extraction()
    
    def _fallback_extraction(self) -> Dict:
        """Fallback extraction when AI is not available"""
        from datetime import datetime
        
        return {
            'merchant': 'Unknown',
            'date': datetime.utcnow().isoformat(),
            'total_amount': 0.0,
            'items': [],
            'confidence': 0.0,
            'extraction_method': 'fallback'
        }
    
    def is_available(self) -> bool:
        """Check if AI service is available"""
        return self.available
    
    def get_capabilities(self) -> Dict:
        """Get AI service capabilities"""
        return {
            'available': self.available,
            'provider': 'HuggingFace' if self.available else 'None',
            'features': [
                'Receipt OCR',
                'Text Extraction',
                'Data Classification'
            ] if self.available else []
        } 
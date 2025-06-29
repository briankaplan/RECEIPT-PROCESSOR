"""
Receipt processing service
"""

import logging
import os
from datetime import datetime
from typing import Dict, Optional, List
from ..utils.validators import validate_upload
from ..config import Config

logger = logging.getLogger(__name__)

class ReceiptService:
    """Service for processing receipts with proper error handling and logging"""
    
    def __init__(self, db_client, ai_processor=None, storage_client=None):
        self.db = db_client
        self.ai = ai_processor
        self.storage = storage_client
    
    def process_receipt(self, file_data: bytes, filename: str) -> Dict:
        """Process receipt with proper error handling and logging"""
        try:
            logger.info(f"Processing receipt: {filename}")
            
            # Validate file
            validate_upload(file_data, filename)
            
            # Extract data using AI if available
            extracted_data = None
            if self.ai:
                try:
                    extracted_data = self.ai.extract_receipt_data(file_data)
                    logger.info(f"AI extraction completed for {filename}")
                except Exception as e:
                    logger.warning(f"AI extraction failed for {filename}: {e}")
                    extracted_data = self._fallback_extraction(file_data)
            else:
                extracted_data = self._fallback_extraction(file_data)
            
            # Store file if storage is available
            storage_url = None
            if self.storage and self.storage.is_connected():
                try:
                    storage_url = self.storage.upload_file(file_data, filename)
                    logger.info(f"File stored: {storage_url}")
                except Exception as e:
                    logger.warning(f"Storage upload failed: {e}")
            
            # Save to database
            receipt_id = None
            if self.db and self.db.connected:
                receipt_record = {
                    **extracted_data,
                    'storage_url': storage_url,
                    'filename': filename,
                    'processed_at': datetime.utcnow(),
                    'source_type': 'api_upload',
                    'status': 'processed'
                }
                receipt_id = self.db.save_receipt(receipt_record)
                logger.info(f"Receipt saved to database: {receipt_id}")
            
            return {
                'success': True,
                'receipt_id': receipt_id,
                'extracted_data': extracted_data,
                'storage_url': storage_url
            }
        
        except Exception as e:
            logger.error(f"Receipt processing failed for {filename}: {e}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
    
    def _fallback_extraction(self, file_data: bytes) -> Dict:
        """Fallback extraction method when AI is not available"""
        return {
            'merchant': 'Unknown',
            'date': datetime.utcnow().isoformat(),
            'total_amount': 0.0,
            'items': [],
            'confidence': 0.0,
            'extraction_method': 'fallback'
        }
    
    def get_receipts(self, limit: int = 50, skip: int = 0) -> List[Dict]:
        """Get receipts from database"""
        if not self.db or not self.db.connected:
            return []
        
        return self.db.get_receipts(limit, skip)
    
    def get_receipt_by_id(self, receipt_id: str) -> Optional[Dict]:
        """Get specific receipt by ID"""
        if not self.db or not self.db.connected:
            return None
        
        try:
            from bson import ObjectId
            return self.db.db.receipts.find_one({'_id': ObjectId(receipt_id)})
        except Exception as e:
            logger.error(f"Error getting receipt {receipt_id}: {e}")
            return None 
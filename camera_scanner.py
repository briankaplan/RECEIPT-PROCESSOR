#!/usr/bin/env python3
"""
Camera scanning and batch photo upload system for receipt capture
Provides camera interface and batch processing capabilities
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from werkzeug.utils import secure_filename
from PIL import Image
import io
import base64

logger = logging.getLogger(__name__)

class CameraScanner:
    """Camera scanning and batch photo upload for receipts"""
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self, upload_dir: str = 'uploads'):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        
    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def process_camera_capture(self, image_data: str, filename: str = None) -> Optional[Dict]:
        """Process image captured from camera (base64 format)"""
        try:
            # Remove data URL prefix if present
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"camera_capture_{timestamp}.jpg"
            
            # Save image file
            filepath = os.path.join(self.upload_dir, secure_filename(filename))
            
            # Convert and optimize image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Optimize for OCR (increase contrast, resize if too large)
            image = self._optimize_for_ocr(image)
            
            # Save optimized image
            image.save(filepath, 'JPEG', quality=95)
            
            file_info = {
                'filepath': filepath,
                'filename': filename,
                'source_type': 'camera_capture',
                'captured_at': datetime.utcnow(),
                'size': os.path.getsize(filepath),
                'width': image.width,
                'height': image.height
            }
            
            logger.info(f"Processed camera capture: {filename}")
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to process camera capture: {e}")
            return None
    
    def process_batch_upload(self, files: List) -> List[Dict]:
        """Process multiple uploaded files"""
        processed_files = []
        
        for file in files:
            try:
                if file and self.allowed_file(file.filename):
                    # Check file size
                    file.seek(0, 2)  # Seek to end
                    size = file.tell()
                    file.seek(0)  # Reset to beginning
                    
                    if size > self.MAX_FILE_SIZE:
                        logger.warning(f"File {file.filename} too large: {size} bytes")
                        continue
                    
                    # Generate unique filename
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    extension = file.filename.rsplit('.', 1)[1].lower()
                    filename = f"batch_upload_{timestamp}_{secure_filename(file.filename)}"
                    filepath = os.path.join(self.upload_dir, filename)
                    
                    # Process and save image
                    image = Image.open(file.stream)
                    
                    # Convert to RGB if necessary
                    if image.mode in ('RGBA', 'LA', 'P'):
                        image = image.convert('RGB')
                    
                    # Optimize for OCR
                    image = self._optimize_for_ocr(image)
                    
                    # Save optimized image
                    image.save(filepath, 'JPEG', quality=95)
                    
                    file_info = {
                        'filepath': filepath,
                        'filename': filename,
                        'original_filename': file.filename,
                        'source_type': 'batch_upload',
                        'uploaded_at': datetime.utcnow(),
                        'size': os.path.getsize(filepath),
                        'width': image.width,
                        'height': image.height
                    }
                    
                    processed_files.append(file_info)
                    logger.info(f"Processed uploaded file: {file.filename}")
                    
            except Exception as e:
                logger.error(f"Failed to process uploaded file {file.filename}: {e}")
        
        logger.info(f"Processed {len(processed_files)} files from batch upload")
        return processed_files
    
    def _optimize_for_ocr(self, image: Image.Image) -> Image.Image:
        """Optimize image for better OCR results"""
        # Resize if image is too large (OCR works better with moderate sizes)
        max_dimension = 2000
        if max(image.width, image.height) > max_dimension:
            ratio = max_dimension / max(image.width, image.height)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Enhance contrast for better text recognition
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)
        
        return image
    
    def process_receipt_images(self, file_infos: List[Dict], receipt_processor) -> List[Dict]:
        """Process receipt images and extract data"""
        processed_receipts = []
        
        for file_info in file_infos:
            try:
                # Extract receipt data
                receipt_data = receipt_processor.extract_receipt_data(file_info['filepath'])
                
                if receipt_data:
                    # Add file metadata
                    receipt_data.update({
                        'source_type': file_info['source_type'],
                        'original_filename': file_info.get('original_filename', file_info['filename']),
                        'processed_at': datetime.utcnow(),
                        'image_width': file_info['width'],
                        'image_height': file_info['height'],
                        'file_size': file_info['size']
                    })
                    
                    processed_receipts.append(receipt_data)
                
                # Clean up temporary file
                if os.path.exists(file_info['filepath']):
                    os.remove(file_info['filepath'])
                    
            except Exception as e:
                logger.error(f"Failed to process receipt image {file_info['filename']}: {e}")
        
        logger.info(f"Processed {len(processed_receipts)} receipt images")
        return processed_receipts
    
    def get_stats(self) -> Dict:
        """Get camera scanner statistics"""
        upload_count = len([f for f in os.listdir(self.upload_dir) 
                           if os.path.isfile(os.path.join(self.upload_dir, f))])
        
        return {
            'upload_directory': self.upload_dir,
            'allowed_extensions': list(self.ALLOWED_EXTENSIONS),
            'max_file_size': self.MAX_FILE_SIZE,
            'pending_uploads': upload_count
        }
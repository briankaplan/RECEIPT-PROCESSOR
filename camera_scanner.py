#!/usr/bin/env python3
"""
Camera scanning and batch photo upload system for receipt capture
Provides camera interface and batch processing capabilities
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from werkzeug.utils import secure_filename
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import io
import base64
import json
import uuid
import time
import numpy as np
import cv2

logger = logging.getLogger(__name__)

class UltraFastReceiptScanner:
    """
    🚀 ULTRA-FAST RECEIPT SCANNER WITH EDGE DETECTION
    Advanced computer vision for instant receipt processing
    """
    
    def __init__(self):
        self.upload_dir = 'uploads'
        self.MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
        self.ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}
        self.processed_count = 0
        
        # Ensure upload directory exists
        os.makedirs(self.upload_dir, exist_ok=True)
        
        # Advanced enhancement settings
        self.enhancement_params = {
            'contrast_boost': 1.3,
            'sharpness_boost': 1.4,
            'brightness_adjust': 1.1,
            'edge_detection_threshold': 50,
            'min_receipt_area': 5000,  # Minimum pixels for receipt detection
            'max_receipt_area': 2000000  # Maximum pixels
        }
        
        logger.info("🚀 Ultra-Fast Receipt Scanner initialized")

    def process_batch_upload_ultra_fast(self, files: List) -> List[Dict]:
        """
        ⚡ ULTRA-FAST batch processing with parallel enhancement
        """
        import concurrent.futures
        import threading
        
        start_time = time.time()
        processed_files = []
        processing_futures = []
        
        # Thread-safe counter
        self.processed_count = 0
        count_lock = threading.Lock()
        
        def process_single_file(file_info):
            try:
                file, index = file_info
                result = self._process_single_file_ultra_fast(file, index)
                
                with count_lock:
                    self.processed_count += 1
                    
                return result
            except Exception as e:
                logger.error(f"Failed to process file {getattr(file, 'filename', 'unknown')}: {e}")
                return None
        
        # Process files in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            file_infos = [(file, i) for i, file in enumerate(files)]
            processing_futures = [executor.submit(process_single_file, info) for info in file_infos]
            
            for future in concurrent.futures.as_completed(processing_futures):
                result = future.result()
                if result:
                    processed_files.append(result)
        
        processing_time = time.time() - start_time
        logger.info(f"⚡ Ultra-fast processing complete: {len(processed_files)} files in {processing_time:.2f}s")
        
        return processed_files

    def _process_single_file_ultra_fast(self, file, index: int) -> Optional[Dict]:
        """Process a single file with advanced edge detection and enhancement"""
        try:
            if not file or not self.allowed_file(file.filename):
                return None
            
            # File size check
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            
            if size > self.MAX_FILE_SIZE:
                logger.warning(f"File {file.filename} too large: {size} bytes")
                return None
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
            extension = file.filename.rsplit('.', 1)[1].lower()
            filename = f"ultra_scan_{timestamp}_{index:03d}.{extension}"
            filepath = os.path.join(self.upload_dir, filename)
            
            # Load and process image
            image = Image.open(file.stream)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # 🎯 ADVANCED RECEIPT PROCESSING PIPELINE
            processed_image = self._ultra_enhance_receipt(image)
            receipt_bounds = self._detect_receipt_edges(processed_image)
            
            if receipt_bounds:
                # Crop to receipt boundaries with smart padding
                cropped_image = self._smart_crop_receipt(processed_image, receipt_bounds)
                final_image = self._final_enhancement(cropped_image)
            else:
                # Fallback to standard enhancement if edge detection fails
                final_image = self._standard_enhancement(processed_image)
            
            # Save optimized image
            final_image.save(filepath, 'JPEG', quality=95, optimize=True)
            
            # Calculate enhancement metrics
            metrics = self._calculate_image_metrics(image, final_image)
            
            file_info = {
                'filepath': filepath,
                'filename': filename,
                'original_filename': file.filename,
                'source_type': 'ultra_fast_scan',
                'uploaded_at': datetime.utcnow(),
                'size': os.path.getsize(filepath),
                'original_size': size,
                'compression_ratio': round(os.path.getsize(filepath) / size, 2),
                'width': final_image.width,
                'height': final_image.height,
                'receipt_detected': receipt_bounds is not None,
                'enhancement_metrics': metrics,
                'processing_index': index
            }
            
            logger.info(f"⚡ Enhanced {file.filename} -> {filename} (Receipt: {'✅' if receipt_bounds else '❌'})")
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to process {getattr(file, 'filename', 'unknown')}: {e}")
            return None

    def _ultra_enhance_receipt(self, image: Image.Image) -> Image.Image:
        """🎯 ULTRA enhancement for receipt clarity"""
        
        # Step 1: Smart resize for optimal processing
        if max(image.width, image.height) > 3000:
            ratio = 3000 / max(image.width, image.height)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Step 2: Advanced contrast enhancement
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(self.enhancement_params['contrast_boost'])
        
        # Step 3: Intelligent sharpening
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(self.enhancement_params['sharpness_boost'])
        
        # Step 4: Brightness optimization
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(self.enhancement_params['brightness_adjust'])
        
        # Step 5: Advanced noise reduction
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        return image

    def _detect_receipt_edges(self, image: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        """🔍 Advanced edge detection to find receipt boundaries"""
        try:
            # Convert PIL to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Edge detection using Canny
            edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Find the largest rectangular contour (likely the receipt)
            receipt_contour = None
            max_area = 0
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Filter by area constraints
                if (self.enhancement_params['min_receipt_area'] < area < 
                    self.enhancement_params['max_receipt_area']):
                    
                    # Approximate contour to polygon
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    # Check if it's roughly rectangular (4 corners)
                    if len(approx) >= 4 and area > max_area:
                        max_area = area
                        receipt_contour = approx
            
            if receipt_contour is not None:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(receipt_contour)
                
                # Add smart padding (5% of dimensions)
                padding_x = int(w * 0.05)
                padding_y = int(h * 0.05)
                
                x = max(0, x - padding_x)
                y = max(0, y - padding_y)
                w = min(image.width - x, w + 2 * padding_x)
                h = min(image.height - y, h + 2 * padding_y)
                
                return (x, y, x + w, y + h)
                
        except Exception as e:
            logger.warning(f"Edge detection failed: {e}")
        
        return None

    def _smart_crop_receipt(self, image: Image.Image, bounds: Tuple[int, int, int, int]) -> Image.Image:
        """✂️ Smart cropping with receipt boundary detection"""
        x1, y1, x2, y2 = bounds
        
        # Ensure bounds are within image
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(image.width, x2)
        y2 = min(image.height, y2)
        
        # Crop to detected receipt area
        cropped = image.crop((x1, y1, x2, y2))
        
        return cropped

    def _final_enhancement(self, image: Image.Image) -> Image.Image:
        """🎨 Final enhancement pass for optimal OCR"""
        
        # Auto-level the image for better contrast
        image = ImageOps.autocontrast(image, cutoff=2)
        
        # Additional sharpening for text clarity
        image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
        
        return image

    def _standard_enhancement(self, image: Image.Image) -> Image.Image:
        """Standard enhancement when edge detection fails"""
        
        # Apply moderate enhancements
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        return image

    def _calculate_image_metrics(self, original: Image.Image, enhanced: Image.Image) -> Dict:
        """Calculate enhancement quality metrics"""
        try:
            # Convert to numpy arrays for analysis
            orig_array = np.array(original.convert('L'))  # Grayscale
            enh_array = np.array(enhanced.convert('L'))
            
            # Calculate metrics
            orig_std = np.std(orig_array)
            enh_std = np.std(enhanced.convert('L'))
            
            metrics = {
                'contrast_improvement': round(enh_std / orig_std if orig_std > 0 else 1.0, 2),
                'size_reduction': round((1 - enhanced.width * enhanced.height / (original.width * original.height)) * 100, 1),
                'edge_sharpness': round(float(np.mean(np.gradient(enh_array))), 2)
            }
            
            return metrics
            
        except Exception as e:
            logger.warning(f"Metrics calculation failed: {e}")
            return {'contrast_improvement': 1.0, 'size_reduction': 0, 'edge_sharpness': 0}

    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return ('.' in filename and 
                filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS)

    def process_receipt_images_ultra_fast(self, processed_files: List[Dict], receipt_processor) -> List[Dict]:
        """Process receipt images with ultra-fast OCR pipeline"""
        import concurrent.futures
        
        start_time = time.time()
        processed_receipts = []
        
        def extract_receipt_data(file_info):
            try:
                if receipt_processor and hasattr(receipt_processor, 'extract_receipt_data'):
                    # Use advanced OCR processor
                    result = receipt_processor.extract_receipt_data(file_info['filepath'])
                    if result:
                        result.update({
                            'source_file': file_info,
                            'extraction_method': 'advanced_ocr',
                            'processing_speed': 'ultra_fast'
                        })
                        return result
                
                # Fallback: basic file info
                return {
                    'source_file': file_info,
                    'merchant': 'Unknown (OCR Required)',
                    'total_amount': 0,
                    'extraction_method': 'file_info_only',
                    'processing_speed': 'ultra_fast'
                }
                
            except Exception as e:
                logger.error(f"Receipt extraction failed for {file_info.get('filename', 'unknown')}: {e}")
                return None
        
        # Process receipts in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            extraction_futures = [executor.submit(extract_receipt_data, file_info) for file_info in processed_files]
            
            for future in concurrent.futures.as_completed(extraction_futures):
                result = future.result()
                if result:
                    processed_receipts.append(result)
        
        processing_time = time.time() - start_time
        logger.info(f"🚀 Ultra-fast OCR complete: {len(processed_receipts)} receipts in {processing_time:.2f}s")
        
        return processed_receipts


# Legacy class for backward compatibility
class CameraScanner(UltraFastReceiptScanner):
    """Legacy camera scanner - now inherits ultra-fast functionality"""
    pass
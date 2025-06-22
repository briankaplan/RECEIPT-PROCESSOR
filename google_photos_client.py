#!/usr/bin/env python3
"""
Google Photos API client for receipt scanning and image processing
Automatically finds receipt images in Google Photos and processes them
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from config import Config

logger = logging.getLogger(__name__)

class GooglePhotosClient:
    """Google Photos API client for automatic receipt discovery"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/photoslibrary.readonly',
        'https://www.googleapis.com/auth/photoslibrary.sharing'
    ]
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Photos API service"""
        try:
            creds_path = Config.GOOGLE_PHOTOS_CREDENTIALS_PATH
            token_path = Config.GOOGLE_PHOTOS_TOKEN_PATH
            
            if os.path.exists(token_path):
                self.credentials = Credentials.from_authorized_user_file(token_path, self.SCOPES)
            
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    logger.warning("Google Photos credentials not found or invalid")
                    return
            
            self.service = build('photoslibrary', 'v1', credentials=self.credentials)
            logger.info("Google Photos API client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Photos client: {e}")
    
    def is_connected(self) -> bool:
        """Check if Google Photos API is connected"""
        return self.service is not None
    
    def search_receipt_photos(self, days_back: int = 30) -> List[Dict]:
        """Search for receipt-like photos in Google Photos"""
        if not self.is_connected():
            return []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Search for photos with potential receipt content
            search_filters = {
                'dateFilter': {
                    'ranges': [{
                        'startDate': {
                            'year': start_date.year,
                            'month': start_date.month,
                            'day': start_date.day
                        },
                        'endDate': {
                            'year': end_date.year,
                            'month': end_date.month,
                            'day': end_date.day
                        }
                    }]
                },
                'mediaTypeFilter': {
                    'mediaTypes': ['PHOTO']
                }
            }
            
            results = self.service.mediaItems().search(
                body={'filters': search_filters, 'pageSize': 100}
            ).execute()
            
            photos = []
            for item in results.get('mediaItems', []):
                if self._is_potential_receipt(item):
                    photos.append({
                        'id': item['id'],
                        'filename': item.get('filename', ''),
                        'creation_time': item.get('mediaMetadata', {}).get('creationTime', ''),
                        'base_url': item['baseUrl'],
                        'description': item.get('description', ''),
                        'width': item.get('mediaMetadata', {}).get('width', 0),
                        'height': item.get('mediaMetadata', {}).get('height', 0)
                    })
            
            logger.info(f"Found {len(photos)} potential receipt photos")
            return photos
            
        except Exception as e:
            logger.error(f"Failed to search Google Photos: {e}")
            return []
    
    def _is_potential_receipt(self, item: Dict) -> bool:
        """Determine if photo is likely a receipt"""
        filename = item.get('filename', '').lower()
        description = item.get('description', '').lower()
        
        # Check for receipt-related keywords
        receipt_keywords = [
            'receipt', 'bill', 'invoice', 'purchase', 'payment', 'ticket',
            'restaurant', 'store', 'shop', 'total', 'tax', 'subtotal'
        ]
        
        text_to_check = f"{filename} {description}"
        
        # Check if any keywords are present
        has_keywords = any(keyword in text_to_check for keyword in receipt_keywords)
        
        # Check image dimensions (receipts are usually tall and narrow)
        metadata = item.get('mediaMetadata', {})
        width = int(metadata.get('width', 0))
        height = int(metadata.get('height', 0))
        
        is_receipt_shape = False
        if width > 0 and height > 0:
            aspect_ratio = height / width
            # Receipts typically have aspect ratio > 1.2 (taller than wide)
            is_receipt_shape = aspect_ratio > 1.2
        
        return has_keywords or is_receipt_shape
    
    def download_photo(self, photo_id: str, save_path: str) -> bool:
        """Download a photo from Google Photos"""
        if not self.is_connected():
            return False
        
        try:
            # Get media item details
            item = self.service.mediaItems().get(mediaItemId=photo_id).execute()
            
            # Download the image
            download_url = f"{item['baseUrl']}=d"  # =d parameter for download
            response = requests.get(download_url)
            
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Downloaded photo to {save_path}")
                return True
            else:
                logger.error(f"Failed to download photo: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to download photo {photo_id}: {e}")
            return False
    
    def process_receipt_photos(self, photos: List[Dict], receipt_processor) -> List[Dict]:
        """Process downloaded receipt photos"""
        processed_receipts = []
        
        for photo in photos:
            try:
                # Download photo to temporary location
                temp_path = f"downloads/google_photos_{photo['id']}.jpg"
                os.makedirs('downloads', exist_ok=True)
                
                if self.download_photo(photo['id'], temp_path):
                    # Process the receipt
                    receipt_data = receipt_processor.extract_receipt_data(temp_path)
                    if receipt_data:
                        receipt_data['source_type'] = 'google_photos'
                        receipt_data['google_photos_id'] = photo['id']
                        receipt_data['original_filename'] = photo['filename']
                        receipt_data['creation_time'] = photo['creation_time']
                        processed_receipts.append(receipt_data)
                    
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
            except Exception as e:
                logger.error(f"Failed to process photo {photo['id']}: {e}")
        
        logger.info(f"Processed {len(processed_receipts)} receipt photos from Google Photos")
        return processed_receipts
    
    def get_stats(self) -> Dict:
        """Get Google Photos client statistics"""
        return {
            'connected': self.is_connected(),
            'service_available': self.service is not None,
            'credentials_valid': self.credentials and self.credentials.valid if self.credentials else False
        }
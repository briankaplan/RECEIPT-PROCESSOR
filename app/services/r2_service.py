"""
R2 storage service for file uploads
"""

import logging
from typing import Optional
from ..config import Config

logger = logging.getLogger(__name__)

class R2Service:
    """R2 storage service wrapper for the application"""
    
    def __init__(self):
        self.client = SafeR2Client()
    
    def is_connected(self) -> bool:
        """Check if R2 is connected"""
        return self.client.is_connected()
    
    def upload_file(self, file_data: bytes, filename: str, content_type: str = None) -> Optional[str]:
        """Upload file to R2 safely"""
        return self.client.upload_file(file_data, filename, content_type)
    
    def delete_file(self, filename: str) -> bool:
        """Delete file from R2"""
        return self.client.delete_file(filename)
    
    def get_file_url(self, filename: str) -> Optional[str]:
        """Get public URL for file"""
        return self.client.get_file_url(filename)
    
    def list_files(self, prefix: str = "") -> list:
        """List files in R2 bucket"""
        return self.client.list_files(prefix)

class SafeR2Client:
    """R2 storage client with error handling"""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Connect to R2 storage with proper error handling"""
        try:
            from r2_client import R2Client
            self.client = R2Client()
            if self.client.is_connected():
                self.connected = True
                logger.info("✅ R2 storage connected")
            else:
                logger.warning("R2 storage not available")
        except Exception as e:
            logger.warning(f"R2 connection failed: {e}")
            self.connected = False
    
    def is_connected(self) -> bool:
        """Check if R2 is connected"""
        return self.connected and self.client and self.client.is_connected()
    
    def upload_file(self, file_data: bytes, filename: str, content_type: str = None) -> Optional[str]:
        """Upload file to R2 safely"""
        try:
            if not self.is_connected():
                return None
            return self.client.upload_file(file_data, filename, content_type)
        except Exception as e:
            logger.error(f"R2 upload failed: {e}")
            return None
    
    def delete_file(self, filename: str) -> bool:
        """Delete file from R2"""
        try:
            if not self.is_connected():
                return False
            return self.client.delete_file(filename)
        except Exception as e:
            logger.error(f"R2 delete failed: {e}")
            return False
    
    def get_file_url(self, filename: str) -> Optional[str]:
        """Get public URL for file"""
        try:
            if not self.is_connected():
                return None
            return self.client.get_file_url(filename)
        except Exception as e:
            logger.error(f"R2 get URL failed: {e}")
            return None
    
    def list_files(self, prefix: str = "") -> list:
        """List files in R2 bucket"""
        try:
            if not self.is_connected():
                return []
            return self.client.list_files(prefix)
        except Exception as e:
            logger.error(f"R2 list files failed: {e}")
            return [] 
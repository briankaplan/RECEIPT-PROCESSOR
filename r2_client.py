import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

class R2Client:
    """Cloudflare R2 client for storing receipt files and attachments"""
    
    def __init__(self):
        self.client = None
        self.bucket_name = None
        self._connect()
    
    def _connect(self):
        """Connect to Cloudflare R2"""
        try:
            # Get R2 credentials from environment
            endpoint = os.getenv('R2_ENDPOINT')
            access_key = os.getenv('R2_ACCESS_KEY')
            secret_key = os.getenv('R2_SECRET_KEY')
            self.bucket_name = os.getenv('R2_BUCKET', 'expensesbk')
            
            if not all([endpoint, access_key, secret_key]):
                logger.warning("R2 credentials not found in environment variables")
                return False
            
            # Create R2 client using your endpoint
            self.client = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name='auto'
            )
            
            # Test connection by listing buckets
            self.client.list_buckets()
            logger.info(f"Connected to Cloudflare R2, using bucket: {self.bucket_name}")
            
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to R2: {str(e)}")
            self.client = None
            return False
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"R2 bucket '{self.bucket_name}' exists")
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                try:
                    self.client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created R2 bucket '{self.bucket_name}'")
                except Exception as create_error:
                    logger.error(f"Failed to create bucket: {str(create_error)}")
            else:
                logger.error(f"Error checking bucket: {str(e)}")
    
    def is_connected(self) -> bool:
        """Check if R2 is connected"""
        if not self.client:
            return False
        
        try:
            self.client.list_buckets()
            return True
        except Exception:
            return False
    
    def upload_file(self, file_path: str, key: str, metadata: Optional[Dict] = None) -> bool:
        """Upload a file to R2"""
        if not self.is_connected():
            logger.error("R2 not connected")
            return False
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False
        
        try:
            # Prepare metadata
            upload_metadata = {
                'uploaded_at': datetime.utcnow().isoformat(),
                'original_filename': os.path.basename(file_path),
                'file_size': str(os.path.getsize(file_path))
            }
            
            if metadata:
                upload_metadata.update({k: str(v) for k, v in metadata.items()})
            
            # Upload file
            self.client.upload_file(
                file_path,
                self.bucket_name,
                key,
                ExtraArgs={
                    'Metadata': upload_metadata,
                    'ContentType': self._get_content_type(file_path)
                }
            )
            
            logger.info(f"Uploaded {file_path} to R2 as {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading file to R2: {str(e)}")
            return False
    
    def upload_receipt_attachment(self, file_path: str, email_id: str, account: str, 
                                attachment_info: Dict) -> Optional[str]:
        """Upload receipt attachment with organized naming"""
        if not self.is_connected():
            return None
        
        try:
            # Create organized key structure
            account_safe = account.replace('@', '_at_').replace('.', '_')
            date_str = datetime.utcnow().strftime('%Y/%m/%d')
            filename = os.path.basename(file_path)
            
            key = f"receipts/{account_safe}/{date_str}/{email_id}_{filename}"
            
            # Metadata for the receipt
            metadata = {
                'email_id': email_id,
                'account': account,
                'attachment_size': str(attachment_info.get('size', 0)),
                'mime_type': attachment_info.get('mime_type', 'unknown'),
                'message_id': attachment_info.get('message_id', '')
            }
            
            if self.upload_file(file_path, key, metadata):
                return key
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error uploading receipt attachment: {str(e)}")
            return None
    
    def download_file(self, key: str, local_path: str) -> bool:
        """Download a file from R2"""
        if not self.is_connected():
            logger.error("R2 not connected")
            return False
        
        try:
            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.client.download_file(self.bucket_name, key, local_path)
            logger.info(f"Downloaded {key} from R2 to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading file from R2: {str(e)}")
            return False
    
    def list_files(self, prefix: str = "", limit: int = 100) -> List[Dict]:
        """List files in R2 bucket"""
        if not self.is_connected():
            logger.error("R2 not connected")
            return []
        
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=limit
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag'].strip('"')
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing files from R2: {str(e)}")
            return []
    
    def get_file_metadata(self, key: str) -> Optional[Dict]:
        """Get metadata for a specific file"""
        if not self.is_connected():
            return None
        
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=key)
            
            return {
                'key': key,
                'size': response['ContentLength'],
                'last_modified': response['LastModified'].isoformat(),
                'content_type': response.get('ContentType', 'unknown'),
                'metadata': response.get('Metadata', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting file metadata: {str(e)}")
            return None
    
    def delete_file(self, key: str) -> bool:
        """Delete a file from R2"""
        if not self.is_connected():
            logger.error("R2 not connected")
            return False
        
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Deleted {key} from R2")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file from R2: {str(e)}")
            return False
    
    def get_file_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate a presigned URL for file access"""
        if not self.is_connected():
            return None
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )
            return url
            
        except Exception as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            return None
    
    def _get_content_type(self, file_path: str) -> str:
        """Get content type based on file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        
        content_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.json': 'application/json',
            '.txt': 'text/plain'
        }
        
        return content_types.get(ext, 'application/octet-stream')
    
    def get_stats(self) -> Dict:
        """Get R2 storage statistics"""
        if not self.is_connected():
            return {
                'connected': False,
                'total_files': 0,
                'total_size': 0,
                'receipts_count': 0
            }
        
        try:
            # Get all files
            all_files = self.list_files(limit=1000)
            total_size = sum(f['size'] for f in all_files)
            
            # Count receipts
            receipts = [f for f in all_files if f['key'].startswith('receipts/')]
            
            return {
                'connected': True,
                'total_files': len(all_files),
                'total_size': total_size,
                'receipts_count': len(receipts),
                'bucket_name': self.bucket_name
            }
            
        except Exception as e:
            logger.error(f"Error getting R2 stats: {str(e)}")
            return {
                'connected': False,
                'total_files': 0,
                'total_size': 0,
                'receipts_count': 0
            }
#!/usr/bin/env python3
"""
Enhanced Attachment Handler Module
Advanced email attachment processing with security and efficiency
"""

import os
import logging
import tempfile
import asyncio
import aiofiles
from typing import Optional, List, Dict, Set, Tuple, Union
from pathlib import Path
import mimetypes
import hashlib
import time
import json
import re
from datetime import datetime, timedelta
import magic  # python-magic for better MIME detection
import zipfile
import tarfile
from dataclasses import dataclass, asdict

@dataclass
class AttachmentInfo:
    """Enhanced attachment information"""
    message_id: str
    attachment_id: str
    original_filename: str
    safe_filename: str
    file_path: str
    mime_type: str
    file_size: int
    file_hash: str
    created_at: str
    is_safe: bool
    scan_results: Dict
    extracted_text: Optional[str] = None

class EnhancedAttachmentHandler:
    """Enhanced attachment handler with security and performance features"""
    
    # Security settings
    ALLOWED_EXTENSIONS = {
        '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
        '.txt', '.csv', '.xlsx', '.xls', '.doc', '.docx',
        '.html', '.htm', '.xml', '.json'
    }
    
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs',
        '.js', '.jar', '.app', '.dmg', '.pkg', '.deb', '.rpm'
    }
    
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_TOTAL_SIZE = 200 * 1024 * 1024  # 200MB
    
    def __init__(self, temp_dir: Optional[str] = None, config: Optional[Dict] = None):
        """Initialize enhanced attachment handler"""
        self.config = config or {}
        
        # Directory setup
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.attachment_dir = Path(self.temp_dir) / "email_attachments_enhanced"
        self.metadata_dir = self.attachment_dir / "metadata"
        self.quarantine_dir = self.attachment_dir / "quarantine"
        
        # Create directories
        for directory in [self.attachment_dir, self.metadata_dir, self.quarantine_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Tracking
        self.downloaded_files: Dict[str, AttachmentInfo] = {}
        self.total_size = 0
        self.security_violations: List[Dict] = []
        
        # Performance settings
        self.max_concurrent_downloads = self.config.get('max_concurrent_downloads', 5)
        self.download_semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        
        # Load existing metadata
        # asyncio.create_task(self._load_metadata())
        # (moved to initialize)
        
        # Security settings from config
        self.security_enabled = self.config.get('security_enabled', True)
        self.quarantine_suspicious = self.config.get('quarantine_suspicious', True)
        self.max_file_size = self.config.get('max_file_size', self.MAX_FILE_SIZE)
        
        logging.info(f"📎 Enhanced attachment handler initialized: {self.attachment_dir}")
    
    async def initialize(self):
        """Async initialization for loading metadata"""
        await self._load_metadata()
    
    async def _load_metadata(self):
        """Load existing attachment metadata"""
        try:
            metadata_file = self.metadata_dir / "attachments.json"
            if metadata_file.exists():
                async with aiofiles.open(metadata_file, 'r') as f:
                    data = json.loads(await f.read())
                    
                for key, info_dict in data.items():
                    self.downloaded_files[key] = AttachmentInfo(**info_dict)
                    
                logging.info(f"📋 Loaded metadata for {len(self.downloaded_files)} attachments")
        except Exception as e:
            logging.warning(f"⚠️ Failed to load attachment metadata: {e}")
    
    async def _save_metadata(self):
        """Save attachment metadata"""
        try:
            metadata_file = self.metadata_dir / "attachments.json"
            data = {key: asdict(info) for key, info in self.downloaded_files.items()}
            
            async with aiofiles.open(metadata_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
                
        except Exception as e:
            logging.error(f"❌ Failed to save attachment metadata: {e}")
    
    def create_safe_filename(self, original_filename: str, message_id: str, attachment_id: str) -> str:
        """Create a safe filename with comprehensive sanitization"""
        
        # Basic cleaning
        filename = re.sub(r'[<>:"/\\|?*]', '_', original_filename)
        filename = re.sub(r'[^\w\s.-]', '', filename)
        filename = re.sub(r'\s+', '_', filename)
        
        # Remove dangerous patterns
        filename = re.sub(r'(\.\.)+', '.', filename)
        filename = filename.strip('.')
        
        # Limit length
        name, ext = os.path.splitext(filename)
        if len(name) > 50:
            name = name[:50]
        
        # Create unique identifier
        unique_id = hashlib.md5(f"{message_id}_{attachment_id}".encode()).hexdigest()[:8]
        
        # Combine for final filename
        safe_filename = f"{unique_id}_{name}{ext}"
        
        # Final length check
        if len(safe_filename) > 200:
            safe_filename = f"{unique_id}{ext}"
        
        return safe_filename
    
    async def security_scan(self, file_path: Path, original_filename: str) -> Dict:
        """Comprehensive security scan of attachment"""
        
        scan_results = {
            'is_safe': True,
            'warnings': [],
            'violations': [],
            'mime_type_verified': False,
            'size_check': False,
            'extension_check': False,
            'content_check': False
        }
        
        try:
            # File size check
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                scan_results['violations'].append(f"File size {file_size} exceeds limit {self.max_file_size}")
                scan_results['is_safe'] = False
            else:
                scan_results['size_check'] = True
            
            # Extension check
            ext = Path(original_filename).suffix.lower()
            if ext in self.DANGEROUS_EXTENSIONS:
                scan_results['violations'].append(f"Dangerous file extension: {ext}")
                scan_results['is_safe'] = False
            elif ext in self.ALLOWED_EXTENSIONS:
                scan_results['extension_check'] = True
            else:
                scan_results['warnings'].append(f"Unknown file extension: {ext}")
            
            # MIME type verification
            try:
                detected_mime = magic.from_file(str(file_path), mime=True)
                expected_mime = mimetypes.guess_type(original_filename)[0]
                
                if expected_mime and detected_mime != expected_mime:
                    scan_results['warnings'].append(
                        f"MIME type mismatch: expected {expected_mime}, got {detected_mime}"
                    )
                else:
                    scan_results['mime_type_verified'] = True
                    
            except Exception as e:
                scan_results['warnings'].append(f"MIME type detection failed: {e}")
            
            # Content-based checks
            try:
                await self._content_security_check(file_path, scan_results)
                scan_results['content_check'] = True
            except Exception as e:
                scan_results['warnings'].append(f"Content check failed: {e}")
            
            # Archive checks
            if ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
                await self._archive_security_check(file_path, scan_results)
            
        except Exception as e:
            scan_results['violations'].append(f"Security scan error: {e}")
            scan_results['is_safe'] = False
        
        return scan_results
    
    async def _content_security_check(self, file_path: Path, scan_results: Dict):
        """Check file content for security issues"""
        
        try:
            # Read first few KB to check for suspicious patterns
            async with aiofiles.open(file_path, 'rb') as f:
                header = await f.read(8192)  # 8KB header
            
            # Check for executable signatures
            exe_signatures = [
                b'\x4d\x5a',  # PE executable
                b'\x7f\x45\x4c\x46',  # ELF executable
                b'\xca\xfe\xba\xbe',  # Mach-O executable
                b'\xfe\xed\xfa',  # Mach-O executable
            ]
            
            for sig in exe_signatures:
                if header.startswith(sig):
                    scan_results['violations'].append("File contains executable signature")
                    scan_results['is_safe'] = False
                    return
            
            # Check for script content in non-script files
            script_patterns = [
                rb'<script[^>]*>',
                rb'javascript:',
                rb'vbscript:',
                rb'powershell',
                rb'cmd\.exe',
                rb'system\(',
                rb'exec\(',
                rb'eval\('
            ]
            
            header_lower = header.lower()
            for pattern in script_patterns:
                if re.search(pattern, header_lower):
                    scan_results['warnings'].append(f"Suspicious script pattern found")
                    break
            
        except Exception as e:
            scan_results['warnings'].append(f"Content check error: {e}")
    
    async def _archive_security_check(self, file_path: Path, scan_results: Dict):
        """Security check for archive files"""
        
        try:
            # Check for zip bombs and path traversal
            if file_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(file_path, 'r') as zf:
                    total_uncompressed = 0
                    for info in zf.infolist():
                        # Check for path traversal
                        if '..' in info.filename or info.filename.startswith('/'):
                            scan_results['violations'].append(f"Path traversal in archive: {info.filename}")
                            scan_results['is_safe'] = False
                        
                        # Check for zip bomb
                        total_uncompressed += info.file_size
                        if total_uncompressed > 1024 * 1024 * 1024:  # 1GB limit
                            scan_results['violations'].append("Potential zip bomb detected")
                            scan_results['is_safe'] = False
                            break
            
        except Exception as e:
            scan_results['warnings'].append(f"Archive check error: {e}")
    
    async def download_attachment_enhanced(self, gmail_service, message_id: str, 
                                         attachment_id: str, filename: str) -> Optional[AttachmentInfo]:
        """Enhanced attachment download with security and performance"""
        
        async with self.download_semaphore:
            try:
                # Check if already downloaded
                key = f"{message_id}_{attachment_id}"
                if key in self.downloaded_files:
                    existing = self.downloaded_files[key]
                    if Path(existing.file_path).exists():
                        logging.info(f"📎 Using cached attachment: {filename}")
                        return existing
                
                # Create safe filename
                safe_filename = self.create_safe_filename(filename, message_id, attachment_id)
                file_path = self.attachment_dir / safe_filename
                
                # Download attachment
                logging.info(f"⬇️ Downloading attachment: {filename}")
                
                attachment_data = gmail_service.users().messages().attachments().get(
                    userId='me',
                    messageId=message_id,
                    id=attachment_id
                ).execute()
                
                # Decode data
                import base64
                file_data = base64.urlsafe_b64decode(attachment_data['data'])
                
                # Check size before saving
                if len(file_data) > self.max_file_size:
                    logging.error(f"❌ Attachment too large: {len(file_data)} bytes")
                    return None
                
                # Check total size limit
                if self.total_size + len(file_data) > self.MAX_TOTAL_SIZE:
                    logging.error(f"❌ Total attachment size limit exceeded")
                    await self._cleanup_oldest_attachments()
                
                # Save file
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(file_data)
                
                # Calculate file hash
                file_hash = hashlib.sha256(file_data).hexdigest()
                
                # Security scan
                scan_results = {'is_safe': True, 'warnings': [], 'violations': []}
                if self.security_enabled:
                    scan_results = await self.security_scan(file_path, filename)
                
                # Handle security violations
                final_path = file_path
                if not scan_results['is_safe'] and self.quarantine_suspicious:
                    quarantine_path = self.quarantine_dir / safe_filename
                    file_path.rename(quarantine_path)
                    final_path = quarantine_path
                    logging.warning(f"⚠️ Quarantined suspicious file: {filename}")
                
                # Create attachment info
                attachment_info = AttachmentInfo(
                    message_id=message_id,
                    attachment_id=attachment_id,
                    original_filename=filename,
                    safe_filename=safe_filename,
                    file_path=str(final_path),
                    mime_type=mimetypes.guess_type(filename)[0] or 'application/octet-stream',
                    file_size=len(file_data),
                    file_hash=file_hash,
                    created_at=datetime.now().isoformat(),
                    is_safe=scan_results['is_safe'],
                    scan_results=scan_results
                )
                
                # Store in tracking
                self.downloaded_files[key] = attachment_info
                self.total_size += len(file_data)
                
                # Save metadata
                await self._save_metadata()
                
                # Log security issues
                if scan_results['violations']:
                    self.security_violations.append({
                        'filename': filename,
                        'message_id': message_id,
                        'violations': scan_results['violations'],
                        'timestamp': datetime.now().isoformat()
                    })
                
                logging.info(f"✅ Downloaded attachment: {filename} ({len(file_data)} bytes)")
                return attachment_info
                
            except Exception as e:
                logging.error(f"❌ Failed to download attachment {filename}: {e}")
                return None
    
    async def extract_text_from_attachment(self, attachment_info: AttachmentInfo) -> Optional[str]:
        """Extract text content from attachments"""
        
        if not attachment_info.is_safe:
            logging.warning(f"⚠️ Skipping text extraction from unsafe file: {attachment_info.original_filename}")
            return None
        
        file_path = Path(attachment_info.file_path)
        if not file_path.exists():
            return None
        
        try:
            # PDF extraction
            if attachment_info.mime_type == 'application/pdf':
                return await self._extract_pdf_text(file_path)
            
            # Office documents
            elif attachment_info.mime_type in [
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/msword'
            ]:
                return await self._extract_docx_text(file_path)
            
            # Plain text
            elif attachment_info.mime_type.startswith('text/'):
                async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return await f.read()
            
            # HTML
            elif attachment_info.mime_type == 'text/html':
                return await self._extract_html_text(file_path)
            
            return None
            
        except Exception as e:
            logging.error(f"❌ Text extraction failed for {attachment_info.original_filename}: {e}")
            return None
    
    async def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF using PyPDF2 or pdfplumber"""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except ImportError:
            logging.warning("⚠️ PyPDF2 not available for PDF text extraction")
            return ""
        except Exception as e:
            logging.error(f"❌ PDF text extraction error: {e}")
            return ""
    
    async def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text from DOCX files"""
        try:
            import docx
            doc = docx.Document(file_path)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return "\n".join(text)
        except ImportError:
            logging.warning("⚠️ python-docx not available for DOCX text extraction")
            return ""
        except Exception as e:
            logging.error(f"❌ DOCX text extraction error: {e}")
            return ""
    
    async def _extract_html_text(self, file_path: Path) -> str:
        """Extract text from HTML files"""
        try:
            from bs4 import BeautifulSoup
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = await f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except ImportError:
            logging.warning("⚠️ BeautifulSoup not available for HTML text extraction")
            return ""
        except Exception as e:
            logging.error(f"❌ HTML text extraction error: {e}")
            return ""
    
    async def batch_download_attachments(self, gmail_service, attachments: List[Tuple[str, str, str]]) -> List[AttachmentInfo]:
        """Download multiple attachments concurrently"""
        
        tasks = []
        for message_id, attachment_id, filename in attachments:
            task = self.download_attachment_enhanced(gmail_service, message_id, attachment_id, filename)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_downloads = []
        for result in results:
            if isinstance(result, AttachmentInfo):
                successful_downloads.append(result)
            elif isinstance(result, Exception):
                logging.error(f"❌ Batch download error: {result}")
        
        logging.info(f"📦 Batch download complete: {len(successful_downloads)}/{len(attachments)} successful")
        return successful_downloads
    
    async def _cleanup_oldest_attachments(self):
        """Clean up oldest attachments to make space"""
        
        if not self.downloaded_files:
            return
        
        # Sort by creation time
        sorted_attachments = sorted(
            self.downloaded_files.items(),
            key=lambda x: x[1].created_at
        )
        
        # Remove oldest 25%
        to_remove = len(sorted_attachments) // 4
        for i in range(to_remove):
            key, attachment_info = sorted_attachments[i]
            await self._remove_attachment(key)
        
        logging.info(f"🧹 Cleaned up {to_remove} oldest attachments")
    
    async def _remove_attachment(self, key: str):
        """Remove a specific attachment"""
        
        if key not in self.downloaded_files:
            return
        
        attachment_info = self.downloaded_files[key]
        
        try:
            # Remove file
            file_path = Path(attachment_info.file_path)
            if file_path.exists():
                file_path.unlink()
            
            # Update tracking
            self.total_size -= attachment_info.file_size
            del self.downloaded_files[key]
            
        except Exception as e:
            logging.error(f"❌ Failed to remove attachment: {e}")
    
    async def cleanup_old_attachments(self, max_age_hours: int = 24):
        """Clean up old attachments with enhanced logic"""
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            to_remove = []
            
            for key, attachment_info in self.downloaded_files.items():
                created_at = datetime.fromisoformat(attachment_info.created_at)
                if created_at < cutoff_time:
                    to_remove.append(key)
            
            for key in to_remove:
                await self._remove_attachment(key)
            
            # Save updated metadata
            await self._save_metadata()
            
            logging.info(f"🧹 Cleaned up {len(to_remove)} old attachments")
            
        except Exception as e:
            logging.error(f"❌ Cleanup failed: {e}")
    
    async def get_security_report(self) -> Dict:
        """Generate comprehensive security report"""
        
        safe_count = sum(1 for info in self.downloaded_files.values() if info.is_safe)
        unsafe_count = len(self.downloaded_files) - safe_count
        
        return {
            'total_attachments': len(self.downloaded_files),
            'safe_attachments': safe_count,
            'unsafe_attachments': unsafe_count,
            'quarantined_count': len(list(self.quarantine_dir.glob('*'))),
            'total_size_mb': self.total_size / (1024 * 1024),
            'security_violations': self.security_violations,
            'generated_at': datetime.now().isoformat()
        }
    
    def get_attachment_by_hash(self, file_hash: str) -> Optional[AttachmentInfo]:
        """Get attachment by file hash (deduplication)"""
        
        for attachment_info in self.downloaded_files.values():
            if attachment_info.file_hash == file_hash:
                return attachment_info
        return None
    
    async def health_check(self) -> Dict:
        """Comprehensive health check"""
        
        health = {
            'status': 'healthy',
            'attachment_dir_exists': self.attachment_dir.exists(),
            'attachment_count': len(self.downloaded_files),
            'total_size_mb': self.total_size / (1024 * 1024),
            'quarantine_count': len(list(self.quarantine_dir.glob('*'))),
            'security_enabled': self.security_enabled,
            'last_check': datetime.now().isoformat()
        }
        
        # Check disk space
        try:
            stat = os.statvfs(self.attachment_dir)
            free_space = stat.f_bavail * stat.f_frsize
            health['free_space_mb'] = free_space / (1024 * 1024)
            
            if free_space < 100 * 1024 * 1024:  # Less than 100MB
                health['status'] = 'warning'
                health['warnings'] = ['Low disk space']
                
        except Exception as e:
            health['status'] = 'error'
            health['error'] = str(e)
        
        return health
    
    async def cleanup_all_attachments(self):
        """Clean up all attachments"""
        
        try:
            # Remove all files
            for path in self.attachment_dir.glob("**/*"):
                if path.is_file():
                    path.unlink()
            
            # Clear tracking
            self.downloaded_files.clear()
            self.total_size = 0
            self.security_violations.clear()
            
            # Save empty metadata
            await self._save_metadata()
            
            logging.info("🧹 All attachments cleaned up")
            
        except Exception as e:
            logging.error(f"❌ Failed to cleanup all attachments: {e}")

# Integration helper for expense processor
async def download_receipt_attachments(gmail_service, messages: List[Dict], 
                                     config: Optional[Dict] = None) -> Dict[str, List[AttachmentInfo]]:
    """Helper function to download attachments from receipt emails"""
    
    handler = EnhancedAttachmentHandler(config=config)
    results = {}
    
    for message in messages:
        message_id = message.get('id')
        if not message_id:
            continue
        
        try:
            # Extract attachment info from message
            attachments = []
            payload = message.get('payload', {})
            
            # Find attachment parts
            parts = payload.get('parts', [])
            if not parts and payload.get('body', {}).get('attachmentId'):
                parts = [payload]
            
            for part in parts:
                body = part.get('body', {})
                attachment_id = body.get('attachmentId')
                filename = part.get('filename', '')
                
                if attachment_id and filename:
                    attachments.append((message_id, attachment_id, filename))
            
            # Download attachments
            if attachments:
                downloaded = await handler.batch_download_attachments(gmail_service, attachments)
                results[message_id] = downloaded
                
                # Extract text from safe attachments
                for attachment_info in downloaded:
                    if attachment_info.is_safe:
                        text = await handler.extract_text_from_attachment(attachment_info)
                        attachment_info.extracted_text = text
            
        except Exception as e:
            logging.error(f"❌ Failed to process attachments for message {message_id}: {e}")
            continue
    
    return results

# Test the enhanced attachment handler
if __name__ == "__main__":
    import asyncio
    
    async def test_attachment_handler():
        config = {
            'security_enabled': True,
            'quarantine_suspicious': True,
            'max_file_size': 10 * 1024 * 1024  # 10MB
        }
        
        handler = EnhancedAttachmentHandler(config=config)
        
        # Test health check
        health = await handler.health_check()
        print(f"🏥 Health check: {health}")
        
        # Test security report
        security_report = await handler.get_security_report()
        print(f"🔒 Security report: {security_report}")
        
        print("✅ Enhanced attachment handler test complete")
    
    # Run test
    print("🧪 Testing Enhanced Attachment Handler")
    asyncio.run(test_attachment_handler())
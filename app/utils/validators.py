"""
Validation utilities for the Receipt Processor application
"""

import os
import magic
import logging
from typing import Union, Optional
from werkzeug.utils import secure_filename
from ..config import Config
import re

logger = logging.getLogger(__name__)

def validate_upload(file_data: Union[bytes, 'FileStorage'], filename: str) -> None:
    """
    Validate uploaded file for security and format
    
    Args:
        file_data: File data as bytes or FileStorage object
        filename: Original filename
        
    Raises:
        ValueError: If file validation fails
    """
    
    # Check file extension
    if not any(filename.lower().endswith(ext) for ext in Config.ALLOWED_EXTENSIONS):
        raise ValueError(f"Invalid file type. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}")
    
    # Check file size
    if hasattr(file_data, 'seek'):
        # FileStorage object
        file_data.seek(0, os.SEEK_END)
        size = file_data.tell()
        file_data.seek(0)
    else:
        # bytes object
        size = len(file_data)
    
    if size > Config.MAX_FILE_SIZE:
        raise ValueError(f"File too large. Max size: {Config.MAX_FILE_SIZE / (1024*1024):.1f}MB")
    
    # Check MIME type
    if hasattr(file_data, 'read'):
        # FileStorage object
        mime_data = file_data.read(1024)
        file_data.seek(0)
    else:
        # bytes object
        mime_data = file_data[:1024]
    
    mime = magic.from_buffer(mime_data, mime=True)
    allowed_mimes = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'application/pdf']
    
    if mime not in allowed_mimes:
        raise ValueError(f"Invalid file content. Detected MIME: {mime}")
    
    # Sanitize filename
    sanitized_filename = secure_filename(filename)
    if not sanitized_filename:
        raise ValueError("Invalid filename")
    
    logger.info(f"File validation passed: {filename} ({mime}, {size} bytes)")

def validate_receipt_data(data: dict) -> bool:
    """
    Validate receipt data structure
    
    Args:
        data: Receipt data dictionary
        
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = ['merchant', 'date', 'total_amount']
    
    for field in required_fields:
        if field not in data:
            logger.warning(f"Missing required field: {field}")
            return False
    
    # Validate amount
    try:
        amount = float(data['total_amount'])
        if amount < 0:
            logger.warning("Negative amount not allowed")
            return False
    except (ValueError, TypeError):
        logger.warning("Invalid amount format")
        return False
    
    return True

def validate_date_range(start_date: str, end_date: str) -> bool:
    """
    Validate date range for queries
    
    Args:
        start_date: Start date string (ISO format)
        end_date: End date string (ISO format)
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        from datetime import datetime
        
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        if start > end:
            logger.warning("Start date cannot be after end date")
            return False
        
        # Check if range is reasonable (not more than 2 years)
        if (end - start).days > 730:
            logger.warning("Date range too large (max 2 years)")
            return False
        
        return True
        
    except ValueError as e:
        logger.warning(f"Invalid date format: {e}")
        return False 

def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password: str) -> bool:
    """Validate password strength"""
    if not password:
        return False
    
    # Minimum 8 characters
    if len(password) < 8:
        return False
    
    # At least one letter and one number
    has_letter = re.search(r'[a-zA-Z]', password)
    has_number = re.search(r'\d', password)
    
    return bool(has_letter and has_number)

def validate_username(username: str) -> bool:
    """Validate username format"""
    if not username:
        return False
    
    # 3-50 characters, alphanumeric and underscores only
    if len(username) < 3 or len(username) > 50:
        return False
    
    pattern = r'^[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, username))

def validate_amount(amount: str) -> Optional[float]:
    """Validate and convert amount string to float"""
    if not amount:
        return None
    
    try:
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$,€£¥]', '', str(amount))
        cleaned = cleaned.replace(',', '')
        
        value = float(cleaned)
        if value < 0:
            return None
        
        return round(value, 2)
    except (ValueError, TypeError):
        return None

def validate_date(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)"""
    if not date_str:
        return False
    
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str):
        return False
    
    try:
        from datetime import datetime
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    if not filename:
        return ''
    
    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename

def validate_file_size(file_size: int, max_size: int = 16 * 1024 * 1024) -> bool:
    """Validate file size"""
    return 0 < file_size <= max_size

def validate_receipt_data(data: dict) -> tuple[bool, str]:
    """Validate receipt data structure"""
    required_fields = ['merchant', 'total_amount', 'date']
    
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Validate amount
    if not isinstance(data['total_amount'], (int, float)) or data['total_amount'] <= 0:
        return False, "Invalid total amount"
    
    # Validate date
    if not validate_date(data['date']):
        return False, "Invalid date format"
    
    # Validate merchant name
    if not data['merchant'] or len(data['merchant']) > 200:
        return False, "Invalid merchant name"
    
    return True, "Valid"

def validate_transaction_data(data: dict) -> tuple[bool, str]:
    """Validate transaction data structure"""
    required_fields = ['amount', 'date', 'description']
    
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Validate amount
    if not isinstance(data['amount'], (int, float)) or data['amount'] == 0:
        return False, "Invalid amount"
    
    # Validate date
    if not validate_date(data['date']):
        return False, "Invalid date format"
    
    # Validate description
    if not data['description'] or len(data['description']) > 500:
        return False, "Invalid description"
    
    return True, "Valid" 
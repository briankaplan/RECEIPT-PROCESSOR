"""
Helper utilities for the Receipt Processor application
"""

import os
import uuid
from datetime import datetime
from typing import Optional

def generate_filename(original_filename: str, prefix: str = "") -> str:
    """
    Generate a unique filename for uploaded files
    
    Args:
        original_filename: Original filename
        prefix: Optional prefix for the filename
        
    Returns:
        str: Generated unique filename
    """
    # Get file extension
    _, ext = os.path.splitext(original_filename)
    
    # Generate unique ID
    unique_id = str(uuid.uuid4())[:8]
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Build filename
    if prefix:
        filename = f"{prefix}_{timestamp}_{unique_id}{ext}"
    else:
        filename = f"{timestamp}_{unique_id}{ext}"
    
    return filename

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Original filename
        
    Returns:
        str: Sanitized filename
    """
    # Remove or replace unsafe characters
    unsafe_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    sanitized = filename
    
    for char in unsafe_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:255-len(ext)] + ext
    
    return sanitized

def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format currency amount for display
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        str: Formatted currency string
    """
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "CAD": "C$",
        "AUD": "A$"
    }
    
    symbol = currency_symbols.get(currency, currency)
    return f"{symbol}{amount:.2f}"

def format_date(date_string: str, format_str: str = "%Y-%m-%d") -> str:
    """
    Format date string for display
    
    Args:
        date_string: Date string to format
        format_str: Output format string
        
    Returns:
        str: Formatted date string
    """
    try:
        if 'T' in date_string:
            # ISO format
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        else:
            # Try parsing as date
            dt = datetime.strptime(date_string, "%Y-%m-%d")
        
        return dt.strftime(format_str)
    except ValueError:
        return date_string

def get_file_size_mb(file_size_bytes: int) -> float:
    """
    Convert file size from bytes to MB
    
    Args:
        file_size_bytes: File size in bytes
        
    Returns:
        float: File size in MB
    """
    return file_size_bytes / (1024 * 1024)

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to specified length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..." 
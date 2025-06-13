# Enhanced Components

This directory contains enhanced versions of core components for the expense processor system.

## Enhanced Attachment Handler

The enhanced attachment handler (`enhanced_attachment_handler.py`) provides advanced email attachment processing with security and efficiency features.

### Key Features

- **Security Scanning**
  - File size limits (50MB per file, 200MB total)
  - Allowed and dangerous file extension lists
  - MIME type verification
  - Content-based security checks
  - Quarantine system for suspicious files

- **File Processing**
  - Support for multiple file types (PDF, images, documents, etc.)
  - Text extraction from various file types
  - Safe filename generation
  - Metadata tracking

- **Performance**
  - Concurrent download support
  - Automatic cleanup of old attachments
  - Batch processing capabilities

### Usage

```python
from enhanced_components.enhanced_attachment_handler import EnhancedAttachmentHandler, download_receipt_attachments

# Initialize handler
handler = EnhancedAttachmentHandler(
    temp_dir="temp_attachments",
    config={
        "security_enabled": True,
        "quarantine_suspicious": True,
        "max_concurrent_downloads": 5
    }
)

# Initialize async
await handler.initialize()

# Download attachments
attachments = await download_receipt_attachments(
    gmail_service,
    messages,
    config=handler.config
)
```

### Configuration

The handler can be configured through the config dictionary:

```python
config = {
    "security_enabled": True,
    "quarantine_suspicious": True,
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "max_concurrent_downloads": 5,
    "cleanup_after_hours": 24
}
```

### Security Features

- Comprehensive file scanning
- MIME type verification
- Content-based security checks
- Archive file inspection
- Safe filename generation
- Quarantine system

### Integration

The enhanced attachment handler integrates with:
- Gmail services
- MongoDB storage
- Email parser
- Expense processor

### Dependencies

- python-magic (for MIME detection)
- aiofiles (for async file operations)
- dataclasses
- pathlib
- asyncio 
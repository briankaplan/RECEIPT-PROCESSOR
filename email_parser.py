#!/usr/bin/env python3
"""
Email Parser - Safely parse receipt messages and handle attachments
"""

import logging
import hashlib
import re
from pathlib import Path
import base64
from datetime import datetime
from attachment_handler_fix import EnhancedAttachmentHandler

def parse_receipts(messages, temp_dir="temp_attachments"):
    """
    Parse receipt messages without filename issues
    """
    logging.info(f"📧 Parsing {len(messages)} messages")
    parsed_receipts = []
    
    # Create safe attachment handler
    attachment_handler = EnhancedAttachmentHandler(temp_dir)
    
    for message in messages:
        try:
            receipt_data = parse_single_message_safely(message, attachment_handler)
            if receipt_data:
                parsed_receipts.append(receipt_data)
                
        except Exception as e:
            logging.error(f"❌ Error parsing message: {e}")
            continue
    
    logging.info(f"✅ Successfully parsed {len(parsed_receipts)} receipts")
    return parsed_receipts

def parse_single_message_safely(message, attachment_handler):
    """
    Parse single message without file path issues
    """
    try:
        message_id = message.get('id', 'unknown')
        
        # Extract basic email info
        headers = message.get('payload', {}).get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'No sender')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Extract email body safely
        body_text = extract_email_body_safely(message.get('payload', {}))
        
        # Process attachments with safe handling
        attachments = []
        try:
            attachment_list = extract_attachments_safely(message, attachment_handler)
            attachments = attachment_list
        except Exception as e:
            logging.warning(f"⚠️ Attachment processing failed for {message_id}: {e}")
            # Continue without attachments rather than failing completely
        
        # Create receipt data
        receipt_data = {
            'id': message_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'body_text': body_text,
            'attachments': [att.get('file_path', '') for att in attachments],
            'attachment_details': attachments,
            'raw_message': message,
            'processed_at': datetime.now().isoformat()
        }
        
        logging.info(f"📧 Parsed receipt: {subject[:50]}... ({len(attachments)} attachments)")
        return receipt_data
        
    except Exception as e:
        logging.error(f"❌ Error parsing single message: {e}")
        return None

def extract_email_body_safely(payload):
    """Extract email body text safely"""
    try:
        body_text = ""
        
        # Handle different payload structures
        if 'parts' in payload:
            # Multi-part message
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    body_data = part.get('body', {}).get('data', '')
                    if body_data:
                        decoded = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                        body_text += decoded + "\n"
        else:
            # Single part message
            if payload.get('mimeType') == 'text/plain':
                body_data = payload.get('body', {}).get('data', '')
                if body_data:
                    body_text = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
        
        return body_text.strip()
        
    except Exception as e:
        logging.warning(f"⚠️ Error extracting email body: {e}")
        return ""

def extract_attachments_safely(message, attachment_handler):
    """Extract attachments safely without filename issues"""
    attachments = []
    
    try:
        message_id = message.get('id', 'unknown')
        payload = message.get('payload', {})
        
        # Find attachment parts
        parts_to_process = []
        
        if 'parts' in payload:
            parts_to_process = payload['parts']
        elif payload.get('body', {}).get('attachmentId'):
            parts_to_process = [payload]
        
        for part in parts_to_process:
            try:
                # Check if this part is an attachment
                body = part.get('body', {})
                attachment_id = body.get('attachmentId')
                
                if not attachment_id:
                    continue
                
                filename = part.get('filename', 'attachment')
                mime_type = part.get('mimeType', 'application/octet-stream')
                size = body.get('size', 0)
                
                # Skip if no filename or too large
                if not filename or size > 50 * 1024 * 1024:  # 50MB limit
                    continue
                
                # Create safe filename
                safe_filename = attachment_handler.create_safe_filename(
                    filename,
                    message_id,
                    attachment_id
                )
                
                # Save attachment info (don't actually download yet)
                attachment_info = {
                    'original_filename': filename,
                    'safe_filename': safe_filename,
                    'file_path': str(Path(attachment_handler.temp_dir) / safe_filename),
                    'mime_type': mime_type,
                    'size': size,
                    'attachment_id': attachment_id,
                    'message_id': message_id
                }
                
                attachments.append(attachment_info)
                
            except Exception as e:
                logging.warning(f"⚠️ Error processing attachment part: {e}")
                continue
        
        return attachments
        
    except Exception as e:
        logging.error(f"❌ Error extracting attachments: {e}")
        return []

def create_safe_filename_simple(original_filename, message_id):
    """Simple safe filename creator as fallback"""
    try:
        # Clean the filename
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', original_filename)
        safe_name = re.sub(r'[{}\'\"]', '', safe_name)
        safe_name = safe_name.replace(' ', '_')
        
        # Create unique prefix
        unique_id = hashlib.md5(f"{message_id}_{safe_name}".encode()).hexdigest()[:8]
        
        # Get extension
        ext = Path(original_filename).suffix[:10]  # Limit extension length
        
        # Truncate if too long
        if len(safe_name) > 50:
            safe_name = safe_name[:50]
        
        final_name = f"{unique_id}_{safe_name}{ext}"
        
        # Final length check
        if len(final_name) > 200:
            final_name = f"{unique_id}{ext}"
        
        return final_name
        
    except Exception:
        # Ultimate fallback
        fallback_id = hashlib.md5(str(original_filename).encode()).hexdigest()[:12]
        return f"attachment_{fallback_id}.bin"

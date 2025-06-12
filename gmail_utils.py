#!/usr/bin/env python3
"""
Gmail Utilities Module
Handles Gmail API interactions for email processing
"""

import logging
import pickle
import base64
import email
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from attachment_handler_fix import EnhancedAttachmentHandler


class GmailManager:
    def __init__(self, email: str, pickle_file: str):
        """Initialize Gmail manager"""
        self.email = email
        self.pickle_file = pickle_file
        self.service = None
        self.creds = None
    
    async def initialize(self) -> bool:
        """Initialize Gmail API connection"""
        try:
            # Load credentials
            self.creds = await self._load_credentials()
            if not self.creds:
                return False
            
            # Build service
            self.service = build('gmail', 'v1', credentials=self.creds)
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize Gmail: {e}")
            return False
    
    async def _load_credentials(self) -> Optional[Credentials]:
        """Load Gmail credentials"""
        try:
            # Load from pickle file
            with open(self.pickle_file, 'rb') as token:
                creds = pickle.load(token)
            
            # Check if credentials need refresh
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # Save refreshed credentials
                    with open(self.pickle_file, 'wb') as token:
                        pickle.dump(creds, token)
                else:
                    logging.error("Invalid credentials")
                    return None
            
            return creds
            
        except Exception as e:
            logging.error(f"Failed to load credentials: {e}")
            return None
    
    async def search_messages(self, query: str, max_results: int = 100) -> List[Dict]:
        """Search Gmail messages"""
        try:
            if not self.service:
                if not await self.initialize():
                    return []
            
            # Execute search
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            # Get full message details
            full_messages = []
            for message in messages:
                try:
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    full_messages.append(msg)
                except HttpError as e:
                    logging.error(f"Failed to get message {message['id']}: {e}")
            
            return full_messages
            
        except Exception as e:
            logging.error(f"Failed to search messages: {e}")
            return []
    
    async def get_message(self, message_id: str) -> Optional[Dict]:
        """Get full message details"""
        try:
            if not self.service:
                if not await self.initialize():
                    return None
            
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            return message
            
        except Exception as e:
            logging.error(f"Failed to get message {message_id}: {e}")
            return None
    
    def get_message_body(self, message: Dict) -> str:
        """Extract message body"""
        try:
            if 'payload' not in message:
                return ""
            
            payload = message['payload']
            
            # Get body from parts
            if 'parts' in payload:
                parts = payload['parts']
                body = ""
                for part in parts:
                    if part['mimeType'] == 'text/plain':
                        if 'data' in part['body']:
                            body += base64.urlsafe_b64decode(
                                part['body']['data']
                            ).decode('utf-8')
                return body
            
            # Get body from payload
            if 'body' in payload and 'data' in payload['body']:
                return base64.urlsafe_b64decode(
                    payload['body']['data']
                ).decode('utf-8')
            
            return ""
            
        except Exception as e:
            logging.error(f"Failed to get message body: {e}")
            return ""
    
    def get_message_subject(self, message: Dict) -> str:
        """Extract message subject"""
        try:
            if 'payload' not in message:
                return ""
            
            headers = message['payload'].get('headers', [])
            for header in headers:
                if header['name'].lower() == 'subject':
                    return header['value']
            
            return ""
            
        except Exception as e:
            logging.error(f"Failed to get message subject: {e}")
            return ""
    
    def get_message_date(self, message: Dict) -> str:
        """Extract message date"""
        try:
            if 'payload' not in message:
                return ""
            
            headers = message['payload'].get('headers', [])
            for header in headers:
                if header['name'].lower() == 'date':
                    return header['value']
            
            return ""
            
        except Exception as e:
            logging.error(f"Failed to get message date: {e}")
            return ""
    
    def get_message_attachments(self, message: Dict) -> List[Dict]:
        """Extract message attachments"""
        try:
            if 'payload' not in message:
                return []
            
            attachments = []
            payload = message['payload']
            
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('filename'):
                        attachment = {
                            'id': part['body'].get('attachmentId'),
                            'filename': part['filename'],
                            'mimeType': part['mimeType'],
                            'size': part['body'].get('size', 0)
                        }
                        attachments.append(attachment)
            
            return attachments
            
        except Exception as e:
            logging.error(f"Failed to get message attachments: {e}")
            return []
    
    async def download_attachment(self, message_id: str, attachment_id: str) -> Optional[bytes]:
        """Download message attachment"""
        try:
            if not self.service:
                if not await self.initialize():
                    return None
            
            attachment = self.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            
            if 'data' in attachment:
                return base64.urlsafe_b64decode(attachment['data'])
            
            return None
            
        except Exception as e:
            logging.error(f"Failed to download attachment: {e}")
            return None

    def fetch_receipt_emails(self, since: str = None, max_results: int = 100) -> List[Dict]:
        """Fetch emails that likely contain receipts."""
        # Build a comprehensive search query
        query_parts = []
        
        # Base query for date range
        if since:
            # Convert ISO format to YYYY/MM/DD for Gmail search
            try:
                from datetime import datetime
                date_obj = datetime.fromisoformat(since.replace('Z', '+00:00'))
                gmail_date = date_obj.strftime('%Y/%m/%d')
                query_parts.append(f"after:{gmail_date}")
            except Exception as e:
                logging.error(f"❌ Error formatting date for Gmail search: {e}")
        
        # Add receipt-related keywords
        receipt_keywords = [
            "receipt", "order", "purchase", "confirmation", "invoice",
            "payment", "transaction", "statement", "bill", "paid",
            "thank you for your order", "your order has been received",
            "order confirmation", "payment confirmation"
        ]
        query_parts.append(f"({' OR '.join(receipt_keywords)})")
        
        # Add attachment filter
        query_parts.append("has:attachment")
        
        # Combine all parts
        query = " ".join(query_parts)
        
        logging.info(f"📬 Fetching receipt emails with query: {query}")
        messages = []
        try:
            response = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            message_ids = response.get('messages', [])

            while 'nextPageToken' in response:
                page_token = response['nextPageToken']
                response = self.service.users().messages().list(
                    userId='me', q=query, maxResults=max_results, pageToken=page_token
                ).execute()
                message_ids.extend(response.get('messages', []))

            for msg in message_ids:
                full_msg = self.get_message(msg['id'])
                if full_msg:
                    messages.append(full_msg)

        except HttpError as e:
            logging.error(f"❌ Error fetching receipt emails: {e}")

        return messages

    def extract_body_from_message(self, message: Dict) -> str:
        """Extract HTML or plain body content from an email message."""
        payload = message.get('payload', {})
        return self._extract_content_recursive(payload.get('parts'), payload)

    def _extract_content_recursive(self, parts, payload) -> str:
        """Recursively search for text/html or fallback to text/plain."""
        if parts:
            for part in parts:
                mime = part.get('mimeType')
                data = part.get('body', {}).get('data')
                if mime == 'text/html' and data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                elif mime == 'text/plain' and data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                elif 'parts' in part:
                    return self._extract_content_recursive(part['parts'], payload)
        else:
            data = payload.get('body', {}).get('data')
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return ""

    def extract_attachments(self, message: Dict, download_dir: str) -> List[str]:
        """Extract and save attachments from a message using EnhancedAttachmentHandler."""
        handler = EnhancedAttachmentHandler(download_dir)
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
                    safe_filename = handler.create_safe_filename(
                        {'filename': filename, 'mime_type': mime_type},
                        message_id
                    )
                    
                    # Save attachment info
                    attachment_info = {
                        'original_filename': filename,
                        'safe_filename': safe_filename,
                        'file_path': str(handler.temp_dir / safe_filename),
                        'mime_type': mime_type,
                        'size': size,
                        'attachment_id': attachment_id,
                        'message_id': message_id
                    }
                    
                    attachments.append(attachment_info['file_path'])
                    
                except Exception as e:
                    logging.warning(f"⚠️ Error processing attachment part: {e}")
                    continue
            
        except Exception as e:
            logging.error(f"❌ Error extracting attachments: {e}")
        
        return attachments
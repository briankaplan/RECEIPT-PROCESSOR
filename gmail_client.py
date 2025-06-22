import os
import json
import base64
import logging
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

class GmailClient:
    """Gmail API client for accessing and downloading email attachments"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API"""
        try:
            # Try to get credentials from environment or file
            creds_json = os.getenv('GMAIL_CREDENTIALS')
            token_json = os.getenv('GMAIL_TOKEN')
            
            if token_json:
                # Load existing token
                token_data = json.loads(token_json)
                self.credentials = Credentials.from_authorized_user_info(token_data, self.SCOPES)
            
            # If there are no (valid) credentials available, prompt user to log in
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                elif creds_json:
                    # Use credentials from environment
                    creds_data = json.loads(creds_json)
                    flow = InstalledAppFlow.from_client_config(creds_data, self.SCOPES)
                    self.credentials = flow.run_local_server(port=0)
                else:
                    logger.warning("No Gmail credentials found. Using mock mode.")
                    return
            
            # Build the service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("Gmail API authenticated successfully")
            
        except Exception as e:
            logger.error(f"Gmail authentication failed: {str(e)}")
            self.service = None
    
    def is_authenticated(self):
        """Check if Gmail API is authenticated"""
        return self.service is not None
    
    def get_emails_with_attachments(self, limit=50):
        """Get emails that have attachments"""
        if not self.service:
            logger.error("Gmail service not available")
            return []
        
        try:
            # Search for emails with attachments
            query = 'has:attachment'
            results = self.service.users().messages().list(
                userId='me', 
                q=query, 
                maxResults=limit
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                # Get message details
                message = self.service.users().messages().get(
                    userId='me', 
                    id=msg['id']
                ).execute()
                
                # Extract basic info
                headers = message['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                # Check if it has attachments
                has_attachments = self._has_attachments(message['payload'])
                
                if has_attachments:
                    emails.append({
                        'id': msg['id'],
                        'subject': subject,
                        'sender': sender,
                        'date': date,
                        'snippet': message.get('snippet', '')
                    })
            
            logger.info(f"Found {len(emails)} emails with attachments")
            return emails
            
        except Exception as e:
            logger.error(f"Error getting emails: {str(e)}")
            return []
    
    def _has_attachments(self, payload):
        """Check if message payload has attachments"""
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('filename') and part.get('body', {}).get('attachmentId'):
                    return True
                # Check nested parts
                if self._has_attachments(part):
                    return True
        return False
    
    def download_attachments(self, message_id):
        """Download all attachments from an email"""
        if not self.service:
            logger.error("Gmail service not available")
            return []
        
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id
            ).execute()
            
            attachments = []
            self._extract_attachments(message['payload'], message_id, attachments)
            
            logger.info(f"Downloaded {len(attachments)} attachments from email {message_id}")
            return attachments
            
        except Exception as e:
            logger.error(f"Error downloading attachments: {str(e)}")
            return []
    
    def _extract_attachments(self, payload, message_id, attachments):
        """Recursively extract attachments from message payload"""
        if 'parts' in payload:
            for part in payload['parts']:
                self._extract_attachments(part, message_id, attachments)
        
        if payload.get('filename'):
            attachment_id = payload.get('body', {}).get('attachmentId')
            if attachment_id:
                try:
                    # Get attachment data
                    attachment = self.service.users().messages().attachments().get(
                        userId='me',
                        messageId=message_id,
                        id=attachment_id
                    ).execute()
                    
                    # Decode and save file
                    file_data = base64.urlsafe_b64decode(attachment['data'])
                    filename = payload['filename']
                    
                    # Ensure downloads directory exists
                    os.makedirs('downloads', exist_ok=True)
                    
                    # Create unique filename
                    safe_filename = f"{message_id}_{filename}"
                    filepath = os.path.join('downloads', safe_filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(file_data)
                    
                    attachments.append({
                        'filename': filename,
                        'filepath': filepath,
                        'size': len(file_data),
                        'mime_type': payload.get('mimeType', 'unknown')
                    })
                    
                    logger.info(f"Downloaded attachment: {filename}")
                    
                except Exception as e:
                    logger.error(f"Error downloading attachment {payload['filename']}: {str(e)}")

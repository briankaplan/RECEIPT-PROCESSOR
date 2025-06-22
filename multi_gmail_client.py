import os
import pickle
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

class MultiGmailClient:
    """Gmail API client with multi-account and parallel receipt fetching"""

    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]

    def __init__(self):
        self.accounts = {
            'kaplan.brian@gmail.com': {
                'email': 'kaplan.brian@gmail.com',
                'pickle_file': 'gmail_tokens/kaplan.brian_at_gmail.com.pickle',
                'service': None
            },
            'brian@downhome.com': {
                'email': 'brian@downhome.com',
                'pickle_file': 'gmail_tokens/brian_at_downhome.com.pickle',
                'service': None
            },
            'brian@musiccityrodeo.com': {
                'email': 'brian@musiccityrodeo.com',
                'pickle_file': 'gmail_tokens/brian_at_musiccityrodeo.com.pickle',
                'service': None
            }
        }

    def init_services(self):
        for account in self.accounts.values():
            creds = None
            if os.path.exists(account['pickle_file']):
                with open(account['pickle_file'], 'rb') as token:
                    creds = pickle.load(token)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            account['service'] = build('gmail', 'v1', credentials=creds)

    def search_receipt_ids(self, service, user_id='me', days=365) -> List[str]:
        from datetime import datetime, timedelta
        after_date = (datetime.now() - timedelta(days=days)).strftime('%Y/%m/%d')
        query = f"has:attachment subject:(receipt OR order OR invoice) after:{after_date}"
        try:
            response = service.users().messages().list(userId=user_id, q=query, maxResults=100).execute()
            return [msg['id'] for msg in response.get('messages', [])]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_metadata(self, service, msg_id, user_id='me') -> Optional[Dict]:
        try:
            msg = service.users().messages().get(userId=user_id, id=msg_id, format='metadata').execute()
            headers = msg.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            return {
                'id': msg_id,
                'subject': subject,
                'from': sender
            }
        except Exception as e:
            logger.error(f"Metadata fetch failed for {msg_id}: {e}")
            return None

    def fetch_receipt_metadata_parallel(self, days=365) -> List[Dict]:
        self.init_services()
        all_receipts = []

        for acct, data in self.accounts.items():
            service = data['service']
            if not service:
                continue
            msg_ids = self.search_receipt_ids(service)
            logger.info(f"{acct}: Found {len(msg_ids)} potential receipts")

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(self.get_metadata, service, msg_id) for msg_id in msg_ids]
                for future in as_completed(futures):
                    metadata = future.result()
                    if metadata:
                        all_receipts.append(metadata)

        return all_receipts
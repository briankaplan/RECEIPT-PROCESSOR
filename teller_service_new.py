"""
Teller service for bank integration
"""

import logging
import requests
import base64
import tempfile
import os
from typing import Dict, List, Optional
from urllib.parse import urlencode
from datetime import datetime

logger = logging.getLogger(__name__)

class SafeTellerClient:
    """Teller client that handles all environments safely"""
    
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Receipt-Processor/1.0',
            'Accept': 'application/json'
        })
        self.cert_files = None
        self._setup_certificates()
    
    def _setup_certificates(self):
        """Setup Teller client certificates"""
        try:
            # Check for certificate files
            cert_path = os.getenv('TELLER_CERT_PATH', './credentials/teller_certificate.b64')
            key_path = os.getenv('TELLER_KEY_PATH', './credentials/teller_private_key.b64')
            
            if os.path.exists(cert_path) and os.path.exists(key_path):
                # Read base64 encoded certificates
                with open(cert_path, 'r') as f:
                    cert_b64 = f.read().strip()
                
                with open(key_path, 'r') as f:
                    key_b64 = f.read().strip()
                
                # Decode base64 to PEM format
                cert_pem = base64.b64decode(cert_b64).decode('utf-8')
                key_pem = base64.b64decode(key_b64).decode('utf-8')
                
                # Create temporary files for requests
                cert_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
                key_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
                
                cert_file.write(cert_pem)
                key_file.write(key_pem)
                
                cert_file.close()
                key_file.close()
                
                # Set secure permissions
                os.chmod(cert_file.name, 0o600)
                os.chmod(key_file.name, 0o600)
                
                self.cert_files = (cert_file.name, key_file.name)
                logger.info("✅ Teller certificates loaded successfully")
                
            else:
                logger.warning("⚠️ Teller certificates not found. API calls may fail.")
                
        except Exception as e:
            logger.error(f"❌ Error setting up Teller certificates: {e}")
    
    def _make_request(self, method: str, url: str, **kwargs):
        """Make HTTP request with certificates if available"""
        try:
            if self.cert_files:
                kwargs['cert'] = self.cert_files
            
            response = self.session.request(method, url, **kwargs)
            return response
            
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def get_connect_url(self, user_id: str) -> str:
        """Generate Teller Connect URL for bank connection"""
        if not self.config.TELLER_APPLICATION_ID:
            return "#"
        
        params = {
            'application_id': self.config.TELLER_APPLICATION_ID,
            'redirect_uri': self.config.TELLER_WEBHOOK_URL.replace('/webhook', '/callback'),
            'state': user_id,
            'scope': 'transactions:read accounts:read identity:read'
        }
        
        base_url = "https://connect.teller.io/connect"
        return f"{base_url}?{urlencode(params)}"
    
    def get_accounts(self, access_token: str) -> List[Dict]:
        """Get bank accounts using access token"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = self._make_request(
                'GET',
                f"{self.config.TELLER_API_URL}/accounts",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return []
    
    def get_transactions(self, access_token: str, account_id: str, 
                        start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get transactions for a specific account"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            params = {}
            
            if start_date:
                params['from'] = start_date
            if end_date:
                params['to'] = end_date
            
            logger.info(f"Fetching transactions for account {account_id} from {start_date} to {end_date}")
            
            response = self._make_request(
                'GET',
                f"{self.config.TELLER_API_URL}/accounts/{account_id}/transactions",
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            transactions = response.json()
            logger.info(f"Retrieved {len(transactions)} transactions from Teller")
            return transactions
        except Exception as e:
            logger.error(f"Error getting transactions for account {account_id}: {e}")
            return []
    
    def validate_token(self, access_token: str) -> bool:
        """Validate if access token is still valid"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = self._make_request(
                'GET',
                f"{self.config.TELLER_API_URL}/accounts",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False 
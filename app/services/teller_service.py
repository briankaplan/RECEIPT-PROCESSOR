"""
Teller service for bank integration
"""

import logging
import requests
from typing import Dict, List, Optional
from urllib.parse import urlencode
from datetime import datetime
from ..config import Config

logger = logging.getLogger(__name__)

class TellerService:
    """Teller service wrapper for the application"""
    
    def __init__(self):
        self.client = SafeTellerClient()
        self.mongo_service = None
        try:
            from .mongo_service import MongoService
            self.mongo_service = MongoService()
        except ImportError:
            logger.warning("MongoService not available for Teller")
    
    def is_configured(self) -> bool:
        """Check if Teller is configured"""
        return bool(Config.TELLER_APPLICATION_ID)
    
    def get_tokens(self) -> List[Dict]:
        """Get Teller access tokens"""
        if self.mongo_service:
            return self.mongo_service.get_teller_tokens()
        return []
    
    def get_connect_url(self, user_id: str) -> str:
        """Generate Teller Connect URL for bank connection"""
        return self.client.get_connect_url(user_id)
    
    def get_accounts(self, access_token: str) -> List[Dict]:
        """Get bank accounts using access token"""
        return self.client.get_accounts(access_token)
    
    def get_transactions(self, access_token: str, account_id: str, 
                        start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get transactions for a specific account"""
        return self.client.get_transactions(access_token, account_id, start_date, end_date)
    
    def validate_token(self, access_token: str) -> bool:
        """Validate if access token is still valid"""
        return self.client.validate_token(access_token)
    
    def get_account_details(self, access_token: str, account_id: str) -> Optional[Dict]:
        """Get detailed account information"""
        return self.client.get_account_details(access_token, account_id)
    
    def get_identity(self, access_token: str) -> Optional[Dict]:
        """Get user identity information"""
        return self.client.get_identity(access_token)

class SafeTellerClient:
    """Teller client that handles all environments safely"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Receipt-Processor/1.0',
            'Accept': 'application/json'
        })
    
    def get_connect_url(self, user_id: str) -> str:
        """Generate Teller Connect URL for bank connection"""
        if not Config.TELLER_APPLICATION_ID:
            return "#"
        
        params = {
            'application_id': Config.TELLER_APPLICATION_ID,
            'redirect_uri': Config.TELLER_WEBHOOK_URL.replace('/webhook', '/callback'),
            'state': user_id,
            'scope': 'transactions:read accounts:read identity:read'
        }
        
        base_url = "https://connect.teller.io/connect"
        return f"{base_url}?{urlencode(params)}"
    
    def get_accounts(self, access_token: str) -> List[Dict]:
        """Get bank accounts using access token"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = self.session.get(
                f"{Config.TELLER_API_URL}/accounts",
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
            
            response = self.session.get(
                f"{Config.TELLER_API_URL}/accounts/{account_id}/transactions",
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting transactions for account {account_id}: {e}")
            return []
    
    def validate_token(self, access_token: str) -> bool:
        """Validate if access token is still valid"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = self.session.get(
                f"{Config.TELLER_API_URL}/accounts",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False
    
    def get_account_details(self, access_token: str, account_id: str) -> Optional[Dict]:
        """Get detailed account information"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = self.session.get(
                f"{Config.TELLER_API_URL}/accounts/{account_id}",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting account details for {account_id}: {e}")
            return None
    
    def get_identity(self, access_token: str) -> Optional[Dict]:
        """Get user identity information"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = self.session.get(
                f"{Config.TELLER_API_URL}/identity",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting identity: {e}")
            return None 
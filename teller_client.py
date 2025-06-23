import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import ssl
from urllib.parse import urljoin
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TellerTransaction:
    id: str
    account_id: str
    amount: float
    date: str
    description: str
    merchant_name: str
    category: str
    type: str
    status: str
    raw_data: Dict

@dataclass
class TellerAccount:
    id: str
    name: str
    type: str
    subtype: str
    balance: float
    currency: str
    institution_name: str

class TellerClient:
    """Teller API client for live bank transaction feeds and intelligent receipt matching"""
    
    def __init__(self, access_token=None):
        self.application_id = os.getenv('TELLER_APPLICATION_ID')
        self.api_url = os.getenv('TELLER_API_URL', 'https://api.teller.io')
        self.api_version = os.getenv('TELLER_API_VERSION', '2020-10-12')
        self.environment = os.getenv('TELLER_ENVIRONMENT', 'sandbox')
        self.webhook_url = os.getenv('TELLER_WEBHOOK_URL')
        self.signing_secret = os.getenv('TELLER_SIGNING_SECRET')
        self.cert_path = os.getenv('TELLER_CERT_PATH')
        self.key_path = os.getenv('TELLER_KEY_PATH')
        
        self.session = None
        self.connected_accounts = []
        
        if self._has_credentials():
            self._initialize_session()
            logger.info("Teller API client initialized")
        else:
            logger.warning("Teller credentials not found in environment variables")
    
    def _has_credentials(self) -> bool:
        """Check if all required Teller credentials are available"""
        required_vars = [
            self.application_id,
            self.api_url
        ]
        
        # Check if all variables exist
        if not all(var for var in required_vars):
            logger.warning("Missing basic Teller configuration")
            return False
        
        # In production (render.com), certificates might not be available initially
        # Allow basic initialization without certificates for Connect flow
        if os.getenv('FLASK_ENV') == 'production' or os.getenv('RENDER'):
            logger.info("Production environment detected - allowing initialization without certificates")
            return True
            
        # Check if certificate files actually exist (development only)
        if self.cert_path and self.key_path:
            if not os.path.exists(self.cert_path):
                logger.warning(f"Teller certificate not found: {self.cert_path}")
                return False
                
            if not os.path.exists(self.key_path):
                logger.warning(f"Teller key not found: {self.key_path}")
                return False
            
        return True
    
    def _initialize_session(self):
        """Initialize SSL session with Teller certificates"""
        try:
            self.session = requests.Session()
            
            # Set up SSL context with client certificates (if available)
            if self.cert_path and self.key_path and os.path.exists(self.cert_path) and os.path.exists(self.key_path):
                self.session.cert = (self.cert_path, self.key_path)
                logger.info("Teller session initialized with SSL certificates")
            else:
                logger.info("Teller session initialized without SSL certificates (Connect flow)")
            
            # Set headers
            self.session.headers.update({
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Teller-Version': self.api_version,
                'User-Agent': f'GmailReceiptProcessor/1.0'
            })
            
        except Exception as e:
            logger.error(f"Failed to initialize Teller session: {str(e)}")
            self.session = None
    
    def is_connected(self) -> bool:
        """Check if Teller API is connected and accessible"""
        if not self.session or not self._has_credentials():
            return False
        
        try:
            # Test connection with a simple API call
            response = self.session.get(f"{self.api_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Teller connection test failed: {str(e)}")
            return False
    
    def get_accounts(self) -> List[TellerAccount]:
        """Alias for get_connected_accounts for backward compatibility"""
        return self.get_connected_accounts()
    
    def get_connected_accounts(self) -> List[TellerAccount]:
        """Get list of connected bank accounts"""
        if not self.is_connected():
            return []
        
        try:
            response = self.session.get(f"{self.api_url}/accounts")
            
            if response.status_code == 200:
                accounts_data = response.json()
                self.connected_accounts = []
                
                for account_data in accounts_data:
                    account = TellerAccount(
                        id=account_data.get('id'),
                        name=account_data.get('name', 'Unknown Account'),
                        type=account_data.get('type', 'unknown'),
                        subtype=account_data.get('subtype', ''),
                        balance=float(account_data.get('balance', {}).get('available', 0)),
                        currency=account_data.get('currency', 'USD'),
                        institution_name=account_data.get('institution', {}).get('name', 'Unknown Bank')
                    )
                    self.connected_accounts.append(account)
                
                logger.info(f"Retrieved {len(self.connected_accounts)} connected accounts")
                return self.connected_accounts
            else:
                logger.error(f"Failed to fetch accounts: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching connected accounts: {str(e)}")
            return []
    
    def get_transactions(self, account_id: str, start_date: Optional[str] = None, 
                        end_date: Optional[str] = None, limit: int = 100) -> List[TellerTransaction]:
        """Get transactions for a specific account within date range"""
        if not self.is_connected():
            return []
        
        try:
            # Build query parameters
            params = {'count': limit}
            
            if start_date:
                params['from_date'] = start_date
            if end_date:
                params['to_date'] = end_date
            
            response = self.session.get(
                f"{self.api_url}/accounts/{account_id}/transactions",
                params=params
            )
            
            if response.status_code == 200:
                transactions_data = response.json()
                transactions = []
                
                for tx_data in transactions_data:
                    transaction = TellerTransaction(
                        id=tx_data.get('id'),
                        account_id=account_id,
                        amount=float(tx_data.get('amount', 0)),
                        date=tx_data.get('date'),
                        description=tx_data.get('description', ''),
                        merchant_name=self._extract_merchant_name(tx_data),
                        category=tx_data.get('details', {}).get('category', 'other'),
                        type=tx_data.get('type', 'unknown'),
                        status=tx_data.get('status', 'unknown'),
                        raw_data=tx_data
                    )
                    transactions.append(transaction)
                
                logger.info(f"Retrieved {len(transactions)} transactions for account {account_id}")
                return transactions
            else:
                logger.error(f"Failed to fetch transactions: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching transactions: {str(e)}")
            return []
    
    def get_transactions_by_date_range(self, start_date: str, end_date: str) -> Dict[str, List[TellerTransaction]]:
        """Get transactions from all connected accounts within date range"""
        all_transactions = {}
        
        accounts = self.get_connected_accounts()
        
        for account in accounts:
            transactions = self.get_transactions(
                account.id, 
                start_date=start_date, 
                end_date=end_date
            )
            all_transactions[account.id] = transactions
        
        return all_transactions
    
    def find_matching_transactions(self, receipt_data: Dict, tolerance_days: int = 3, 
                                 amount_tolerance: float = 0.01) -> List[Dict]:
        """Find bank transactions that match a receipt"""
        matches = []
        
        if not receipt_data.get('total_amount') or not receipt_data.get('date'):
            return matches
        
        receipt_amount = abs(float(receipt_data['total_amount']))
        receipt_date = datetime.strptime(receipt_data['date'], '%Y-%m-%d')
        
        # Define search date range
        start_date = (receipt_date - timedelta(days=tolerance_days)).strftime('%Y-%m-%d')
        end_date = (receipt_date + timedelta(days=tolerance_days)).strftime('%Y-%m-%d')
        
        # Get transactions from all accounts
        all_transactions = self.get_transactions_by_date_range(start_date, end_date)
        
        for account_id, transactions in all_transactions.items():
            for transaction in transactions:
                # Check amount match (convert to positive for comparison)
                tx_amount = abs(transaction.amount)
                amount_diff = abs(tx_amount - receipt_amount)
                
                if amount_diff <= amount_tolerance:
                    # Check merchant name similarity
                    merchant_similarity = self._calculate_merchant_similarity(
                        receipt_data.get('merchant', ''),
                        transaction.merchant_name
                    )
                    
                    # Calculate date difference
                    tx_date = datetime.strptime(transaction.date, '%Y-%m-%d')
                    date_diff = abs((tx_date - receipt_date).days)
                    
                    # Calculate match confidence
                    confidence = self._calculate_match_confidence(
                        amount_diff, date_diff, merchant_similarity, tolerance_days, amount_tolerance
                    )
                    
                    match = {
                        'transaction_id': transaction.id,
                        'account_id': account_id,
                        'transaction': transaction.__dict__,
                        'confidence': confidence,
                        'amount_diff': amount_diff,
                        'date_diff': date_diff,
                        'merchant_similarity': merchant_similarity,
                        'match_reasons': self._get_match_reasons(amount_diff, date_diff, merchant_similarity)
                    }
                    matches.append(match)
        
        # Sort by confidence score
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        logger.info(f"Found {len(matches)} potential transaction matches for receipt")
        return matches
    
    def search_transactions_for_receipts(self, receipt_list: List[Dict]) -> Dict:
        """Search for transactions that match any receipt in the list"""
        matching_results = {}
        
        for receipt in receipt_list:
            matches = self.find_matching_transactions(receipt)
            if matches:
                receipt_id = receipt.get('id', receipt.get('email_id', 'unknown'))
                matching_results[receipt_id] = {
                    'receipt': receipt,
                    'matches': matches,
                    'best_match': matches[0] if matches else None
                }
        
        return matching_results
    
    def get_unmatched_transactions(self, start_date: str, end_date: str, 
                                 matched_transaction_ids: List[str] = None) -> List[TellerTransaction]:
        """Get transactions that haven't been matched to receipts"""
        if matched_transaction_ids is None:
            matched_transaction_ids = []
        
        all_transactions = self.get_transactions_by_date_range(start_date, end_date)
        unmatched = []
        
        for account_id, transactions in all_transactions.items():
            for transaction in transactions:
                if transaction.id not in matched_transaction_ids:
                    # Filter for potential receipt-related transactions
                    if self._is_receipt_relevant_transaction(transaction):
                        unmatched.append(transaction)
        
        return unmatched
    
    def _extract_merchant_name(self, transaction_data: Dict) -> str:
        """Extract merchant name from transaction data"""
        # Try various fields for merchant information
        merchant_fields = [
            'merchant_name',
            'details.counterparty.name',
            'description'
        ]
        
        for field in merchant_fields:
            if '.' in field:
                # Handle nested fields
                parts = field.split('.')
                value = transaction_data
                for part in parts:
                    value = value.get(part, {}) if isinstance(value, dict) else {}
                if isinstance(value, str) and value.strip():
                    return value.strip()
            else:
                value = transaction_data.get(field)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        
        # Fallback to description
        return transaction_data.get('description', 'Unknown Merchant')
    
    def _calculate_merchant_similarity(self, receipt_merchant: str, tx_merchant: str) -> float:
        """Calculate similarity between receipt and transaction merchant names"""
        if not receipt_merchant or not tx_merchant:
            return 0.0
        
        receipt_merchant = receipt_merchant.lower().strip()
        tx_merchant = tx_merchant.lower().strip()
        
        # Exact match
        if receipt_merchant == tx_merchant:
            return 1.0
        
        # Check if one contains the other
        if receipt_merchant in tx_merchant or tx_merchant in receipt_merchant:
            return 0.8
        
        # Simple word overlap
        receipt_words = set(receipt_merchant.split())
        tx_words = set(tx_merchant.split())
        
        if receipt_words and tx_words:
            overlap = len(receipt_words.intersection(tx_words))
            total_words = len(receipt_words.union(tx_words))
            return overlap / total_words if total_words > 0 else 0.0
        
        return 0.0
    
    def _calculate_match_confidence(self, amount_diff: float, date_diff: int, 
                                  merchant_similarity: float, tolerance_days: int, 
                                  amount_tolerance: float) -> float:
        """Calculate overall match confidence score"""
        # Amount score (closer = higher score)
        amount_score = max(0, 1 - (amount_diff / amount_tolerance)) if amount_tolerance > 0 else 0
        
        # Date score (closer = higher score)
        date_score = max(0, 1 - (date_diff / tolerance_days)) if tolerance_days > 0 else 0
        
        # Weighted combination
        confidence = (amount_score * 0.4) + (date_score * 0.3) + (merchant_similarity * 0.3)
        
        return min(1.0, max(0.0, confidence))
    
    def _get_match_reasons(self, amount_diff: float, date_diff: int, merchant_similarity: float) -> List[str]:
        """Get human-readable reasons for the match"""
        reasons = []
        
        if amount_diff <= 0.01:
            reasons.append("Exact amount match")
        elif amount_diff <= 1.00:
            reasons.append("Close amount match")
        
        if date_diff == 0:
            reasons.append("Same date")
        elif date_diff <= 1:
            reasons.append("Adjacent date")
        elif date_diff <= 3:
            reasons.append("Within 3 days")
        
        if merchant_similarity >= 0.8:
            reasons.append("Strong merchant match")
        elif merchant_similarity >= 0.5:
            reasons.append("Partial merchant match")
        
        return reasons
    
    def _is_receipt_relevant_transaction(self, transaction: TellerTransaction) -> bool:
        """Determine if a transaction is likely to have a receipt"""
        # Filter out internal transfers, fees, etc.
        irrelevant_categories = ['transfer', 'fee', 'interest', 'dividend']
        
        if transaction.category.lower() in irrelevant_categories:
            return False
        
        # Look for merchant-like descriptions
        merchant_indicators = ['*', 'inc', 'llc', 'corp', 'store', 'market', 'shop']
        description_lower = transaction.description.lower()
        
        return any(indicator in description_lower for indicator in merchant_indicators)
    
    def get_stats(self) -> Dict:
        """Get Teller client statistics"""
        stats = {
            'connected': self.is_connected(),
            'credentials_configured': self._has_credentials(),
            'connected_accounts': len(self.connected_accounts),
            'environment': self.environment
        }
        
        if self.connected_accounts:
            stats['accounts'] = [
                {
                    'id': acc.id,
                    'name': acc.name,
                    'type': acc.type,
                    'institution': acc.institution_name,
                    'balance': acc.balance
                }
                for acc in self.connected_accounts
            ]
        
        return stats
    
    def setup_webhook(self) -> bool:
        """Set up webhook for real-time transaction notifications"""
        if not self.is_connected() or not self.webhook_url:
            return False
        
        try:
            webhook_data = {
                'url': self.webhook_url,
                'events': ['transaction.created', 'transaction.updated']
            }
            
            response = self.session.post(
                f"{self.api_url}/webhooks",
                json=webhook_data
            )
            
            if response.status_code in [200, 201]:
                logger.info("Teller webhook configured successfully")
                return True
            else:
                logger.error(f"Failed to setup webhook: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting up webhook: {str(e)}")
            return False
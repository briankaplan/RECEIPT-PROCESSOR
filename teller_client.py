import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import ssl
from urllib.parse import urljoin
from dataclasses import dataclass
import tempfile
import base64

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

def load_certificates_from_environment():
    """
    Load Teller client certificate and key from environment variables or files.
    Supports both PEM and base64-encoded (.b64) files.
    Returns (cert_path, key_path) to use for SSL connections.
    Adds debug logging to print the first few lines of the decoded temp files and original PEM files.
    """
    cert_path = os.getenv('TELLER_CERT_PATH', './credentials/teller_certificate.pem')
    key_path = os.getenv('TELLER_KEY_PATH', './credentials/teller_private_key.pem')
    
    def print_file_head(path, label):
        if path and os.path.exists(path):
            with open(path, 'r') as f:
                lines = f.readlines()
                logger.info(f"[DEBUG] {label} ({path}):\n" + ''.join(lines[:5]))
        else:
            logger.warning(f"[DEBUG] {label} not found: {path}")
    
    # Print original PEM file heads
    if cert_path.endswith('.pem') and os.path.exists(cert_path):
        print_file_head(cert_path, 'Original PEM Certificate')
    if key_path.endswith('.pem') and os.path.exists(key_path):
        print_file_head(key_path, 'Original PEM Key')
    
    # If .b64 files exist, decode them to temp .pem files
    if cert_path.endswith('.b64') and os.path.exists(cert_path):
        with open(cert_path, 'rb') as f:
            b64_data = f.read()
            pem_data = base64.b64decode(b64_data)
            temp_cert = tempfile.NamedTemporaryFile(delete=False, suffix='.pem')
            temp_cert.write(pem_data)
            temp_cert.close()
            cert_path = temp_cert.name
            print_file_head(cert_path, 'Decoded Temp Certificate')
    elif os.path.exists(cert_path):
        # Use as-is if .pem
        pass
    else:
        cert_path = None
    
    if key_path.endswith('.b64') and os.path.exists(key_path):
        with open(key_path, 'rb') as f:
            b64_data = f.read()
            pem_data = base64.b64decode(b64_data)
            temp_key = tempfile.NamedTemporaryFile(delete=False, suffix='.pem')
            temp_key.write(pem_data)
            temp_key.close()
            key_path = temp_key.name
            print_file_head(key_path, 'Decoded Temp Key')
    elif os.path.exists(key_path):
        # Use as-is if .pem
        pass
    else:
        key_path = None
    
    return cert_path, key_path

def is_base64_content(content: str) -> bool:
    """Check if content appears to be base64 encoded"""
    if not content:
        return False
    
    # Basic checks for base64
    if len(content) < 100:  # Too short to be a certificate
        return False
    
    if '\n' in content or ' ' in content:  # Base64 should be single line without spaces
        return False
    
    # Check if all characters are valid base64
    base64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
    return all(c in base64_chars for c in content)

def validate_pem_format(content: str, pem_type: str) -> bool:
    """Validate that content is properly formatted PEM"""
    if not content:
        return False
    
    begin_marker = f"-----BEGIN {pem_type}-----"
    end_marker = f"-----END {pem_type}-----"
    
    if not content.startswith(begin_marker):
        logger.error(f"❌ Missing BEGIN marker for {pem_type}")
        return False
    
    if not content.rstrip().endswith(end_marker):
        logger.error(f"❌ Missing END marker for {pem_type}")
        return False
    
    # Check that there's content between markers
    content_lines = content.split('\n')[1:-1]  # Remove first and last line (markers)
    if not any(line.strip() for line in content_lines):
        logger.error(f"❌ No content between PEM markers for {pem_type}")
        return False
    
    return True

def create_temp_certificate_files(cert_content: str, key_content: str):
    """Create temporary certificate files for requests library"""
    try:
        # Create temporary files
        cert_fd, cert_temp_path = tempfile.mkstemp(suffix='.pem', text=True)
        key_fd, key_temp_path = tempfile.mkstemp(suffix='.pem', text=True)
        
        # Write certificate content
        with os.fdopen(cert_fd, 'w') as f:
            f.write(cert_content)
        
        # Write key content
        with os.fdopen(key_fd, 'w') as f:
            f.write(key_content)
        
        # Set secure permissions
        os.chmod(cert_temp_path, 0o600)
        os.chmod(key_temp_path, 0o600)
        
        logger.info(f"✅ Created temporary certificate files: {cert_temp_path}, {key_temp_path}")
        return cert_temp_path, key_temp_path
        
    except Exception as e:
        logger.error(f"❌ Failed to create temporary certificate files: {e}")
        return None, None

class TellerClient:
    """Teller API client for live bank transaction feeds and intelligent receipt matching"""
    
    def __init__(self, access_token=None):
        self.application_id = os.getenv('TELLER_APPLICATION_ID')
        self.api_url = os.getenv('TELLER_API_URL', 'https://api.teller.io')
        self.api_version = os.getenv('TELLER_API_VERSION', '2020-10-12')
        self.environment = os.getenv('TELLER_ENVIRONMENT', 'sandbox')
        self.webhook_url = os.getenv('TELLER_WEBHOOK_URL')
        self.signing_secret = os.getenv('TELLER_SIGNING_SECRET')
        
        # Load certificates using the enhanced loading function
        self.cert_path, self.key_path = load_certificates_from_environment()
        
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
        """Get connection and transaction statistics"""
        try:
            if not self.is_connected():
                return {
                    'connected': False,
                    'accounts_count': 0,
                    'total_transactions': 0,
                    'last_sync': None
                }
            
            accounts = self.get_connected_accounts()
            total_transactions = 0
            
            for account in accounts:
                try:
                    transactions = self.get_transactions(account.id, limit=1)
                    if transactions:
                        # Get total count from account metadata if available
                        total_transactions += len(transactions)
                except Exception as e:
                    logger.warning(f"Error getting transactions for account {account.id}: {e}")
            
            return {
                'connected': True,
                'accounts_count': len(accounts),
                'total_transactions': total_transactions,
                'last_sync': datetime.now().isoformat(),
                'environment': self.environment
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'connected': False,
                'error': str(e)
            }

    # ===== TELLER CONNECT METHODS =====
    
    def get_accounts_with_token(self, access_token: str) -> List[Dict]:
        """Get accounts using Teller Connect access token"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(f"{self.api_url}/accounts", headers=headers)
            response.raise_for_status()
            
            accounts = response.json()
            logger.info(f"Retrieved {len(accounts)} accounts from Teller")
            return accounts
            
        except Exception as e:
            logger.error(f"Error getting accounts with token: {e}")
            return []
    
    def get_transactions_with_token(self, access_token: str, account_id: str, days_back: int = 30) -> List[Dict]:
        """Get transactions using Teller Connect access token"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            params = {
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'limit': 1000  # Get more transactions
            }
            
            response = requests.get(
                f"{self.api_url}/accounts/{account_id}/transactions", 
                headers=headers, 
                params=params
            )
            response.raise_for_status()
            
            transactions = response.json()
            logger.info(f"Retrieved {len(transactions)} transactions from account {account_id}")
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting transactions with token: {e}")
            return []
    
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
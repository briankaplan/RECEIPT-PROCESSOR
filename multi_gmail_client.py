import os
import pickle
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import base64

logger = logging.getLogger(__name__)

class MultiGmailClient:
    """Gmail API client with multi-account and parallel receipt fetching"""

    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]

    def __init__(self):
        # Load account configuration from environment variables
        self.accounts = {
            os.getenv('GMAIL_ACCOUNT_1_EMAIL', 'kaplan.brian@gmail.com'): {
                'email': os.getenv('GMAIL_ACCOUNT_1_EMAIL', 'kaplan.brian@gmail.com'),
                'pickle_file': os.getenv('GMAIL_ACCOUNT_1_PICKLE_FILE', 'gmail_tokens/kaplan_brian_gmail.pickle'),
                'service': None
            },
            os.getenv('GMAIL_ACCOUNT_2_EMAIL', 'brian@downhome.com'): {
                'email': os.getenv('GMAIL_ACCOUNT_2_EMAIL', 'brian@downhome.com'),
                'pickle_file': os.getenv('GMAIL_ACCOUNT_2_PICKLE_FILE', 'gmail_tokens/brian_downhome.pickle'),
                'service': None
            },
            os.getenv('GMAIL_ACCOUNT_3_EMAIL', 'brian@musiccityrodeo.com'): {
                'email': os.getenv('GMAIL_ACCOUNT_3_EMAIL', 'brian@musiccityrodeo.com'),
                'pickle_file': os.getenv('GMAIL_ACCOUNT_3_PICKLE_FILE', 'gmail_tokens/brian_musiccityrodeo.pickle'),
                'service': None
            }
        }

    def init_services(self):
        for account in self.accounts.values():
            creds = None
            pickle_file = account['pickle_file']
            
            if os.path.exists(pickle_file):
                try:
                    # Try loading as regular pickle first
                    with open(pickle_file, 'rb') as token:
                        creds = pickle.load(token)
                    logger.info(f"✅ Loaded regular pickle file: {pickle_file}")
                except Exception as pickle_error:
                    # If regular pickle fails, try base64-encoded pickle
                    try:
                        logger.info(f"🔄 Regular pickle failed, trying base64 format: {pickle_file}")
                        with open(pickle_file, 'r') as token:
                            base64_data = token.read().strip()
                            decoded_data = base64.b64decode(base64_data)
                            creds = pickle.loads(decoded_data)
                        logger.info(f"✅ Loaded base64-encoded pickle file: {pickle_file}")
                    except Exception as b64_error:
                        logger.error(f"❌ Failed to load pickle file {pickle_file}")
                        logger.error(f"   Regular pickle error: {pickle_error}")
                        logger.error(f"   Base64 pickle error: {b64_error}")
                        continue
            else:
                logger.warning(f"⚠️ Pickle file not found: {pickle_file}")
                continue
                
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info(f"🔄 Refreshed expired credentials for {account['email']}")
                except Exception as refresh_error:
                    logger.error(f"❌ Failed to refresh credentials for {account['email']}: {refresh_error}")
                    continue
                    
            if creds and creds.valid:
                try:
                    account['service'] = build('gmail', 'v1', credentials=creds)
                    logger.info(f"✅ Gmail service built for {account['email']}")
                except Exception as service_error:
                    logger.error(f"❌ Failed to build Gmail service for {account['email']}: {service_error}")
            else:
                logger.error(f"❌ Invalid credentials for {account['email']}")

    def search_receipt_ids(self, service, user_id='me', days=365) -> List[str]:
        """OPTIMIZED: Search for receipt messages with better filtering"""
        from datetime import datetime, timedelta
        after_date = (datetime.now() - timedelta(days=days)).strftime('%Y/%m/%d')
        
        # Enhanced query with more receipt indicators
        receipt_terms = [
            "receipt", "invoice", "order", "bill", "payment", "confirmation",
            "purchase", "transaction", "statement", "refund"
        ]
        
        # Common merchant domains that send receipts
        merchant_domains = [
            "amazon.com", "paypal.com", "stripe.com", "square.com", 
            "walmart.com", "target.com", "costco.com", "bestbuy.com",
            "apple.com", "google.com", "microsoft.com", "uber.com"
        ]
        
        # Build comprehensive query
        subject_query = " OR ".join([f"subject:{term}" for term in receipt_terms])
        domain_query = " OR ".join([f"from:{domain}" for domain in merchant_domains])
        
        query = f"has:attachment ({subject_query} OR {domain_query}) after:{after_date}"
        
        try:
            all_message_ids = []
            next_page_token = None
            
            # Fetch all pages of results
            while True:
                params = {
                    'userId': user_id, 
                    'q': query, 
                    'maxResults': 500  # Increased from 100
                }
                
                if next_page_token:
                    params['pageToken'] = next_page_token
                
                response = service.users().messages().list(**params).execute()
                messages = response.get('messages', [])
                all_message_ids.extend([msg['id'] for msg in messages])
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
                # Limit to prevent excessive API calls
                if len(all_message_ids) >= 1000:
                    break
            
            logger.info(f"Found {len(all_message_ids)} potential receipt messages")
            return all_message_ids
            
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

    def fetch_receipt_metadata_parallel(self, days=365, max_per_account=200) -> List[Dict]:
        """OPTIMIZED: Fetch receipt metadata from all accounts with better performance"""
        import time
        start_time = time.time()
        
        self.init_services()
        all_receipts = []
        
        logger.info(f"🚀 Starting parallel receipt search across {len(self.accounts)} accounts")
        
        # Process all accounts in parallel
        with ThreadPoolExecutor(max_workers=len(self.accounts)) as account_executor:
            account_futures = []
            
            for acct, data in self.accounts.items():
                service = data['service']
                if not service:
                    logger.warning(f"⚠️ No service available for {acct}")
                    continue
                    
                future = account_executor.submit(
                    self._process_account_messages, 
                    acct, service, days, max_per_account
                )
                account_futures.append(future)
            
            # Collect results from all accounts
            for future in as_completed(account_futures):
                try:
                    account_receipts = future.result(timeout=60)  # 60-second timeout per account
                    all_receipts.extend(account_receipts)
                except Exception as e:
                    logger.error(f"❌ Account processing failed: {e}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ Completed parallel search in {elapsed_time:.2f}s. Found {len(all_receipts)} total receipts")
        
        # Sort by most recent first
        all_receipts.sort(key=lambda x: x.get('date', ''), reverse=True)
        return all_receipts
    
    def _process_account_messages(self, account_email: str, service, days: int, max_messages: int) -> List[Dict]:
        """Process messages for a single account"""
        try:
            # Search for receipt messages
            msg_ids = self.search_receipt_ids(service, days=days)
            
            # Limit messages per account
            if len(msg_ids) > max_messages:
                msg_ids = msg_ids[:max_messages]
                logger.info(f"📧 {account_email}: Limited to {max_messages} most recent messages")
            
            logger.info(f"📧 {account_email}: Processing {len(msg_ids)} messages")
            
            account_receipts = []
            
            # Process messages in parallel for this account
            with ThreadPoolExecutor(max_workers=15) as executor:
                futures = [
                    executor.submit(self.get_metadata, service, msg_id) 
                    for msg_id in msg_ids
                ]
                
                for future in as_completed(futures):
                    try:
                        metadata = future.result(timeout=10)  # 10-second timeout per message
                        if metadata:
                            metadata['account'] = account_email  # Add account info
                            account_receipts.append(metadata)
                    except Exception as e:
                        logger.warning(f"⚠️ Message metadata failed: {e}")
            
            logger.info(f"✅ {account_email}: Retrieved {len(account_receipts)} receipt metadata")
            return account_receipts
            
        except Exception as e:
            logger.error(f"❌ Failed to process account {account_email}: {e}")
            return []
    
    def connect_account(self, email: str) -> bool:
        """Connect to a specific Gmail account"""
        if email not in self.accounts:
            logger.error(f"❌ Unknown Gmail account: {email}")
            return False
        
        account = self.accounts[email]
        
        try:
            creds = None
            pickle_file = account['pickle_file']
            
            # Load existing credentials with base64 support
            if os.path.exists(pickle_file):
                try:
                    # Try loading as regular pickle first
                    with open(pickle_file, 'rb') as token:
                        creds = pickle.load(token)
                    logger.info(f"📁 Loaded regular pickle credentials for {email} from {pickle_file}")
                except Exception as pickle_error:
                    # If regular pickle fails, try base64-encoded pickle
                    try:
                        logger.info(f"🔄 Trying base64 format for {email}")
                        with open(pickle_file, 'r') as token:
                            base64_data = token.read().strip()
                            decoded_data = base64.b64decode(base64_data)
                            creds = pickle.loads(decoded_data)
                        logger.info(f"📁 Loaded base64-encoded pickle credentials for {email}")
                    except Exception as b64_error:
                        logger.error(f"❌ Failed to load credentials for {email}")
                        logger.error(f"   Regular pickle error: {pickle_error}")
                        logger.error(f"   Base64 pickle error: {b64_error}")
                        return False
            else:
                logger.error(f"❌ No credentials file found: {pickle_file}")
                return False
            
            # Refresh if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info(f"🔄 Refreshed credentials for {email}")
            
            # Build service
            if creds and creds.valid:
                account['service'] = build('gmail', 'v1', credentials=creds)
                logger.info(f"✅ Connected to Gmail account: {email}")
                return True
            else:
                logger.error(f"❌ Invalid credentials for {email}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to {email}: {e}")
            return False
    
    def search_messages(self, email: str, query: str, max_results: int = 100, days_back: int = 365) -> List[Dict]:
        """Search for messages in a specific Gmail account"""
        if email not in self.accounts or not self.accounts[email].get('service'):
            logger.error(f"❌ Gmail account not connected: {email}")
            return []
        
        service = self.accounts[email]['service']
        
        try:
            from datetime import datetime, timedelta
            after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
            full_query = f"{query} after:{after_date}"
            
            response = service.users().messages().list(
                userId='me',
                q=full_query,
                maxResults=max_results
            ).execute()
            
            messages = response.get('messages', [])
            logger.info(f"📧 Found {len(messages)} messages for query: {query}")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Gmail search failed for {email}: {e}")
            return []
    
    def get_message_content(self, email: str, message_id: str) -> Optional[Dict]:
        """Get full message content including attachments"""
        if email not in self.accounts or not self.accounts[email].get('service'):
            logger.error(f"❌ Gmail account not connected: {email}")
            return None
        
        service = self.accounts[email]['service']
        
        try:
            message = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message.get('payload', {}).get('headers', [])
            result = {
                'id': message_id,
                'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), ''),
                'from': next((h['value'] for h in headers if h['name'] == 'From'), ''),
                'date': next((h['value'] for h in headers if h['name'] == 'Date'), ''),
                'body': '',
                'attachments': []
            }
            
            # Extract body and attachments
            self._extract_content_from_payload(message.get('payload', {}), result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get message content {message_id}: {e}")
            return None
    
    def _extract_content_from_payload(self, payload: Dict, result: Dict):
        """Recursively extract content from message payload"""
        if payload.get('parts'):
            for part in payload['parts']:
                self._extract_content_from_payload(part, result)
        else:
            # Extract body text
            if payload.get('mimeType') == 'text/plain':
                body_data = payload.get('body', {}).get('data', '')
                if body_data:
                    try:
                        text = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        result['body'] += text + '\n'
                    except:
                        pass
            
            # Extract attachments
            filename = payload.get('filename', '')
            attachment_id = payload.get('body', {}).get('attachmentId')
            if filename and attachment_id:
                result['attachments'].append({
                    'filename': filename,
                    'attachment_id': attachment_id,
                    'mime_type': payload.get('mimeType', ''),
                    'size': payload.get('body', {}).get('size', 0)
                })

    def get_available_accounts(self) -> List[Dict]:
        """Get list of available Gmail accounts"""
        self.init_services()
        available = []
        
        for email, data in self.accounts.items():
            if data.get('service'):
                available.append({
                    'email': email,
                    'status': 'connected',
                    'pickle_file': data['pickle_file']
                })
            else:
                available.append({
                    'email': email,
                    'status': 'disconnected',
                    'pickle_file': data['pickle_file']
                })
        
        return available
    
    def get_stats(self) -> Dict:
        """Get multi-account Gmail client statistics"""
        self.init_services()
        
        total_accounts = len(self.accounts)
        connected_accounts = sum(1 for data in self.accounts.values() if data.get('service'))
        
        return {
            'total_accounts': total_accounts,
            'connected_accounts': connected_accounts,
            'connection_rate': connected_accounts / total_accounts if total_accounts > 0 else 0,
            'accounts': self.get_available_accounts()
        }

    def fetch_receipt_metadata_teller_guided(self, teller_transactions: List[Dict], days=30, max_per_account=100) -> List[Dict]:
        """REVOLUTIONARY: Use Teller transaction data to guide Gmail searches for PERFECT precision"""
        import time
        
        start_time = time.time()
        
        self.init_services()
        all_targeted_receipts = []
        
        logger.info(f"🎯 TELLER-GUIDED SEARCH: Processing {len(teller_transactions)} bank transactions")
        
        # Extract precise search targets from Teller data
        search_targets = self._extract_search_targets_from_transactions(teller_transactions, days)
        
        logger.info(f"🎯 Generated {len(search_targets)} precise search targets")
        
        # Process all accounts in parallel with targeted searches
        with ThreadPoolExecutor(max_workers=len(self.accounts)) as account_executor:
            account_futures = []
            
            for acct, data in self.accounts.items():
                service = data['service']
                if not service:
                    logger.warning(f"⚠️ No service available for {acct}")
                    continue
                    
                future = account_executor.submit(
                    self._process_account_with_targets, 
                    acct, service, search_targets, max_per_account
                )
                account_futures.append(future)
            
            # Collect results from all accounts
            for future in as_completed(account_futures):
                try:
                    account_receipts = future.result(timeout=90)  # Longer timeout for precision
                    all_targeted_receipts.extend(account_receipts)
                except Exception as e:
                    logger.error(f"❌ Targeted account processing failed: {e}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"🎯 TELLER-GUIDED SEARCH completed in {elapsed_time:.2f}s. Found {len(all_targeted_receipts)} targeted receipts")
        
        # Sort by relevance (transaction match probability)
        all_targeted_receipts.sort(key=lambda x: x.get('match_probability', 0), reverse=True)
        return all_targeted_receipts

    def _extract_search_targets_from_transactions(self, transactions: List[Dict], days: int) -> List[Dict]:
        """Extract precise search targets from Teller transaction data"""
        import re
        
        targets = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for tx in transactions:
            try:
                # Parse transaction data
                tx_date = self._parse_transaction_date(tx.get('date'))
                if not tx_date or tx_date < cutoff_date:
                    continue
                
                tx_amount = abs(float(tx.get('amount', 0)))
                if tx_amount < 1.0:  # Skip small amounts
                    continue
                
                tx_description = tx.get('description', '').strip()
                if not tx_description:
                    continue
                
                # Extract merchant information
                merchant_info = self._extract_merchant_from_description(tx_description)
                
                # Create targeted search parameters
                target = {
                    'transaction_id': tx.get('id'),
                    'amount': tx_amount,
                    'date': tx_date,
                    'date_range': {
                        'start': (tx_date - timedelta(days=2)).strftime('%Y/%m/%d'),
                        'end': (tx_date + timedelta(days=2)).strftime('%Y/%m/%d')
                    },
                    'merchant_keywords': merchant_info['keywords'],
                    'merchant_domain': merchant_info['domain'],
                    'description': tx_description,
                    'search_queries': self._generate_targeted_queries(merchant_info, tx_amount, tx_date),
                    'priority': merchant_info['priority']
                }
                
                targets.append(target)
                
            except Exception as e:
                logger.warning(f"Failed to process transaction: {e}")
                continue
        
        # Sort by priority (high-confidence merchants first)
        targets.sort(key=lambda x: x['priority'], reverse=True)
        return targets

    def _extract_merchant_from_description(self, description: str) -> Dict:
        """Extract merchant information from transaction description"""
        description = description.lower().strip()
        
        # Known high-confidence merchant patterns
        merchant_patterns = {
            'amazon': {'keywords': ['amazon', 'amzn'], 'domain': 'amazon.com', 'priority': 10},
            'uber': {'keywords': ['uber'], 'domain': 'uber.com', 'priority': 9},
            'paypal': {'keywords': ['paypal', 'pp*'], 'domain': 'paypal.com', 'priority': 9},
            'apple': {'keywords': ['apple', 'app store'], 'domain': 'apple.com', 'priority': 9},
            'google': {'keywords': ['google', 'goog'], 'domain': 'google.com', 'priority': 9},
            'stripe': {'keywords': ['stripe'], 'domain': 'stripe.com', 'priority': 8},
            'square': {'keywords': ['square', 'sq*'], 'domain': 'squareup.com', 'priority': 8},
            'walmart': {'keywords': ['walmart', 'wal-mart'], 'domain': 'walmart.com', 'priority': 8},
            'target': {'keywords': ['target'], 'domain': 'target.com', 'priority': 8},
            'costco': {'keywords': ['costco'], 'domain': 'costco.com', 'priority': 8},
        }
        
        # Check for known merchants
        for merchant, info in merchant_patterns.items():
            if any(keyword in description for keyword in info['keywords']):
                return {
                    'merchant': merchant,
                    'keywords': info['keywords'],
                    'domain': info['domain'],
                    'priority': info['priority']
                }
        
        # Extract generic merchant name (fallback)
        import re
        
        # Common patterns for merchant extraction
        patterns = [
            r'(\w+(?:\s+\w+)*)\s+\d{2}/\d{2}',  # "MERCHANT NAME 12/25"
            r'(\w+(?:\s+\w+)*)\s+#\d+',         # "MERCHANT NAME #123"
            r'^([A-Z][A-Za-z\s&]+)',            # Starting with capital letter
        ]
        
        extracted_name = None
        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                extracted_name = match.group(1).strip()
                break
        
        if not extracted_name:
            # Use first few words as fallback
            words = description.split()
            extracted_name = ' '.join(words[:3]) if len(words) >= 3 else description
        
        return {
            'merchant': extracted_name,
            'keywords': [extracted_name.lower()],
            'domain': None,
            'priority': 5  # Medium priority for unknown merchants
        }

    def _generate_targeted_queries(self, merchant_info: Dict, amount: float, date: datetime) -> List[str]:
        """Generate highly targeted Gmail search queries"""
        queries = []
        
        date_str = date.strftime('%Y/%m/%d')
        date_range = f"after:{(date - timedelta(days=2)).strftime('%Y/%m/%d')} before:{(date + timedelta(days=2)).strftime('%Y/%m/%d')}"
        
        merchant = merchant_info['merchant']
        keywords = merchant_info['keywords']
        domain = merchant_info['domain']
        
        # Primary query: Merchant + date range + attachment
        if domain:
            queries.append(f"from:{domain} has:attachment {date_range}")
        
        # Keyword-based queries
        for keyword in keywords:
            queries.append(f"(subject:{keyword} OR {keyword}) has:attachment {date_range}")
        
        # Amount-based query (if amount is unique enough)
        if 10 <= amount <= 1000:
            amount_str = f"{amount:.2f}".replace('.', '')
            queries.append(f"{amount_str} has:attachment {date_range}")
        
        # Receipt confirmation query
        queries.append(f"(receipt OR confirmation OR invoice) \"{merchant}\" has:attachment {date_range}")
        
        return queries

    def _process_account_with_targets(self, account_email: str, service, search_targets: List[Dict], max_messages: int) -> List[Dict]:
        """Process a single account with targeted searches"""
        try:
            account_receipts = []
            processed_message_ids = set()  # Avoid duplicates
            
            logger.info(f"🎯 {account_email}: Starting targeted search with {len(search_targets)} targets")
            
            # Process each search target
            for i, target in enumerate(search_targets):
                if len(account_receipts) >= max_messages:
                    break
                
                # Execute all targeted queries for this transaction
                target_msg_ids = set()
                
                for query in target['search_queries']:
                    try:
                        msg_ids = self._execute_targeted_query(service, query)
                        target_msg_ids.update(msg_ids)
                        
                        # Limit to prevent API abuse
                        if len(target_msg_ids) > 20:
                            break
                            
                    except Exception as e:
                        logger.warning(f"Query failed: {query} - {e}")
                        continue
                
                # Process found messages for this target
                for msg_id in target_msg_ids:
                    if msg_id in processed_message_ids:
                        continue
                    
                    try:
                        metadata = self.get_metadata(service, msg_id)
                        if metadata:
                            # Enhance metadata with transaction matching info
                            metadata['account'] = account_email
                            metadata['target_transaction'] = target['transaction_id']
                            metadata['match_probability'] = self._calculate_email_transaction_probability(metadata, target)
                            metadata['target_amount'] = target['amount']
                            metadata['target_date'] = target['date'].isoformat()
                            
                            account_receipts.append(metadata)
                            processed_message_ids.add(msg_id)
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Message processing failed for {msg_id}: {e}")
                
                # Progress logging
                if (i + 1) % 10 == 0:
                    logger.info(f"🎯 {account_email}: Processed {i + 1}/{len(search_targets)} targets, found {len(account_receipts)} receipts")
            
            logger.info(f"✅ {account_email}: Targeted search complete - {len(account_receipts)} receipts found")
            return account_receipts
            
        except Exception as e:
            logger.error(f"❌ Failed targeted processing for {account_email}: {e}")
            return []

    def _execute_targeted_query(self, service, query: str) -> List[str]:
        """Execute a single targeted Gmail query"""
        try:
            response = service.users().messages().list(
                userId='me', 
                q=query, 
                maxResults=50  # Smaller batches for precision
            ).execute()
            
            messages = response.get('messages', [])
            return [msg['id'] for msg in messages]
            
        except Exception as e:
            logger.warning(f"Targeted query failed: {query} - {e}")
            return []

    def _calculate_email_transaction_probability(self, email_metadata: Dict, target: Dict) -> float:
        """Calculate probability that email corresponds to the target transaction"""
        score = 0.0
        
        subject = email_metadata.get('subject', '').lower()
        sender = email_metadata.get('from', '').lower()
        merchant = target['merchant_keywords'][0] if target['merchant_keywords'] else ''
        
        # Domain match (highest confidence)
        if target['merchant_domain'] and target['merchant_domain'] in sender:
            score += 0.6
        
        # Keyword match in subject
        if any(keyword in subject for keyword in target['merchant_keywords']):
            score += 0.3
        
        # Receipt/confirmation keywords
        if any(word in subject for word in ['receipt', 'confirmation', 'invoice', 'order']):
            score += 0.1
        
        return min(score, 1.0)

    def _parse_transaction_date(self, date_str) -> Optional[datetime]:
        """Parse transaction date from various formats"""
        if not date_str:
            return None
        
        formats = [
            '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ',
            '%m/%d/%Y', '%d/%m/%Y', '%B %d, %Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).strip(), fmt)
            except ValueError:
                continue
        
        return None
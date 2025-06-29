#!/usr/bin/env python3
"""
Full Receipt Scan System
Comprehensive scan with fixes for $0.0 amounts and intelligent receipt detection
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FullReceiptScanner:
    """
    Comprehensive receipt scanner that fixes common issues and performs full analysis
    """
    
    def __init__(self, gmail_service=None, mongo_client=None, config=None):
        self.gmail_service = gmail_service
        self.mongo_client = mongo_client
        self.config = config or {}
        
        # Initialize components
        self._initialize_components()
        
        # Scan results
        self.scan_results = {
            'total_emails_processed': 0,
            'receipts_found': 0,
            'successful_matches': 0,
            'failed_extractions': 0,
            'zero_amount_fixes': 0,
            'date_range': {},
            'errors': [],
            'intelligence_learned': {}
        }
    
    def _initialize_components(self):
        """Initialize all system components"""
        try:
            # Import enhanced system
            from enhanced_receipt_system import EnhancedReceiptSystem
            self.enhanced_system = EnhancedReceiptSystem(
                self.gmail_service, self.mongo_client, self.config
            )
            logger.info("✅ Enhanced receipt system initialized")
        except Exception as e:
            logger.warning(f"⚠️ Enhanced system not available: {e}")
            self.enhanced_system = None
        
        try:
            # Import intelligent processor
            from intelligent_receipt_processor import IntelligentReceiptProcessor
            self.intelligence = IntelligentReceiptProcessor()
            logger.info("✅ Intelligent processor initialized")
        except Exception as e:
            logger.warning(f"⚠️ Intelligent processor not available: {e}")
            self.intelligence = None
        
        try:
            # Import existing search
            from personalized_email_search import PersonalizedEmailSearchSystem
            self.existing_search = PersonalizedEmailSearchSystem(
                self.gmail_service, self.mongo_client, self.config
            )
            logger.info("✅ Existing search system initialized")
        except Exception as e:
            logger.warning(f"⚠️ Existing search not available: {e}")
            self.existing_search = None
    
    async def run_full_scan(self, start_date: str = "2024-07-01", 
                           end_date: str = "2025-06-28") -> Dict:
        """
        Run comprehensive full scan of all receipts
        """
        logger.info(f"🚀 Starting full receipt scan from {start_date} to {end_date}")
        
        # Calculate days to scan
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end - start).days
        
        logger.info(f"📅 Scanning {total_days} days of emails")
        
        # Get transactions for the period
        transactions = await self._get_transactions_for_period(start_date, end_date)
        logger.info(f"💰 Found {len(transactions)} transactions to match")
        
        # Initialize scan results
        self.scan_results['date_range'] = {
            'start_date': start_date,
            'end_date': end_date,
            'total_days': total_days
        }
        
        # Scan in chunks to avoid overwhelming the system
        chunk_size = 30  # 30 days at a time
        all_receipts = []
        all_matches = []
        
        current_date = start
        while current_date <= end:
            chunk_end = min(current_date + timedelta(days=chunk_size), end)
            
            logger.info(f"📅 Scanning chunk: {current_date.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}")
            
            # Scan this chunk
            chunk_results = await self._scan_chunk(
                current_date.strftime('%Y-%m-%d'),
                chunk_end.strftime('%Y-%m-%d'),
                transactions
            )
            
            all_receipts.extend(chunk_results.get('receipts', []))
            all_matches.extend(chunk_results.get('matches', []))
            
            # Update scan results
            self.scan_results['total_emails_processed'] += chunk_results.get('emails_processed', 0)
            self.scan_results['receipts_found'] += chunk_results.get('receipts_found', 0)
            self.scan_results['successful_matches'] += chunk_results.get('successful_matches', 0)
            self.scan_results['failed_extractions'] += chunk_results.get('failed_extractions', 0)
            self.scan_results['zero_amount_fixes'] += chunk_results.get('zero_amount_fixes', 0)
            
            # Move to next chunk
            current_date = chunk_end + timedelta(days=1)
        
        # Final processing
        final_results = await self._process_final_results(all_receipts, all_matches, transactions)
        
        # Save results
        self._save_scan_results()
        
        logger.info("✅ Full scan complete!")
        logger.info(f"📊 Final Results:")
        logger.info(f"  - Total emails processed: {self.scan_results['total_emails_processed']}")
        logger.info(f"  - Receipts found: {self.scan_results['receipts_found']}")
        logger.info(f"  - Successful matches: {self.scan_results['successful_matches']}")
        logger.info(f"  - Zero amount fixes: {self.scan_results['zero_amount_fixes']}")
        
        return final_results
    
    async def _scan_chunk(self, start_date: str, end_date: str, 
                         transactions: List[Dict]) -> Dict:
        """
        Scan a specific date chunk
        """
        chunk_results = {
            'emails_processed': 0,
            'receipts_found': 0,
            'successful_matches': 0,
            'failed_extractions': 0,
            'zero_amount_fixes': 0,
            'receipts': [],
            'matches': []
        }
        
        try:
            # Use enhanced search if available
            if self.enhanced_system:
                search_results = await self.enhanced_system.enhanced_search(
                    days_back=self._calculate_days_back(start_date),
                    transactions=transactions,
                    use_existing_search=True
                )
            elif self.existing_search:
                search_results = await self.existing_search.execute_personalized_search(
                    days_back=self._calculate_days_back(start_date)
                )
            else:
                logger.warning("⚠️ No search system available")
                return chunk_results
            
            emails = search_results.get('emails', [])
            chunk_results['emails_processed'] = len(emails)
            
            # Process each email
            for email in emails:
                receipt_data = await self._process_email_receipt(email, transactions)
                if receipt_data:
                    chunk_results['receipts'].append(receipt_data)
                    chunk_results['receipts_found'] += 1
                    
                    # Check for matches
                    matches = self._find_transaction_matches(receipt_data, transactions)
                    if matches:
                        chunk_results['matches'].extend(matches)
                        chunk_results['successful_matches'] += len(matches)
                    
                    # Check for zero amount fixes
                    if receipt_data.get('amount', 0) > 0 and receipt_data.get('original_amount', 0) == 0:
                        chunk_results['zero_amount_fixes'] += 1
        
        except Exception as e:
            logger.error(f"❌ Error scanning chunk {start_date} to {end_date}: {e}")
            self.scan_results['errors'].append({
                'chunk': f"{start_date} to {end_date}",
                'error': str(e)
            })
        
        return chunk_results
    
    async def _process_email_receipt(self, email: Dict, transactions: List[Dict]) -> Optional[Dict]:
        """
        Process a single email for receipt extraction with fixes
        """
        try:
            # Extract basic receipt data
            receipt_data = {
                'email_id': email.get('id'),
                'subject': email.get('subject', ''),
                'from_email': email.get('from', ''),
                'date': email.get('date', ''),
                'body': email.get('body', ''),
                'has_attachments': email.get('has_attachments', False),
                'receipt_likelihood': email.get('receipt_likelihood', 0),
                'receipt_confidence': email.get('receipt_confidence', 0)
            }
            
            # Extract amount with multiple fallback methods
            amount = await self._extract_amount_with_fallbacks(email, transactions)
            receipt_data['amount'] = amount
            receipt_data['original_amount'] = amount
            
            # Fix zero amounts
            if amount == 0:
                fixed_amount = self._fix_zero_amount(email, transactions)
                if fixed_amount > 0:
                    receipt_data['amount'] = fixed_amount
                    receipt_data['amount_fixed'] = True
                    receipt_data['fix_method'] = 'transaction_matching'
            
            # Extract merchant
            merchant = self._extract_merchant_with_intelligence(email, transactions)
            receipt_data['merchant'] = merchant
            
            # Only return if we have meaningful data
            if receipt_data['amount'] > 0 or receipt_data['merchant']:
                return receipt_data
            
        except Exception as e:
            logger.warning(f"⚠️ Error processing email {email.get('id', 'unknown')}: {e}")
        
        return None
    
    async def _extract_amount_with_fallbacks(self, email: Dict, transactions: List[Dict]) -> float:
        """
        Extract amount using multiple fallback methods
        """
        amount = 0.0
        
        # Method 1: Extract from email body using regex
        body = email.get('body', '')
        amount_patterns = [
            r'\$\s*(\d+\.?\d*)',  # $45.67
            r'(\d+\.?\d*)\s*USD',  # 45.67 USD
            r'Total:\s*\$?\s*(\d+\.?\d*)',  # Total: $45.67
            r'Amount:\s*\$?\s*(\d+\.?\d*)',  # Amount: $45.67
            r'(\d+\.?\d*)\s*dollars',  # 45.67 dollars
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            if matches:
                try:
                    amount = float(matches[0])
                    if amount > 0:
                        logger.info(f"💰 Extracted amount ${amount} from email body")
                        return amount
                except ValueError:
                    continue
        
        # Method 2: Extract from subject
        subject = email.get('subject', '')
        for pattern in amount_patterns:
            matches = re.findall(pattern, subject, re.IGNORECASE)
            if matches:
                try:
                    amount = float(matches[0])
                    if amount > 0:
                        logger.info(f"💰 Extracted amount ${amount} from subject")
                        return amount
                except ValueError:
                    continue
        
        # Method 3: Match with transactions by date and merchant
        email_date = email.get('date')
        if email_date:
            matching_transactions = [
                tx for tx in transactions 
                if tx.get('date') == email_date
            ]
            
            if len(matching_transactions) == 1:
                amount = matching_transactions[0].get('amount', 0)
                if amount > 0:
                    logger.info(f"💰 Matched amount ${amount} from transaction")
                    return amount
        
        return amount
    
    def _fix_zero_amount(self, email: Dict, transactions: List[Dict]) -> float:
        """
        Fix zero amounts using intelligent matching
        """
        email_date = email.get('date')
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        
        # Find transactions on the same date
        date_matches = [
            tx for tx in transactions 
            if tx.get('date') == email_date
        ]
        
        if len(date_matches) == 1:
            # Only one transaction on this date, likely a match
            return date_matches[0].get('amount', 0)
        
        # Multiple transactions, try to match by merchant keywords
        for tx in date_matches:
            tx_merchant = tx.get('merchant', '').lower()
            tx_description = tx.get('description', '').lower()
            
            # Check if merchant appears in email
            if tx_merchant in subject or tx_merchant in body:
                return tx.get('amount', 0)
            
            # Check if description keywords appear
            description_words = tx_description.split()
            for word in description_words:
                if len(word) > 3 and word in subject:
                    return tx.get('amount', 0)
        
        return 0.0
    
    def _extract_merchant_with_intelligence(self, email: Dict, transactions: List[Dict]) -> str:
        """
        Extract merchant using intelligent methods
        """
        # Method 1: Extract from email sender domain
        sender = email.get('from', '')
        domain = self._extract_domain(sender)
        
        # Common domain mappings
        domain_mappings = {
            'anthropic.com': 'ANTHROPIC',
            'claude.ai': 'CLAUDE',
            'netflix.com': 'NETFLIX',
            'spotify.com': 'SPOTIFY',
            'github.com': 'GITHUB',
            'apple.com': 'APPLE',
            'uber.com': 'UBER',
            'square.com': 'SQUARE',
            'paypal.com': 'PAYPAL',
            'stripe.com': 'STRIPE'
        }
        
        if domain in domain_mappings:
            return domain_mappings[domain]
        
        # Method 2: Extract from subject
        subject = email.get('subject', '')
        subject_lower = subject.lower()
        
        # Common merchant keywords
        merchant_keywords = {
            'claude': 'CLAUDE',
            'anthropic': 'ANTHROPIC',
            'netflix': 'NETFLIX',
            'spotify': 'SPOTIFY',
            'github': 'GITHUB',
            'apple': 'APPLE',
            'uber': 'UBER',
            'square': 'SQUARE',
            'paypal': 'PAYPAL',
            'stripe': 'STRIPE',
            'microsoft': 'MICROSOFT',
            'google': 'GOOGLE',
            'amazon': 'AMAZON'
        }
        
        for keyword, merchant in merchant_keywords.items():
            if keyword in subject_lower:
                return merchant
        
        # Method 3: Match with transactions
        email_date = email.get('date')
        if email_date:
            matching_transactions = [
                tx for tx in transactions 
                if tx.get('date') == email_date
            ]
            
            if len(matching_transactions) == 1:
                return matching_transactions[0].get('merchant', 'UNKNOWN')
        
        return 'UNKNOWN'
    
    def _find_transaction_matches(self, receipt_data: Dict, transactions: List[Dict]) -> List[Dict]:
        """
        Find matching transactions for a receipt
        """
        matches = []
        
        receipt_amount = receipt_data.get('amount', 0)
        receipt_date = receipt_data.get('date')
        receipt_merchant = receipt_data.get('merchant', '')
        
        for transaction in transactions:
            confidence = 0.0
            reasons = []
            
            # Amount matching
            tx_amount = transaction.get('amount', 0)
            if abs(receipt_amount - tx_amount) < 0.01:  # Exact amount match
                confidence += 0.5
                reasons.append('exact_amount_match')
            elif abs(receipt_amount - tx_amount) < 1.0:  # Close amount match
                confidence += 0.3
                reasons.append('close_amount_match')
            
            # Date matching
            tx_date = transaction.get('date')
            if receipt_date == tx_date:
                confidence += 0.3
                reasons.append('date_match')
            
            # Merchant matching
            tx_merchant = transaction.get('merchant', '').lower()
            if receipt_merchant.lower() in tx_merchant or tx_merchant in receipt_merchant.lower():
                confidence += 0.2
                reasons.append('merchant_match')
            
            if confidence > 0.5:  # High confidence threshold
                matches.append({
                    'transaction': transaction,
                    'receipt': receipt_data,
                    'confidence': confidence,
                    'reasons': reasons
                })
        
        return matches
    
    def _extract_domain(self, email: str) -> str:
        """Extract domain from email address"""
        if '@' in email:
            return email.split('@')[1].lower()
        return email.lower()
    
    def _calculate_days_back(self, start_date: str) -> int:
        """Calculate days back from start date to today"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        today = datetime.now()
        return (today - start).days
    
    async def _get_transactions_for_period(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Get transactions for the specified period
        """
        try:
            if self.mongo_client:
                # Query MongoDB for transactions
                db = self.mongo_client.get_database()
                collection = db.transactions
                
                transactions = list(collection.find({
                    'date': {
                        '$gte': start_date,
                        '$lte': end_date
                    }
                }))
                
                logger.info(f"📊 Retrieved {len(transactions)} transactions from MongoDB")
                return transactions
            else:
                logger.warning("⚠️ MongoDB not available, using empty transaction list")
                return []
        
        except Exception as e:
            logger.error(f"❌ Error retrieving transactions: {e}")
            return []
    
    async def _process_final_results(self, receipts: List[Dict], matches: List[Dict], 
                                   transactions: List[Dict]) -> Dict:
        """
        Process final scan results
        """
        # Calculate statistics
        total_transactions = len(transactions)
        matched_transactions = len(set(match['transaction']['id'] for match in matches if 'id' in match['transaction']))
        match_rate = (matched_transactions / total_transactions * 100) if total_transactions > 0 else 0
        
        # Generate insights
        insights = self._generate_insights(receipts, matches, transactions)
        
        # Learn from results
        if self.intelligence:
            learning_result = self.intelligence.learn_from_transactions(transactions)
            self.scan_results['intelligence_learned'] = learning_result
        
        return {
            'scan_summary': self.scan_results,
            'receipts': receipts,
            'matches': matches,
            'statistics': {
                'total_transactions': total_transactions,
                'total_receipts': len(receipts),
                'successful_matches': len(matches),
                'match_rate': match_rate,
                'zero_amount_fixes': self.scan_results['zero_amount_fixes']
            },
            'insights': insights
        }
    
    def _generate_insights(self, receipts: List[Dict], matches: List[Dict], 
                          transactions: List[Dict]) -> List[Dict]:
        """
        Generate insights from scan results
        """
        insights = []
        
        # Analyze match rate
        total_transactions = len(transactions)
        matched_transactions = len(set(match['transaction']['id'] for match in matches if 'id' in match['transaction']))
        
        if matched_transactions < total_transactions * 0.5:
            insights.append({
                'type': 'low_match_rate',
                'message': f"Only {matched_transactions}/{total_transactions} transactions matched to receipts",
                'suggestion': "Consider expanding search criteria or improving receipt detection"
            })
        
        # Analyze zero amount fixes
        if self.scan_results['zero_amount_fixes'] > 0:
            insights.append({
                'type': 'zero_amount_fixes',
                'message': f"Fixed {self.scan_results['zero_amount_fixes']} receipts with $0.0 amounts",
                'suggestion': "Receipt extraction is working but needs improvement"
            })
        
        # Analyze merchant patterns
        merchants = [receipt.get('merchant') for receipt in receipts if receipt.get('merchant')]
        if merchants:
            from collections import Counter
            merchant_counts = Counter(merchants)
            top_merchant = merchant_counts.most_common(1)[0]
            
            insights.append({
                'type': 'merchant_pattern',
                'message': f"Most common receipt merchant: {top_merchant[0]} ({top_merchant[1]} receipts)",
                'suggestion': "Focus on improving detection for this merchant"
            })
        
        return insights
    
    def _save_scan_results(self):
        """
        Save scan results to file
        """
        try:
            filename = f"full_scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w') as f:
                json.dump(self.scan_results, f, indent=2, default=str)
            
            logger.info(f"💾 Saved scan results to {filename}")
            
        except Exception as e:
            logger.error(f"❌ Error saving scan results: {e}")

# Convenience function
async def run_full_receipt_scan(gmail_service=None, mongo_client=None, config=None,
                               start_date="2024-07-01", end_date="2025-06-28"):
    """
    Run the complete full receipt scan
    """
    scanner = FullReceiptScanner(gmail_service, mongo_client, config)
    return await scanner.run_full_scan(start_date, end_date)

if __name__ == "__main__":
    # Example usage
    async def main():
        results = await run_full_receipt_scan()
        print(f"Scan complete! Found {results['statistics']['total_receipts']} receipts")
    
    asyncio.run(main()) 
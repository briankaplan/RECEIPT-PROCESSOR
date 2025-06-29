#!/usr/bin/env python3
"""
Integrated Full Receipt Scan
Works with existing app.py system
"""

import asyncio
import logging
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegratedFullScanner:
    """
    Integrated scanner that works with your existing Flask app
    """
    
    def __init__(self, app_url: str = "http://127.0.0.1:10000"):
        self.app_url = app_url
        self.scan_results = {
            'total_emails_processed': 0,
            'receipts_found': 0,
            'successful_matches': 0,
            'failed_extractions': 0,
            'zero_amount_fixes': 0,
            'date_range': {},
            'errors': [],
            'receipts': [],
            'matches': []
        }
    
    async def run_full_scan(self, start_date: str = "2024-07-01", 
                           end_date: str = "2025-06-28") -> Dict:
        """
        Run full scan using the existing Flask app API
        """
        logger.info(f"🚀 Starting integrated full scan from {start_date} to {end_date}")
        
        # Calculate days to scan
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end - start).days
        
        logger.info(f"📅 Scanning {total_days} days of emails")
        
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
            chunk_results = await self._scan_chunk_via_api(
                current_date.strftime('%Y-%m-%d'),
                chunk_end.strftime('%Y-%m-%d')
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
        final_results = await self._process_final_results(all_receipts, all_matches)
        
        # Save results
        self._save_scan_results()
        
        logger.info("✅ Integrated full scan complete!")
        logger.info(f"📊 Final Results:")
        logger.info(f"  - Total emails processed: {self.scan_results['total_emails_processed']}")
        logger.info(f"  - Receipts found: {self.scan_results['receipts_found']}")
        logger.info(f"  - Successful matches: {self.scan_results['successful_matches']}")
        logger.info(f"  - Zero amount fixes: {self.scan_results['zero_amount_fixes']}")
        
        return final_results
    
    async def _scan_chunk_via_api(self, start_date: str, end_date: str) -> Dict:
        """
        Scan a specific date chunk using the Flask app API
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
            # Calculate days back for the search
            start = datetime.strptime(start_date, "%Y-%m-%d")
            today = datetime.now()
            days_back = (today - start).days
            
            logger.info(f"🔍 Searching for emails from {days_back} days ago via API")
            
            # Call the personalized email search API
            search_results = await self._call_personalized_search_api(days_back)
            
            if search_results and 'emails' in search_results:
                emails = search_results['emails']
                chunk_results['emails_processed'] = len(emails)
                
                logger.info(f"📧 Found {len(emails)} emails in this chunk")
                
                # Process each email
                for email in emails:
                    receipt_data = await self._process_email_receipt(email)
                    if receipt_data:
                        chunk_results['receipts'].append(receipt_data)
                        chunk_results['receipts_found'] += 1
                        
                        # Check for zero amount fixes
                        if receipt_data.get('amount', 0) > 0 and receipt_data.get('original_amount', 0) == 0:
                            chunk_results['zero_amount_fixes'] += 1
            else:
                logger.warning(f"⚠️ No search results for chunk {start_date} to {end_date}")
        
        except Exception as e:
            logger.error(f"❌ Error scanning chunk {start_date} to {end_date}: {e}")
            self.scan_results['errors'].append({
                'chunk': f"{start_date} to {end_date}",
                'error': str(e)
            })
        
        return chunk_results
    
    async def _call_personalized_search_api(self, days_back: int) -> Optional[Dict]:
        """
        Call the personalized email search API
        """
        try:
            url = f"{self.app_url}/api/personalized-email-search"
            
            payload = {
                "days_back": days_back,
                "use_enhanced_search": True,
                "fix_zero_amounts": True
            }
            
            response = requests.post(url, json=payload, timeout=300)  # 5 minute timeout
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ API call failed with status {response.status_code}: {response.text}")
                return None
        
        except Exception as e:
            logger.error(f"❌ Error calling API: {e}")
            return None
    
    async def _process_email_receipt(self, email: Dict) -> Optional[Dict]:
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
            amount = await self._extract_amount_with_fallbacks(email)
            receipt_data['amount'] = amount
            receipt_data['original_amount'] = amount
            
            # Fix zero amounts
            if amount == 0:
                fixed_amount = self._fix_zero_amount(email)
                if fixed_amount > 0:
                    receipt_data['amount'] = fixed_amount
                    receipt_data['amount_fixed'] = True
                    receipt_data['fix_method'] = 'intelligent_matching'
            
            # Extract merchant
            merchant = self._extract_merchant_with_intelligence(email)
            receipt_data['merchant'] = merchant
            
            # Only return if we have meaningful data
            if receipt_data['amount'] > 0 or receipt_data['merchant']:
                return receipt_data
            
        except Exception as e:
            logger.warning(f"⚠️ Error processing email {email.get('id', 'unknown')}: {e}")
        
        return None
    
    async def _extract_amount_with_fallbacks(self, email: Dict) -> float:
        """
        Extract amount using multiple fallback methods
        """
        import re
        
        amount = 0.0
        
        # Method 1: Extract from email body using regex
        body = email.get('body', '')
        amount_patterns = [
            r'\$\s*(\d+\.?\d*)',  # $45.67
            r'(\d+\.?\d*)\s*USD',  # 45.67 USD
            r'Total:\s*\$?\s*(\d+\.?\d*)',  # Total: $45.67
            r'Amount:\s*\$?\s*(\d+\.?\d*)',  # Amount: $45.67
            r'(\d+\.?\d*)\s*dollars',  # 45.67 dollars
            r'charged\s*\$?\s*(\d+\.?\d*)',  # charged $45.67
            r'payment\s*of\s*\$?\s*(\d+\.?\d*)',  # payment of $45.67
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
        
        return amount
    
    def _fix_zero_amount(self, email: Dict) -> float:
        """
        Fix zero amounts using intelligent matching
        """
        # This is a simplified version - in a real system, you'd match against transactions
        # For now, we'll use pattern matching to find amounts that might have been missed
        
        import re
        
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        
        # Look for common amount patterns that might have been missed
        amount_indicators = [
            r'(\d+\.?\d*)\s*for',  # 45.67 for
            r'(\d+\.?\d*)\s*paid',  # 45.67 paid
            r'(\d+\.?\d*)\s*charged',  # 45.67 charged
            r'(\d+\.?\d*)\s*processed',  # 45.67 processed
        ]
        
        for pattern in amount_indicators:
            matches = re.findall(pattern, subject + ' ' + body, re.IGNORECASE)
            if matches:
                try:
                    amount = float(matches[0])
                    if amount > 0:
                        logger.info(f"🔧 Fixed zero amount to ${amount} using pattern matching")
                        return amount
                except ValueError:
                    continue
        
        return 0.0
    
    def _extract_merchant_with_intelligence(self, email: Dict) -> str:
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
            'stripe.com': 'STRIPE',
            'microsoft.com': 'MICROSOFT',
            'google.com': 'GOOGLE',
            'amazon.com': 'AMAZON'
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
        
        return 'UNKNOWN'
    
    def _extract_domain(self, email: str) -> str:
        """Extract domain from email address"""
        if '@' in email:
            return email.split('@')[1].lower()
        return email.lower()
    
    async def _process_final_results(self, receipts: List[Dict], matches: List[Dict]) -> Dict:
        """
        Process final scan results
        """
        # Generate insights
        insights = self._generate_insights(receipts, matches)
        
        return {
            'scan_summary': self.scan_results,
            'receipts': receipts,
            'matches': matches,
            'statistics': {
                'total_transactions': 0,  # We don't have transaction data in this mode
                'total_receipts': len(receipts),
                'successful_matches': len(matches),
                'match_rate': 0.0,  # Can't calculate without transactions
                'zero_amount_fixes': self.scan_results['zero_amount_fixes']
            },
            'insights': insights
        }
    
    def _generate_insights(self, receipts: List[Dict], matches: List[Dict]) -> List[Dict]:
        """
        Generate insights from scan results
        """
        insights = []
        
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
        
        # Analyze amount patterns
        amounts = [receipt.get('amount', 0) for receipt in receipts if receipt.get('amount', 0) > 0]
        if amounts:
            avg_amount = sum(amounts) / len(amounts)
            insights.append({
                'type': 'amount_pattern',
                'message': f"Average receipt amount: ${avg_amount:.2f}",
                'suggestion': "Use this for validation of extracted amounts"
            })
        
        return insights
    
    def _save_scan_results(self):
        """
        Save scan results to file
        """
        try:
            filename = f"integrated_full_scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w') as f:
                json.dump(self.scan_results, f, indent=2, default=str)
            
            logger.info(f"💾 Saved scan results to {filename}")
            
        except Exception as e:
            logger.error(f"❌ Error saving scan results: {e}")

def check_app_running(app_url: str = "http://127.0.0.1:10000") -> bool:
    """
    Check if the Flask app is running
    """
    try:
        response = requests.get(f"{app_url}/", timeout=5)
        return response.status_code == 200
    except:
        return False

# Convenience function
async def run_integrated_full_scan(start_date="2024-07-01", end_date="2025-06-28", app_url="http://127.0.0.1:10000"):
    """
    Run the integrated full receipt scan
    """
    # Check if app is running
    if not check_app_running(app_url):
        logger.error(f"❌ Flask app is not running at {app_url}")
        logger.info("💡 Please start your app.py first: python3 app.py")
        return {'error': 'Flask app not running'}
    
    scanner = IntegratedFullScanner(app_url)
    return await scanner.run_full_scan(start_date, end_date)

if __name__ == "__main__":
    # Example usage
    async def main():
        print("🔍 Integrated Full Receipt Scanner")
        print("="*50)
        
        # Check if app is running
        if not check_app_running():
            print("❌ Flask app is not running!")
            print("💡 Please start your app.py first:")
            print("   python3 app.py")
            return
        
        print("✅ Flask app is running, starting scan...")
        
        results = await run_integrated_full_scan()
        
        if 'error' not in results:
            print(f"\n🎉 Scan complete! Found {results['statistics']['total_receipts']} receipts")
            print(f"🔧 Zero amount fixes: {results['statistics']['zero_amount_fixes']}")
        else:
            print(f"\n❌ Scan failed: {results['error']}")
    
    asyncio.run(main()) 
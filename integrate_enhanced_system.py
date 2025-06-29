#!/usr/bin/env python3
"""
Integration Script for Enhanced Receipt System
Shows how to integrate the machine learning intelligence with your existing receipt processor
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedReceiptIntegration:
    """
    Complete integration of enhanced receipt system with your existing processor
    """
    
    def __init__(self, gmail_service=None, mongo_client=None, config=None):
        self.gmail_service = gmail_service
        self.mongo_client = mongo_client
        self.config = config or {}
        
        # Import the enhanced system
        try:
            from enhanced_receipt_system import EnhancedReceiptSystem
            self.enhanced_system = EnhancedReceiptSystem(gmail_service, mongo_client, config)
            logger.info("✅ Enhanced receipt system initialized")
        except ImportError as e:
            logger.error(f"❌ Failed to import enhanced system: {e}")
            self.enhanced_system = None
        
        # Import existing components
        try:
            from personalized_email_search import PersonalizedEmailSearchSystem
            self.existing_search = PersonalizedEmailSearchSystem(gmail_service, mongo_client, config)
            logger.info("✅ Existing personalized search initialized")
        except ImportError as e:
            logger.warning(f"⚠️ Existing search not available: {e}")
            self.existing_search = None
        
        try:
            from receipt_processor import ReceiptProcessor
            self.receipt_processor = ReceiptProcessor()
            logger.info("✅ Receipt processor initialized")
        except ImportError as e:
            logger.warning(f"⚠️ Receipt processor not available: {e}")
            self.receipt_processor = None
    
    async def run_complete_enhanced_search(self, days_back: int = 7, 
                                         transactions: Optional[List[Dict]] = None) -> Dict:
        """
        Run complete enhanced search with all systems integrated
        """
        logger.info(f"🚀 Starting complete enhanced search for last {days_back} days")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'days_back': days_back,
            'emails_found': 0,
            'receipts_processed': 0,
            'matches_found': 0,
            'intelligence_insights': [],
            'performance_metrics': {},
            'errors': []
        }
        
        try:
            # Step 1: Run enhanced search with intelligence
            if self.enhanced_system:
                logger.info("🔍 Step 1: Running enhanced search with intelligence...")
                enhanced_results = await self.enhanced_system.enhanced_search(
                    days_back=days_back,
                    transactions=transactions,
                    use_existing_search=True
                )
                
                results['emails_found'] = len(enhanced_results.get('emails', []))
                results['intelligence_insights'] = enhanced_results.get('intelligence_insights', [])
                results['enhanced_results'] = enhanced_results
                
                logger.info(f"📧 Found {results['emails_found']} emails with enhanced search")
                
                # Step 2: Process receipts with existing processor
                if self.receipt_processor and enhanced_results.get('emails'):
                    logger.info("🔧 Step 2: Processing receipts with existing processor...")
                    processed_receipts = await self._process_receipts(enhanced_results['emails'])
                    results['receipts_processed'] = len(processed_receipts)
                    results['processed_receipts'] = processed_receipts
                    
                    logger.info(f"📄 Processed {results['receipts_processed']} receipts")
                
                # Step 3: Match receipts to transactions
                if transactions and enhanced_results.get('emails'):
                    logger.info("🔗 Step 3: Matching receipts to transactions...")
                    matches = self._match_receipts_to_transactions(
                        enhanced_results['emails'], transactions
                    )
                    results['matches_found'] = len(matches)
                    results['matches'] = matches
                    
                    logger.info(f"🔗 Found {results['matches_found']} matches")
                
                # Step 4: Get performance metrics
                if self.enhanced_system:
                    performance_report = self.enhanced_system.get_performance_report()
                    results['performance_metrics'] = performance_report
                    
                    logger.info("📊 Performance metrics collected")
                
            else:
                logger.warning("⚠️ Enhanced system not available, using fallback")
                results['errors'].append("Enhanced system not available")
        
        except Exception as e:
            logger.error(f"❌ Error in complete search: {str(e)}")
            results['errors'].append(str(e))
        
        logger.info("✅ Complete enhanced search finished")
        return results
    
    async def _process_receipts(self, emails: List[Dict]) -> List[Dict]:
        """
        Process receipts using existing receipt processor
        """
        processed_receipts = []
        
        for email in emails:
            try:
                # Extract receipt data from email
                receipt_data = self._extract_receipt_data(email)
                
                if receipt_data:
                    # Process with existing processor if available
                    if self.receipt_processor:
                        processed_receipt = await self.receipt_processor.process_receipt(receipt_data)
                        processed_receipts.append(processed_receipt)
                    else:
                        # Fallback processing
                        processed_receipt = self._fallback_process_receipt(receipt_data)
                        processed_receipts.append(processed_receipt)
                
            except Exception as e:
                logger.warning(f"⚠️ Error processing receipt from {email.get('subject', 'Unknown')}: {e}")
        
        return processed_receipts
    
    def _extract_receipt_data(self, email: Dict) -> Optional[Dict]:
        """
        Extract receipt data from email
        """
        try:
            # Extract basic receipt information
            receipt_data = {
                'email_id': email.get('id'),
                'subject': email.get('subject', ''),
                'from_email': email.get('from', ''),
                'date': email.get('date', ''),
                'body': email.get('body', ''),
                'has_attachments': email.get('has_attachments', False),
                'receipt_likelihood': email.get('receipt_likelihood', 0),
                'receipt_confidence': email.get('receipt_confidence', 0),
                'transaction_matches': email.get('transaction_matches', []),
                'search_suggestions': email.get('search_suggestions', [])
            }
            
            # Extract amount if present
            import re
            amount_patterns = re.findall(r'\$\d+\.?\d*', email.get('body', ''))
            if amount_patterns:
                receipt_data['amount'] = float(amount_patterns[0].replace('$', ''))
            
            # Extract merchant from subject or transaction matches
            merchant = self._extract_merchant_from_email(email)
            if merchant:
                receipt_data['merchant'] = merchant
            
            return receipt_data
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting receipt data: {e}")
            return None
    
    def _extract_merchant_from_email(self, email: Dict) -> Optional[str]:
        """
        Extract merchant name from email
        """
        # Try to get merchant from transaction matches
        transaction_matches = email.get('transaction_matches', [])
        if transaction_matches:
            return transaction_matches[0]['transaction'].get('merchant')
        
        # Try to extract from subject
        subject = email.get('subject', '').lower()
        
        # Common merchant patterns
        merchant_patterns = {
            'claude': 'CLAUDE',
            'anthropic': 'ANTHROPIC',
            'netflix': 'NETFLIX',
            'spotify': 'SPOTIFY',
            'apple': 'APPLE',
            'uber': 'UBER',
            'github': 'GITHUB',
            'square': 'SQUARE',
            'paypal': 'PAYPAL'
        }
        
        for pattern, merchant in merchant_patterns.items():
            if pattern in subject:
                return merchant
        
        return None
    
    def _fallback_process_receipt(self, receipt_data: Dict) -> Dict:
        """
        Fallback receipt processing when main processor is not available
        """
        processed_receipt = {
            'id': receipt_data.get('email_id'),
            'merchant': receipt_data.get('merchant', 'Unknown'),
            'amount': receipt_data.get('amount', 0.0),
            'date': receipt_data.get('date', ''),
            'confidence': receipt_data.get('receipt_confidence', 0.0),
            'processing_method': 'fallback',
            'extracted_data': receipt_data
        }
        
        return processed_receipt
    
    def _match_receipts_to_transactions(self, emails: List[Dict], 
                                      transactions: List[Dict]) -> List[Dict]:
        """
        Match processed receipts to transactions
        """
        matches = []
        
        for email in emails:
            transaction_matches = email.get('transaction_matches', [])
            
            for match in transaction_matches:
                if match['confidence'] > 0.5:  # Only high confidence matches
                    match_data = {
                        'email_id': email.get('id'),
                        'transaction_id': match['transaction'].get('id'),
                        'merchant': match['transaction'].get('merchant'),
                        'amount': match['transaction'].get('amount'),
                        'date': match['transaction'].get('date'),
                        'confidence': match['confidence'],
                        'reasons': match.get('reasons', [])
                    }
                    matches.append(match_data)
        
        return matches
    
    def get_integration_summary(self) -> Dict:
        """
        Get summary of integration status
        """
        return {
            'enhanced_system_available': self.enhanced_system is not None,
            'existing_search_available': self.existing_search is not None,
            'receipt_processor_available': self.receipt_processor is not None,
            'integration_status': 'full' if all([
                self.enhanced_system, self.existing_search, self.receipt_processor
            ]) else 'partial' if any([
                self.enhanced_system, self.existing_search, self.receipt_processor
            ]) else 'none'
        }
    
    def save_integration_results(self, results: Dict, filepath: str = 'integration_results.json'):
        """
        Save integration results to file
        """
        try:
            import json
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"💾 Saved integration results to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving integration results: {e}")
            return False

# Example usage functions
async def example_enhanced_search():
    """
    Example of how to use the enhanced receipt system
    """
    logger.info("📝 Example: Enhanced Receipt Search")
    
    # Sample transaction data
    sample_transactions = [
        {
            'id': 'tx_1',
            'date': '2025-06-28',
            'amount': 45.67,
            'description': 'CLAUDE AI',
            'merchant': 'CLAUDE',
            'category': 'Technology',
            'has_tip': False,
            'payment_method': 'credit_card'
        },
        {
            'id': 'tx_2',
            'date': '2025-06-27',
            'amount': 89.50,
            'description': 'SQUARE *DOWNTOWN DINER',
            'merchant': 'SQUARE *DOWNTOWN DINER',
            'category': 'Food & Dining',
            'has_tip': True,
            'payment_method': 'credit_card'
        }
    ]
    
    # Initialize integration
    integration = EnhancedReceiptIntegration()
    
    # Check integration status
    summary = integration.get_integration_summary()
    logger.info(f"🔧 Integration status: {summary['integration_status']}")
    
    # Run enhanced search
    results = await integration.run_complete_enhanced_search(
        days_back=7,
        transactions=sample_transactions
    )
    
    # Show results
    logger.info(f"📊 Search Results:")
    logger.info(f"  - Emails found: {results['emails_found']}")
    logger.info(f"  - Receipts processed: {results['receipts_processed']}")
    logger.info(f"  - Matches found: {results['matches_found']}")
    logger.info(f"  - Intelligence insights: {len(results['intelligence_insights'])}")
    
    # Save results
    integration.save_integration_results(results)
    
    return results

async def main():
    """
    Main function to demonstrate the enhanced system
    """
    logger.info("🚀 Enhanced Receipt System Integration Demo")
    
    try:
        # Run example
        results = await example_enhanced_search()
        
        logger.info("✅ Integration demo completed successfully!")
        
        # Show how to use in your existing system
        logger.info("💡 How to integrate with your existing system:")
        logger.info("""
# 1. Import the integration
from integrate_enhanced_system import EnhancedReceiptIntegration

# 2. Initialize with your existing services
integration = EnhancedReceiptIntegration(
    gmail_service=your_gmail_service,
    mongo_client=your_mongo_client,
    config=your_config
)

# 3. Run enhanced search
results = await integration.run_complete_enhanced_search(
    days_back=7,
    transactions=your_transactions
)

# 4. Use the results
for match in results['matches']:
    print(f"Matched: {match['merchant']} - ${match['amount']}")
        """)
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 
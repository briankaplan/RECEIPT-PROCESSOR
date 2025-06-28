#!/usr/bin/env python3
"""
Enhanced Receipt Processor - Match First, Upload Later
Processes email receipts, matches to transactions, then uploads to R2
"""

import os
import sys
import logging
import tempfile
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ReceiptMatch:
    """Receipt match result"""
    receipt_id: str
    transaction_id: str
    confidence: float
    match_type: str  # exact, fuzzy, amount, date
    merchant_similarity: float
    amount_match: bool
    date_match: bool
    receipt_data: Dict
    transaction_data: Dict

class EnhancedReceiptProcessor:
    """Enhanced receipt processor with match-first workflow"""
    
    def __init__(self, mongo_client, r2_client=None):
        # Handle both regular MongoClient and SafeMongoClient
        if hasattr(mongo_client, 'client'):
            # SafeMongoClient
            self.mongo_client = mongo_client.client
        else:
            # Regular MongoClient
            self.mongo_client = mongo_client
            
        self.r2_client = r2_client
        self.db = self.mongo_client['expense']
        
        # Initialize OCR processor
        try:
            from huggingface_receipt_processor import HuggingFaceReceiptProcessor
            self.ocr_processor = HuggingFaceReceiptProcessor()
            logger.info("✅ OCR processor initialized")
        except Exception as e:
            logger.warning(f"OCR processor not available: {e}")
            self.ocr_processor = None
    
    def process_email_receipts(self, email_candidates: List[Dict], gmail_account: str) -> Dict[str, any]:
        """Process email receipts with match-first workflow"""
        try:
            logger.info(f"🎯 Processing {len(email_candidates)} email receipt candidates...")
            
            results = {
                "receipts_processed": 0,
                "receipts_matched": 0,
                "receipts_uploaded": 0,
                "matches": [],
                "errors": []
            }
            
            # Get all transactions for matching
            transactions = list(self.db.bank_transactions.find({}))
            logger.info(f"📊 Found {len(transactions)} transactions for matching")
            
            for candidate in email_candidates:
                try:
                    # Step 1: Extract receipt data from email
                    receipt_data = self._extract_receipt_from_email(candidate, gmail_account)
                    if not receipt_data:
                        continue
                    
                    results["receipts_processed"] += 1
                    
                    # Step 2: Match to transactions
                    match = self._match_receipt_to_transaction(receipt_data, transactions)
                    
                    if match and match.confidence >= 0.7:  # High confidence threshold
                        results["receipts_matched"] += 1
                        results["matches"].append(match)
                        
                        # Step 3: Upload to R2 only if matched
                        if self._upload_matched_receipt(match):
                            results["receipts_uploaded"] += 1
                            
                            # Step 4: Save receipt record with transaction link
                            self._save_receipt_record(match)
                            
                            logger.info(f"✅ Matched and uploaded: {receipt_data.get('merchant', 'Unknown')} - ${receipt_data.get('amount', 0)}")
                        else:
                            logger.warning(f"⚠️ Failed to upload matched receipt: {receipt_data.get('merchant', 'Unknown')}")
                    else:
                        logger.info(f"❌ No match found for: {receipt_data.get('merchant', 'Unknown')} - ${receipt_data.get('amount', 0)}")
                
                except Exception as e:
                    error_msg = f"Error processing candidate {candidate.get('message_id', 'unknown')}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            logger.info(f"🎉 Processing complete: {results['receipts_matched']}/{results['receipts_processed']} matched")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in process_email_receipts: {e}")
            return {"error": str(e)}
    
    def _extract_receipt_from_email(self, candidate: Dict, gmail_account: str) -> Optional[Dict]:
        """Extract receipt data from email candidate"""
        try:
            # Extract basic info from email
            receipt_data = {
                "email_id": candidate.get("message_id"),
                "gmail_account": gmail_account,
                "subject": candidate.get("subject", ""),
                "from_email": candidate.get("from_email", ""),
                "date": candidate.get("date", ""),
                "confidence_score": candidate.get("confidence_score", 0.0),
                "source": "email",
                "source_type": "attachment",
                "scanned_at": datetime.utcnow().isoformat(),
                "ocr_processed": False,
                "ocr_confidence": 0.0
            }
            
            # Debug: Log the subject we're processing
            subject = candidate.get("subject", "")
            logger.info(f"🔍 Processing subject: '{subject}'")
            
            # Try to extract merchant and amount from subject/body
            merchant, amount = self._extract_basic_info(subject)
            receipt_data["merchant"] = merchant
            receipt_data["amount"] = amount
            
            # Debug: Log extraction results
            logger.info(f"📊 Extracted: Merchant='{merchant}', Amount=${amount}")
            
            # If we have attachments, process them with OCR
            if candidate.get("attachment_count", 0) > 0:
                ocr_result = self._process_attachments_with_ocr(candidate)
                if ocr_result:
                    receipt_data.update(ocr_result)
                    receipt_data["ocr_processed"] = True
            
            return receipt_data
            
        except Exception as e:
            logger.error(f"Error extracting receipt from email: {e}")
            return None
    
    def _extract_basic_info(self, subject: str) -> Tuple[str, float]:
        """Extract merchant and amount from email subject with sophisticated patterns"""
        try:
            import re
            
            # Clean subject
            subject = subject.strip()
            if not subject:
                return "Unknown", 0.0
            
            # Enhanced amount patterns for real email subjects
            amount_patterns = [
                # Standard currency patterns
                r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*USD',
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*dollars?',
                
                # Receipt-specific patterns
                r'Total:\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'Amount:\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'Charged:\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'Payment:\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'Billed:\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                
                # Action-based patterns
                r'charged\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'payment\s*of\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*paid',
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*charged',
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*billed',
                
                # Subscription patterns
                r'monthly\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*monthly',
                r'subscription\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*subscription',
                
                # Simple patterns (fallback)
                r'\$(\d+\.?\d*)',
                r'(\d+\.?\d*)\s*bucks?',
            ]
            
            amount = 0.0
            for pattern in amount_patterns:
                match = re.search(pattern, subject, re.IGNORECASE)
                if match:
                    try:
                        amount_str = match.group(1).replace(',', '')
                        amount = float(amount_str)
                        break
                    except ValueError:
                        continue
            
            # Enhanced merchant extraction
            merchant = self._extract_merchant_from_subject(subject)
            
            return merchant, amount
            
        except Exception as e:
            logger.error(f"Error extracting basic info: {e}")
            return "Unknown", 0.0
    
    def _extract_merchant_from_subject(self, subject: str) -> str:
        """Extract merchant name from email subject with sophisticated patterns"""
        try:
            import re
            
            # Clean subject for better extraction
            subject = subject.strip()
            
            # Remove common prefixes that don't help with merchant identification
            subject = re.sub(r'^(Fwd|Fwd:|Re|Re:|FW|FW:)\s*', '', subject, flags=re.IGNORECASE)
            
            # Enhanced merchant patterns for real email subjects
            merchant_patterns = [
                # Receipt patterns
                r'receipt\s+from\s+([A-Za-z0-9\s&.\-]+?)(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                r'([A-Za-z0-9\s&.\-]+?)\s+receipt(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                
                # Order patterns
                r'order\s+confirmation\s+from\s+([A-Za-z0-9\s&.\-]+?)(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                r'([A-Za-z0-9\s&.\-]+?)\s+order(?:\s+confirmation)?(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                
                # Invoice patterns
                r'invoice\s+from\s+([A-Za-z0-9\s&.\-]+?)(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                r'([A-Za-z0-9\s&.\-]+?)\s+invoice(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                
                # Payment patterns
                r'payment\s+to\s+([A-Za-z0-9\s&.\-]+?)(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                r'([A-Za-z0-9\s&.\-]+?)\s+payment(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                
                # Subscription patterns
                r'subscription\s+([A-Za-z0-9\s&.\-]+?)(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                r'([A-Za-z0-9\s&.\-]+?)\s+subscription(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                
                # Billing patterns
                r'billing\s+([A-Za-z0-9\s&.\-]+?)(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                r'([A-Za-z0-9\s&.\-]+?)\s+billing(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                
                # Charge patterns
                r'charge\s+from\s+([A-Za-z0-9\s&.\-]+?)(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                r'([A-Za-z0-9\s&.\-]+?)\s+charge(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                
                # Transaction patterns
                r'transaction\s+from\s+([A-Za-z0-9\s&.\-]+?)(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                r'([A-Za-z0-9\s&.\-]+?)\s+transaction(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                
                # Purchase patterns
                r'purchase\s+from\s+([A-Za-z0-9\s&.\-]+?)(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                r'([A-Za-z0-9\s&.\-]+?)\s+purchase(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                
                # Statement patterns
                r'statement\s+from\s+([A-Za-z0-9\s&.\-]+?)(?:\s+\$|\s+for|\s+dated|\s+order|$)',
                r'([A-Za-z0-9\s&.\-]+?)\s+statement(?:\s+\$|\s+for|\s+dated|\s+order|$)',
            ]
            
            for pattern in merchant_patterns:
                match = re.search(pattern, subject, re.IGNORECASE)
                if match:
                    merchant = match.group(1).strip()
                    # Clean up merchant name
                    merchant = self._clean_merchant_name(merchant)
                    if merchant and len(merchant) > 2:
                        return merchant
            
            # Fallback: extract first meaningful word/phrase
            merchant = self._extract_fallback_merchant(subject)
            return merchant
            
        except Exception as e:
            logger.error(f"Error extracting merchant: {e}")
            return "Unknown"
    
    def _clean_merchant_name(self, merchant: str) -> str:
        """Clean and normalize merchant name"""
        try:
            import re
            
            # Remove extra spaces
            merchant = re.sub(r'\s+', ' ', merchant)
            
            # Remove common suffixes/prefixes
            suffixes = [' inc', ' llc', ' corp', ' company', ' co', ' ltd', ' limited']
            for suffix in suffixes:
                if merchant.lower().endswith(suffix):
                    merchant = merchant[:-len(suffix)]
            
            # Remove common prefixes
            prefixes = ['receipt from ', 'order from ', 'invoice from ', 'payment to ']
            for prefix in prefixes:
                if merchant.lower().startswith(prefix):
                    merchant = merchant[len(prefix):]
            
            # Remove punctuation at ends
            merchant = merchant.strip('.,!?()[]{}":;')
            
            # Title case for better matching
            merchant = merchant.title()
            
            return merchant.strip()
            
        except Exception as e:
            logger.error(f"Error cleaning merchant name: {e}")
            return merchant
    
    def _extract_fallback_merchant(self, subject: str) -> str:
        """Extract merchant name using fallback method"""
        try:
            import re
            
            # Skip common words that aren't merchant names
            skip_words = {
                'receipt', 'order', 'invoice', 'payment', 'subscription', 'billing', 
                'confirmation', 'from', 'to', 'your', 'the', 'a', 'an', 'and', 'or', 
                'but', 'in', 'on', 'at', 'for', 'of', 'with', 'by', 'is', 'was', 'are',
                'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must',
                'new', 'latest', 'recent', 'monthly', 'weekly', 'daily', 'annual',
                'yearly', 'quarterly', 'bi', 'semi', 'auto', 'automatic', 'manual',
                'digital', 'online', 'web', 'mobile', 'app', 'application', 'service',
                'account', 'user', 'customer', 'client', 'member', 'premium', 'basic',
                'pro', 'professional', 'business', 'personal', 'corporate', 'enterprise',
                'small', 'medium', 'large', 'big', 'major', 'minor', 'important',
                'urgent', 'critical', 'essential', 'necessary', 'required', 'optional',
                'available', 'unavailable', 'active', 'inactive', 'enabled', 'disabled',
                'enabled', 'disabled', 'on', 'off', 'yes', 'no', 'true', 'false',
                'success', 'failed', 'error', 'warning', 'info', 'debug', 'test',
                'demo', 'trial', 'beta', 'alpha', 'release', 'version', 'update',
                'upgrade', 'downgrade', 'cancel', 'suspend', 'resume', 'restart',
                'refresh', 'reload', 'sync', 'backup', 'restore', 'export', 'import',
                'download', 'upload', 'install', 'uninstall', 'configure', 'setup',
                'install', 'uninstall', 'configure', 'setup', 'login', 'logout',
                'register', 'unregister', 'subscribe', 'unsubscribe', 'activate',
                'deactivate', 'enable', 'disable', 'start', 'stop', 'pause', 'resume'
            }
            
            # Split subject into words
            words = re.findall(r'\b[A-Za-z0-9&.-]+\b', subject)
            
            # Find the first meaningful word
            for word in words:
                word = word.strip('.,!?()[]{}":;')
                if (word and 
                    word.lower() not in skip_words and 
                    len(word) > 2 and
                    not word.isdigit() and
                    not re.match(r'^\d+\.\d+$', word)):  # Skip decimal numbers
                    return word.title()
            
            return "Unknown"
            
        except Exception as e:
            logger.error(f"Error in fallback merchant extraction: {e}")
            return "Unknown"
    
    def _process_attachments_with_ocr(self, candidate: Dict) -> Optional[Dict]:
        """Process attachments with OCR to extract receipt data"""
        try:
            if not self.ocr_processor:
                return None
            
            # This would download and process attachments
            # For now, return basic extracted data
            return {
                "merchant": candidate.get("subject", "").split()[0],
                "amount": 0.0,
                "ocr_confidence": 0.5
            }
            
        except Exception as e:
            logger.error(f"Error processing attachments with OCR: {e}")
            return None
    
    def _match_receipt_to_transaction(self, receipt_data: Dict, transactions: List[Dict]) -> Optional[ReceiptMatch]:
        """Match receipt to transaction using multiple strategies"""
        try:
            best_match = None
            best_confidence = 0.0
            
            receipt_merchant = receipt_data.get("merchant", "").lower()
            receipt_amount = receipt_data.get("amount", 0.0)
            receipt_date = receipt_data.get("date", "")
            
            for transaction in transactions:
                confidence = 0.0
                match_type = "none"
                
                # Get transaction data
                txn_merchant = (transaction.get("merchant") or transaction.get("description", "")).lower()
                txn_amount = abs(float(transaction.get("amount", 0)))
                txn_date = transaction.get("date", "")
                
                # Strategy 1: Exact merchant + amount match
                if (receipt_merchant in txn_merchant or txn_merchant in receipt_merchant) and abs(receipt_amount - txn_amount) < 0.01:
                    confidence = 0.95
                    match_type = "exact"
                
                # Strategy 2: Merchant similarity + amount match
                elif self._calculate_merchant_similarity(receipt_merchant, txn_merchant) > 0.8 and abs(receipt_amount - txn_amount) < 0.01:
                    confidence = 0.85
                    match_type = "fuzzy"
                
                # Strategy 3: Amount match + date proximity
                elif abs(receipt_amount - txn_amount) < 0.01 and self._dates_close(receipt_date, txn_date):
                    confidence = 0.75
                    match_type = "amount_date"
                
                # Strategy 4: High merchant similarity
                elif self._calculate_merchant_similarity(receipt_merchant, txn_merchant) > 0.9:
                    confidence = 0.70
                    match_type = "merchant"
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = ReceiptMatch(
                        receipt_id=receipt_data.get("email_id", ""),
                        transaction_id=str(transaction.get("_id")),
                        confidence=confidence,
                        match_type=match_type,
                        merchant_similarity=self._calculate_merchant_similarity(receipt_merchant, txn_merchant),
                        amount_match=abs(receipt_amount - txn_amount) < 0.01,
                        date_match=self._dates_close(receipt_date, txn_date),
                        receipt_data=receipt_data,
                        transaction_data=transaction
                    )
            
            return best_match
            
        except Exception as e:
            logger.error(f"Error matching receipt to transaction: {e}")
            return None
    
    def _calculate_merchant_similarity(self, merchant1: str, merchant2: str) -> float:
        """Calculate similarity between merchant names"""
        try:
            if not merchant1 or not merchant2:
                return 0.0
            
            # Simple similarity calculation
            words1 = set(merchant1.split())
            words2 = set(merchant2.split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union)
            
        except Exception as e:
            logger.error(f"Error calculating merchant similarity: {e}")
            return 0.0
    
    def _dates_close(self, date1: str, date2: str, days_threshold: int = 7) -> bool:
        """Check if two dates are within the threshold"""
        try:
            import re
            from datetime import datetime, timedelta
            
            # Parse date1 (receipt date)
            date1_parsed = self._parse_date(date1)
            if not date1_parsed:
                return False
            
            # Parse date2 (transaction date)
            date2_parsed = self._parse_date(date2)
            if not date2_parsed:
                return False
            
            # Calculate difference
            diff = abs((date1_parsed - date2_parsed).days)
            return diff <= days_threshold
            
        except Exception as e:
            logger.error(f"Error checking date proximity: {e}")
            return False
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats"""
        try:
            import re
            from datetime import datetime
            from email.utils import parsedate_to_datetime
            
            if not date_str:
                return None
            
            # Try RFC format first (common in email headers)
            try:
                return parsedate_to_datetime(date_str)
            except:
                pass
            
            # Try ISO format
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                pass
            
            # Try common formats
            formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y/%m/%d',
                '%B %d, %Y',
                '%b %d, %Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue
            
            # Try to extract date from string
            date_patterns = [
                r'(\d{4})-(\d{1,2})-(\d{1,2})',
                r'(\d{1,2})/(\d{1,2})/(\d{4})',
                r'(\d{1,2})-(\d{1,2})-(\d{4})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    try:
                        if len(match.group(1)) == 4:  # YYYY-MM-DD
                            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                        else:  # MM/DD/YYYY or DD/MM/YYYY
                            return datetime(int(match.group(3)), int(match.group(1)), int(match.group(2)))
                    except:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
            return None
    
    def _upload_matched_receipt(self, match: ReceiptMatch) -> bool:
        """Upload matched receipt to R2 storage"""
        try:
            if not self.r2_client:
                logger.warning("R2 client not available")
                return False
            
            # Create R2 key
            receipt_data = match.receipt_data
            account_safe = receipt_data.get("gmail_account", "").replace('@', '_at_').replace('.', '_')
            date_str = datetime.utcnow().strftime('%Y/%m/%d')
            key = f"receipts/{account_safe}/{date_str}/{receipt_data.get('email_id', 'unknown')}.pdf"
            
            # For now, create a placeholder file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(b"Receipt placeholder")
                temp_file_path = temp_file.name
            
            # Upload to R2
            success = self.r2_client.upload_file(temp_file_path, key, {
                'transaction_id': match.transaction_id,
                'confidence': str(match.confidence),
                'match_type': match.match_type
            })
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            if success:
                receipt_data["r2_key"] = key
                receipt_data["r2_url"] = self.r2_client.get_file_url(key)
            
            return success
            
        except Exception as e:
            logger.error(f"Error uploading matched receipt: {e}")
            return False
    
    def _save_receipt_record(self, match: ReceiptMatch):
        """Save receipt record to database with transaction link"""
        try:
            receipt_data = match.receipt_data.copy()
            receipt_data["transaction_id"] = match.transaction_id
            receipt_data["match_confidence"] = match.confidence
            receipt_data["match_type"] = match.match_type
            receipt_data["matched_at"] = datetime.utcnow().isoformat()
            
            # Insert receipt record
            result = self.db.receipts.insert_one(receipt_data)
            
            # Update transaction with receipt link
            self.db.bank_transactions.update_one(
                {"_id": match.transaction_data["_id"]},
                {"$set": {"receipt_url": receipt_data.get("r2_url", "")}}
            )
            
            logger.info(f"✅ Saved receipt record: {result.inserted_id}")
            
        except Exception as e:
            logger.error(f"Error saving receipt record: {e}")

def main():
    """Test the enhanced receipt processor"""
    try:
        # Initialize clients
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri:
            logger.error("❌ No MongoDB URI configured")
            return
        
        mongo_client = MongoClient(mongo_uri)
        
        # Initialize R2 client
        try:
            from r2_client import R2Client
            r2_client = R2Client()
        except Exception as e:
            logger.warning(f"R2 client not available: {e}")
            r2_client = None
        
        # Initialize processor
        processor = EnhancedReceiptProcessor(mongo_client, r2_client)
        
        # Test with sample data
        sample_candidates = [
            {
                "message_id": "test_1",
                "subject": "Receipt from EXPENSIFY - $99.00",
                "from_email": "receipts@expensify.com",
                "date": "2025-06-28T10:00:00Z",
                "confidence_score": 0.9,
                "attachment_count": 1
            }
        ]
        
        results = processor.process_email_receipts(sample_candidates, "test@example.com")
        logger.info(f"Test results: {results}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()

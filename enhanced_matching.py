#!/usr/bin/env python3
"""
Enhanced Receipt-to-Transaction Matching
Uses fuzzy logic and real receipt data from OCR
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import re

logger = logging.getLogger(__name__)

class EnhancedReceiptMatcher:
    """Enhanced matching using fuzzy logic and OCR data"""
    
    def __init__(self):
        self.merchant_aliases = {
            'walmart': ['wal-mart', 'walmart supercenter', 'walmart neighborhood market'],
            'target': ['target corporation', 'target store'],
            'amazon': ['amazon.com', 'amazon marketplace'],
            'apple': ['apple store', 'apple.com', 'itunes'],
            'starbucks': ['starbucks coffee', 'starbucks corporation'],
            'uber': ['uber technologies', 'uber ride'],
            'netflix': ['netflix streaming'],
            'spotify': ['spotify usa'],
            'chase': ['jpmorgan chase', 'chase bank'],
            'bank of america': ['bofa', 'bank of america corp'],
            'wells fargo': ['wells fargo bank'],
        }
        
        self.date_tolerance_days = 3
        self.amount_tolerance_percent = 0.05  # 5%
        self.min_merchant_similarity = 0.6
        self.min_overall_score = 0.4

    def normalize_merchant_name(self, merchant: str) -> str:
        """Normalize merchant name for comparison"""
        if not merchant:
            return ""
        
        # Convert to lowercase and remove common words
        normalized = merchant.lower().strip()
        
        # Remove common business suffixes
        suffixes = [' inc', ' llc', ' corp', ' co', ' ltd', ' company']
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        
        # Remove punctuation and extra spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized

    def calculate_merchant_similarity(self, receipt_merchant: str, transaction_merchant: str) -> float:
        """Calculate similarity between merchant names"""
        if not receipt_merchant or not transaction_merchant:
            return 0.0
        
        receipt_norm = self.normalize_merchant_name(receipt_merchant)
        transaction_norm = self.normalize_merchant_name(transaction_merchant)
        
        # Check for exact match
        if receipt_norm == transaction_norm:
            return 1.0
        
        # Check for substring match
        if receipt_norm in transaction_norm or transaction_norm in receipt_norm:
            return 0.9
        
        # Check merchant aliases
        for alias_group in self.merchant_aliases.values():
            if receipt_norm in alias_group and transaction_norm in alias_group:
                return 0.8
        
        # Use fuzzy string matching
        similarity = SequenceMatcher(None, receipt_norm, transaction_norm).ratio()
        
        return similarity

    def calculate_amount_similarity(self, receipt_amount: float, transaction_amount: float) -> float:
        """Calculate similarity between amounts"""
        if not receipt_amount or not transaction_amount:
            return 0.0
        
        # Use absolute values for comparison
        receipt_abs = abs(receipt_amount)
        transaction_abs = abs(transaction_amount)
        
        # Check for exact match
        if receipt_abs == transaction_abs:
            return 1.0
        
        # Calculate percentage difference
        if transaction_abs > 0:
            diff_percent = abs(receipt_abs - transaction_abs) / transaction_abs
            
            if diff_percent <= self.amount_tolerance_percent:
                return 1.0 - (diff_percent / self.amount_tolerance_percent)
            elif diff_percent <= 0.1:  # 10% tolerance
                return 0.5
            else:
                return 0.0
        
        return 0.0

    def calculate_date_similarity(self, receipt_date: datetime, transaction_date: datetime) -> float:
        """Calculate similarity between dates"""
        if not receipt_date or not transaction_date:
            return 0.0
        
        # Calculate date difference
        date_diff = abs((receipt_date - transaction_date).days)
        
        if date_diff == 0:
            return 1.0
        elif date_diff <= self.date_tolerance_days:
            return 1.0 - (date_diff / self.date_tolerance_days)
        elif date_diff <= 7:  # Within a week
            return 0.3
        else:
            return 0.0

    def parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        
        try:
            # Try different date formats
            formats = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S%z',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y/%m/%d',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # If all formats fail, try parsing with dateutil
            from dateutil import parser
            return parser.parse(date_str)
            
        except Exception as e:
            logger.warning(f"Failed to parse date: {date_str}, error: {e}")
            return None

    def calculate_match_score(self, receipt: Dict, transaction: Dict) -> float:
        """Calculate overall match score between receipt and transaction"""
        score = 0.0
        weights = {
            'merchant': 0.4,
            'amount': 0.4,
            'date': 0.2
        }
        
        # Extract receipt data (prefer OCR data over email data)
        receipt_merchant = (receipt.get('receipt_merchant') or 
                          receipt.get('merchant') or "")
        receipt_amount = (receipt.get('receipt_amount') or 
                        receipt.get('amount') or 0.0)
        receipt_date_str = (receipt.get('receipt_date') or 
                          receipt.get('date'))
        
        # Extract transaction data
        transaction_merchant = (transaction.get('merchant_name') or 
                              transaction.get('merchant') or "")
        transaction_amount = abs(float(transaction.get('amount', 0)))
        transaction_date_str = transaction.get('date')
        
        # Parse dates
        receipt_date = self.parse_date_string(receipt_date_str)
        transaction_date = self.parse_date_string(transaction_date_str)
        
        # Calculate individual scores
        merchant_score = self.calculate_merchant_similarity(receipt_merchant, transaction_merchant)
        amount_score = self.calculate_amount_similarity(receipt_amount, transaction_amount)
        date_score = self.calculate_date_similarity(receipt_date, transaction_date)
        
        # Calculate weighted score
        score = (merchant_score * weights['merchant'] +
                amount_score * weights['amount'] +
                date_score * weights['date'])
        
        # Log detailed scoring for debugging
        logger.debug(f"Match scoring for receipt {receipt.get('_id')} vs transaction {transaction.get('_id')}:")
        logger.debug(f"  Merchant: {receipt_merchant} vs {transaction_merchant} = {merchant_score:.3f}")
        logger.debug(f"  Amount: {receipt_amount} vs {transaction_amount} = {amount_score:.3f}")
        logger.debug(f"  Date: {receipt_date} vs {transaction_date} = {date_score:.3f}")
        logger.debug(f"  Overall score: {score:.3f}")
        
        return score

    def find_best_match(self, receipt: Dict, transactions: List[Dict]) -> Tuple[Optional[Dict], float]:
        """Find the best matching transaction for a receipt"""
        best_match = None
        best_score = 0.0
        
        for transaction in transactions:
            score = self.calculate_match_score(receipt, transaction)
            
            if score > best_score and score >= self.min_overall_score:
                best_score = score
                best_match = transaction
        
        return best_match, best_score

    def batch_match_receipts(self, receipts: List[Dict], transactions: List[Dict]) -> List[Dict]:
        """Match multiple receipts to transactions"""
        matches = []
        
        # Filter out already matched transactions
        unmatched_transactions = [t for t in transactions if not t.get('matched_receipt_id')]
        
        for receipt in receipts:
            # Skip already matched receipts
            if receipt.get('matched_transaction_id'):
                continue
            
            best_match, score = self.find_best_match(receipt, unmatched_transactions)
            
            if best_match and score >= self.min_overall_score:
                # Convert ObjectIds to strings for JSON serialization
                receipt_id = str(receipt.get('_id')) if receipt.get('_id') else None
                transaction_id = str(best_match.get('_id')) if best_match.get('_id') else None
                
                match_data = {
                    'receipt_id': receipt_id,
                    'transaction_id': transaction_id,
                    'score': score,
                    'receipt_merchant': receipt.get('receipt_merchant') or receipt.get('merchant'),
                    'transaction_merchant': best_match.get('merchant_name') or best_match.get('merchant'),
                    'receipt_amount': receipt.get('receipt_amount') or receipt.get('amount'),
                    'transaction_amount': best_match.get('amount'),
                    'receipt_date': receipt.get('receipt_date') or receipt.get('date'),
                    'transaction_date': best_match.get('date'),
                    'match_confidence': 'high' if score >= 0.8 else 'medium' if score >= 0.6 else 'low'
                }
                
                matches.append(match_data)
                
                # Mark transaction as matched
                best_match['matched_receipt_id'] = receipt_id
                
                logger.info(f"✅ Matched receipt {receipt_id} to transaction {transaction_id} "
                           f"with score {score:.3f}")
        
        return matches 
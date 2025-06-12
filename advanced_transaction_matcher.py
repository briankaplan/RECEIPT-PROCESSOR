#!/usr/bin/env python3
"""
Advanced Transaction Matcher - AI-powered receipt-to-transaction matching
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, NamedTuple, Tuple
from dataclasses import dataclass
from fuzzywuzzy import fuzz
from sentence_transformers import SentenceTransformer, util
import numpy as np
from match_result import MatchResult

class MatchResult(NamedTuple):
    receipt_id: str
    transaction_id: str
    confidence: float
    match_type: str
    reasoning: str
    score_breakdown: Dict[str, float]

@dataclass
class MatchCandidate:
    receipt: Dict
    transaction: Dict
    scores: Dict[str, float]
    total_score: float
    reasoning: List[str]

class AdvancedTransactionMatcher:
    """
    Advanced transaction matching using multiple AI techniques:
    - Fuzzy string matching
    - Semantic similarity 
    - Date proximity analysis
    - Amount validation with tolerance
    - Merchant name normalization
    - Context-aware scoring
    """
    
    def __init__(self):
        # Load semantic model for text similarity
        try:
            self.semantic_model = SentenceTransformer("all-MiniLM-L6-v2")
            self.use_semantic = True
            logging.info("✅ Semantic model loaded for advanced matching")
        except Exception as e:
            logging.warning(f"⚠️ Semantic model failed to load: {e}")
            self.use_semantic = False
        
        # Matching configuration
        self.config = {
            'date_tolerance_days': 7,
            'amount_tolerance_percent': 0.05,  # 5% tolerance
            'amount_tolerance_absolute': 2.0,   # $2 absolute tolerance
            'min_confidence_threshold': 0.65,
            'fuzzy_weight': 0.3,
            'semantic_weight': 0.4,
            'date_weight': 0.15,
            'amount_weight': 0.15
        }
        
        # Merchant normalization patterns
        self.merchant_normalizers = self._load_merchant_normalizers()
        
        # Match statistics
        self.match_stats = {
            'total_attempts': 0,
            'successful_matches': 0,
            'high_confidence_matches': 0,
            'manual_review_needed': 0
        }
    
    def _load_merchant_normalizers(self) -> List[Tuple[str, str]]:
        """Load merchant name normalization patterns"""
        
        return [
            # Remove common prefixes/suffixes
            (r'^(TST\*|SQ \*|PP \*|SP )', ''),
            (r'\s+(LLC|INC|CORP|CO|LTD)\.?$', ''),
            (r'\s+#\d+$', ''),  # Remove store numbers
            (r'\s+-\s+.*$', ''),  # Remove location suffixes
            
            # Standardize common merchants
            (r'STARBUCKS.*', 'STARBUCKS'),
            (r'MCDONALD.*', 'MCDONALDS'),
            (r'WAL-?MART.*', 'WALMART'),
            (r'AMAZON.*', 'AMAZON'),
            (r'GOOGLE.*GSUITE.*', 'GOOGLE WORKSPACE'),
            (r'BEST\s*BUY.*', 'BEST BUY'),
            
            # Your specific merchants
            (r'.*CLAUDE.*', 'CLAUDE.AI'),
            (r'.*MIDJOURNEY.*', 'MIDJOURNEY'),
            (r'.*EXPENSIFY.*', 'EXPENSIFY'),
            (r'.*CAMBRIA.*HOTEL.*', 'CAMBRIA HOTEL'),
            (r'.*HIVE.*', 'HIVE CO'),
        ]
    
    def match_receipts_to_transactions(self, 
                                     receipts: List[Dict], 
                                     transactions: List[Dict],
                                     use_ai_enhancement: bool = True) -> List[Dict]:
        """
        Main matching function with AI enhancement
        """
        
        self.match_stats['total_attempts'] = len(receipts) * len(transactions)
        matches = []
        
        logging.info(f"🎯 Starting advanced matching: {len(receipts)} receipts × {len(transactions)} transactions")
        
        # Pre-process data
        normalized_receipts = [self._normalize_receipt(r) for r in receipts]
        normalized_transactions = [self._normalize_transaction(t) for t in transactions]
        
        # Build semantic embeddings if available
        if self.use_semantic and use_ai_enhancement:
            receipt_embeddings = self._build_embeddings([r['search_text'] for r in normalized_receipts])
            transaction_embeddings = self._build_embeddings([t['search_text'] for t in normalized_transactions])
        else:
            receipt_embeddings = None
            transaction_embeddings = None
        
        # Match each receipt
        used_transactions = set()
        
        for i, receipt in enumerate(normalized_receipts):
            best_match = None
            best_confidence = 0
            
            candidates = []
            
            for j, transaction in enumerate(normalized_transactions):
                if transaction['id'] in used_transactions:
                    continue
                
                # Calculate match scores
                match_candidate = self._calculate_match_scores(
                    receipt, transaction, 
                    receipt_embeddings[i] if receipt_embeddings is not None else None,
                    transaction_embeddings[j] if transaction_embeddings is not None else None
                )
                
                if match_candidate.total_score >= self.config['min_confidence_threshold']:
                    candidates.append(match_candidate)
            
            # Select best candidate
            if candidates:
                best_candidate = max(candidates, key=lambda c: c.total_score)
                
                match_result = MatchResult(
                    receipt_id=best_candidate.receipt['id'],
                    transaction_id=best_candidate.transaction['id'],
                    confidence=best_candidate.total_score,
                    reasoning='; '.join(best_candidate.reasoning),
                    match_type=self._determine_match_type(best_candidate.total_score),
                    receipt=best_candidate.receipt,
                    transaction=best_candidate.transaction
                ).to_dict()
                
                matches.append(match_result)
                used_transactions.add(best_candidate.transaction['id'])
                
                self.match_stats['successful_matches'] += 1
                if best_candidate.total_score >= 0.8:
                    self.match_stats['high_confidence_matches'] += 1
                elif best_candidate.total_score < 0.75:
                    self.match_stats['manual_review_needed'] += 1
                
                logging.info(f"✅ Match: {receipt['merchant']} → {best_candidate.transaction['merchant']} (confidence: {best_candidate.total_score:.2f})")
        
        logging.info(f"📊 Matching complete: {len(matches)} matches found")
        self._log_match_statistics()
        
        return matches
    
    def _normalize_receipt(self, receipt: Dict) -> Dict:
        """Normalize receipt data for matching"""
        
        merchant = self._normalize_merchant_name(receipt.get('merchant', ''))
        amount = self._parse_amount(receipt.get('amount', 0))
        date = self._parse_date(receipt.get('date', ''))
        
        return {
            'id': receipt['id'],
            'merchant': merchant,
            'amount': amount,
            'date': date,
            'confidence': receipt.get('confidence', 1.0),
            'full_text': receipt.get('full_text', ''),
            'search_text': f"{merchant} {amount} {receipt.get('full_text', '')[:200]}"
        }
    
    def _normalize_transaction(self, transaction: Dict) -> Dict:
        """Normalize transaction data for matching"""
        
        # Handle different possible column names
        merchant = transaction.get('Description', transaction.get('merchant', transaction.get('description', '')))
        amount = transaction.get('Amount', transaction.get('amount', 0))
        date = transaction.get('Transaction Date', transaction.get('date', transaction.get('Date', '')))
        
        merchant = self._normalize_merchant_name(merchant)
        amount = abs(self._parse_amount(amount))  # Use absolute value for debits
        date = self._parse_date(date)
        
        return {
            'id': transaction['id'],
            'merchant': merchant,
            'amount': amount,
            'date': date,
            'search_text': f"{merchant} {amount}"
        }
    
    def _normalize_merchant_name(self, merchant: str) -> str:
        """Normalize merchant names for better matching"""
        
        if not merchant:
            return ""
        
        # Convert to uppercase for consistency
        normalized = merchant.upper().strip()
        
        # Apply normalization patterns
        for pattern, replacement in self.merchant_normalizers:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _calculate_match_scores(self, receipt: Dict, transaction: Dict, 
                               receipt_embedding=None, transaction_embedding=None) -> MatchCandidate:
        """Calculate comprehensive match scores"""
        
        scores = {}
        reasoning = []
        
        # 1. Fuzzy string matching
        fuzzy_score = fuzz.token_set_ratio(receipt['merchant'], transaction['merchant']) / 100.0
        scores['fuzzy'] = fuzzy_score
        if fuzzy_score > 0.8:
            reasoning.append(f"High fuzzy match ({fuzzy_score:.2f})")
        
        # 2. Semantic similarity (if available)
        if self.use_semantic and receipt_embedding is not None and transaction_embedding is not None:
            semantic_score = float(util.pytorch_cos_sim(receipt_embedding, transaction_embedding)[0])
            scores['semantic'] = semantic_score
            if semantic_score > 0.7:
                reasoning.append(f"High semantic similarity ({semantic_score:.2f})")
        else:
            scores['semantic'] = fuzzy_score  # Fallback to fuzzy
        
        # 3. Date proximity
        date_score = self._calculate_date_score(receipt['date'], transaction['date'])
        scores['date'] = date_score
        if date_score > 0.8:
            reasoning.append(f"Close date match ({date_score:.2f})")
        
        # 4. Amount matching
        amount_score = self._calculate_amount_score(receipt['amount'], transaction['amount'])
        scores['amount'] = amount_score
        if amount_score > 0.9:
            reasoning.append(f"Exact amount match")
        elif amount_score > 0.7:
            reasoning.append(f"Close amount match ({amount_score:.2f})")
        
        # 5. Calculate weighted total score
        total_score = (
            scores['fuzzy'] * self.config['fuzzy_weight'] +
            scores['semantic'] * self.config['semantic_weight'] +
            scores['date'] * self.config['date_weight'] +
            scores['amount'] * self.config['amount_weight']
        )
        
        # 6. Apply confidence boost from receipt processing
        confidence_boost = receipt['confidence'] * 0.1
        total_score = min(total_score + confidence_boost, 1.0)
        
        if not reasoning:
            reasoning.append("Low confidence match")
        
        return MatchCandidate(
            receipt=receipt,
            transaction=transaction,
            scores=scores,
            total_score=total_score,
            reasoning=reasoning
        )
    
    def _calculate_date_score(self, receipt_date: str, transaction_date: str) -> float:
        """Calculate date proximity score"""
        
        try:
            r_date = datetime.strptime(receipt_date, '%Y-%m-%d')
            t_date = datetime.strptime(transaction_date, '%Y-%m-%d')
            
            days_diff = abs((r_date - t_date).days)
            
            if days_diff == 0:
                return 1.0
            elif days_diff <= 1:
                return 0.9
            elif days_diff <= 3:
                return 0.8
            elif days_diff <= self.config['date_tolerance_days']:
                return 0.7 - (days_diff / self.config['date_tolerance_days']) * 0.3
            else:
                return 0.0
        
        except (ValueError, TypeError):
            return 0.5  # Unknown dates get neutral score
    
    def _calculate_amount_score(self, receipt_amount: float, transaction_amount: float) -> float:
        """Calculate amount matching score with tolerance"""
        
        if receipt_amount <= 0 or transaction_amount <= 0:
            return 0.3  # Low score for missing amounts
        
        diff = abs(receipt_amount - transaction_amount)
        
        # Exact match
        if diff == 0:
            return 1.0
        
        # Within absolute tolerance
        if diff <= self.config['amount_tolerance_absolute']:
            return 0.95 - (diff / self.config['amount_tolerance_absolute']) * 0.2
        
        # Within percentage tolerance
        percent_diff = diff / max(receipt_amount, transaction_amount)
        if percent_diff <= self.config['amount_tolerance_percent']:
            return 0.9 - (percent_diff / self.config['amount_tolerance_percent']) * 0.3
        
        # Larger differences get lower scores
        if percent_diff <= 0.1:  # 10%
            return 0.6 - percent_diff * 2
        elif percent_diff <= 0.2:  # 20%
            return 0.4 - percent_diff
        else:
            return 0.0
    
    def _build_embeddings(self, texts: List[str]):
        """Build semantic embeddings for text similarity"""
        
        if not self.use_semantic:
            return None
        
        try:
            return self.semantic_model.encode(texts, convert_to_tensor=True)
        except Exception as e:
            logging.warning(f"⚠️ Embedding generation failed: {e}")
            return None
    
    def _determine_match_type(self, confidence: float) -> str:
        """Determine match type based on confidence"""
        
        if confidence >= 0.9:
            return "HIGH_CONFIDENCE"
        elif confidence >= 0.8:
            return "GOOD_MATCH"
        elif confidence >= 0.7:
            return "POSSIBLE_MATCH"
        else:
            return "LOW_CONFIDENCE"
    
    def _parse_amount(self, amount) -> float:
        """Parse amount to float"""
        
        if isinstance(amount, (int, float)):
            return float(amount)
        
        if isinstance(amount, str):
            # Clean the string
            amount = re.sub(r'[^\d.-]', '', amount)
            try:
                return float(amount)
            except ValueError:
                return 0.0
        
        return 0.0
    
    def _parse_date(self, date_str) -> str:
        """Parse date to YYYY-MM-DD format"""
        
        if not date_str:
            return ""
        
        # If already in correct format
        if re.match(r'\d{4}-\d{2}-\d{2}', str(date_str)):
            return str(date_str)
        
        # Try common formats
        date_formats = [
            '%m/%d/%Y', '%m-%d-%Y',
            '%m/%d/%y', '%m-%d-%y',
            '%Y-%m-%d', '%Y/%m/%d'
        ]
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(str(date_str), fmt)
                if date_obj.year < 1950:
                    date_obj = date_obj.replace(year=date_obj.year + 100)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return ""
    
    def _log_match_statistics(self):
        """Log matching statistics"""
        
        total = self.match_stats['total_attempts']
        successful = self.match_stats['successful_matches']
        high_conf = self.match_stats['high_confidence_matches']
        manual = self.match_stats['manual_review_needed']
        
        logging.info(f"📊 Match Statistics:")
        logging.info(f"  Total attempts: {total}")
        logging.info(f"  Successful matches: {successful}")
        logging.info(f"  High confidence: {high_conf}")
        logging.info(f"  Manual review needed: {manual}")
        if successful > 0:
            logging.info(f"  Match rate: {(successful/len(self.match_stats.get('receipts', [1]))):.1%}")
    
    def get_match_statistics(self) -> Dict:
        """Get detailed matching statistics"""
        return self.match_stats.copy()

# Test the advanced matcher
if __name__ == "__main__":
    matcher = AdvancedTransactionMatcher()
    
    # Sample data
    receipts = [
        {
            'id': 'receipt_1',
            'merchant': 'STARBUCKS',
            'amount': 8.83,
            'date': '2025-06-10',
            'confidence': 0.9,
            'full_text': 'STARBUCKS STORE GRANDE COFFEE $8.83'
        }
    ]
    
    transactions = [
        {
            'id': 'txn_1',
            'Description': 'STARBUCKS STORE #123',
            'Amount': -8.83,
            'Transaction Date': '2025-06-10'
        }
    ]
    
    matches = matcher.match_receipts_to_transactions(receipts, transactions)
    
    print("🎯 Advanced Transaction Matcher Test:")
    for match in matches:
        print(f"  Receipt: {match['receipt_id']}")
        print(f"  Transaction: {match['transaction_id']}")
        print(f"  Confidence: {match['confidence']:.2f}")
        print(f"  Type: {match['match_type']}")
        print(f"  Reasoning: {match['reasoning']}")
        print(f"  Scores: {match['score_breakdown']}")
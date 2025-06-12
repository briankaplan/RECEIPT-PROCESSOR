#!/usr/bin/env python3
"""
Merchant Intelligence Module
Handles merchant name matching and pattern learning
"""

import logging
from typing import Dict, List, Tuple, Optional
from fuzzywuzzy import fuzz
import re

class MerchantIntelligenceSystem:
    def __init__(self, config: Optional[Dict] = None):
        """Initialize merchant intelligence system"""
        self.config = config or {}
        self.merchant_variations = self._build_comprehensive_merchant_db()
        logging.info("Merchant intelligence system initialized")
    
    def _build_comprehensive_merchant_db(self) -> Dict[str, List[str]]:
        """Build comprehensive merchant variations database"""
        return {
            # Food & Beverage
            'starbucks': ['sbux', 'starbucks coffee', 'starbucks store'],
            'mcdonalds': ['mcd', 'mcds', 'mcdonalds restaurant'],
            'chipotle': ['chipotle mexican grill'],
            'panera': ['panera bread'],
            'subway': ['subway sandwich'],
            'dunkin': ['dunkin donuts', 'dd'],
            
            # Retail
            'target': ['tgt', 'target store'],
            'walmart': ['wmt', 'wal-mart'],
            'amazon': ['amzn', 'amazon.com'],
            'costco': ['costco wholesale'],
            'whole foods': ['whole foods market', 'wf'],
            'trader joes': ['trader joe', 'tj'],
            
            # Tech
            'apple': ['apple store', 'apple.com'],
            'google': ['google store', 'google.com'],
            'microsoft': ['microsoft store', 'msft'],
            
            # Transportation
            'uber': ['uber rides', 'uber.com'],
            'lyft': ['lyft rides', 'lyft.com'],
            'delta': ['delta airlines', 'delta.com'],
            'united': ['united airlines', 'united.com'],
            
            # Entertainment
            'netflix': ['netflix.com'],
            'spotify': ['spotify.com'],
            'hulu': ['hulu.com'],
            'disney': ['disney+', 'disney plus'],
            
            # Grocery
            'safeway': ['safeway store'],
            'kroger': ['kroger store'],
            'albertsons': ['albertsons store'],
            'publix': ['publix store'],
            'wegmans': ['wegmans store']
        }
    
    def calculate_similarity(self, merchant1: str, merchant2: str) -> float:
        """Calculate similarity between two merchant names"""
        try:
            # Normalize merchant names
            merchant1 = self._normalize_merchant_name(merchant1)
            merchant2 = self._normalize_merchant_name(merchant2)
            
            # Get variations
            variations1 = self._get_merchant_variations(merchant1)
            variations2 = self._get_merchant_variations(merchant2)
            
            # Calculate scores using different methods
            scores = []
            
            # Direct comparison
            scores.append(fuzz.ratio(merchant1.lower(), merchant2.lower()) / 100.0)
            scores.append(fuzz.token_sort_ratio(merchant1.lower(), merchant2.lower()) / 100.0)
            scores.append(fuzz.token_set_ratio(merchant1.lower(), merchant2.lower()) / 100.0)
            
            # Compare variations
            for v1 in variations1:
                for v2 in variations2:
                    scores.append(fuzz.ratio(v1.lower(), v2.lower()) / 100.0)
                    scores.append(fuzz.token_sort_ratio(v1.lower(), v2.lower()) / 100.0)
                    scores.append(fuzz.token_set_ratio(v1.lower(), v2.lower()) / 100.0)
            
            # Return highest score
            return max(scores) if scores else 0.0
            
        except Exception as e:
            logging.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def _normalize_merchant_name(self, merchant: str) -> str:
        """Normalize merchant name for better matching"""
        if not merchant:
            return ""
        
        # Convert to lowercase
        merchant = merchant.lower()
        
        # Remove common suffixes
        merchant = re.sub(r'\s+(inc\.?|llc|ltd\.?|corp\.?|company|co\.?)$', '', merchant)
        
        # Remove common prefixes
        merchant = re.sub(r'^(the\s+)', '', merchant)
        
        # Remove special characters and extra spaces
        merchant = re.sub(r'[^\w\s]', ' ', merchant)
        merchant = re.sub(r'\s+', ' ', merchant).strip()
        
        # Remove common words that don't help matching
        common_words = ['store', 'location', 'branch', 'shop']
        merchant = ' '.join(word for word in merchant.split() if word not in common_words)
        
        return merchant
    
    def _get_merchant_variations(self, merchant: str) -> List[str]:
        """Get variations of a merchant name"""
        variations = [merchant]
        
        # Add variations from database
        for key, values in self.merchant_variations.items():
            if key in merchant.lower():
                variations.extend(values)
            for value in values:
                if value in merchant.lower():
                    variations.append(key)
        
        # Add variations with and without spaces
        variations.extend([v.replace(' ', '') for v in variations])
        variations.extend([v.replace('-', ' ') for v in variations])
        
        # Remove duplicates and empty strings
        return list(set(filter(None, variations)))
    
    def learn_merchant_pattern(self, merchant: str, pattern: Dict):
        """Learn new merchant pattern"""
        try:
            # Normalize merchant name
            merchant = self._normalize_merchant_name(merchant)
            
            # Add to variations if not exists
            if merchant not in self.merchant_variations:
                self.merchant_variations[merchant] = []
            
            # Add pattern-specific variations
            if 'amount' in pattern:
                amount = pattern['amount']
                if amount > 0:
                    self.merchant_variations[merchant].append(f"{merchant} {amount}")
            
            if 'category' in pattern:
                category = pattern['category']
                if category:
                    self.merchant_variations[merchant].append(f"{merchant} {category}")
            
            logging.info(f"Learned new pattern for {merchant}")
            
        except Exception as e:
            logging.error(f"Failed to learn merchant pattern: {e}")
    
    def get_merchant_category(self, merchant: str) -> Optional[str]:
        """Get merchant category based on patterns"""
        try:
            # Normalize merchant name
            merchant = self._normalize_merchant_name(merchant)
            
            # Check for category in variations
            for category, merchants in self.merchant_variations.items():
                if merchant in merchants:
                    return category
            
            return None
            
        except Exception as e:
            logging.error(f"Failed to get merchant category: {e}")
            return None
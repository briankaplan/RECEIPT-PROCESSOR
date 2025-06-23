import re
import logging
from datetime import datetime, timedelta
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class BankMatcher:
    """Match receipt data with bank statement transactions"""
    
    def __init__(self):
        self.amount_tolerance = 0.01  # $0.01 tolerance for amount matching
        self.date_tolerance_days = 3   # 3 days tolerance for date matching

    def fetch_and_process_teller_transactions(self, teller_client):
        """Fetch recent transactions from Teller using provided client"""
        print("🔄 Fetching Teller transactions...")
        if not teller_client or not teller_client.is_connected():
            print("❌ Teller client not connected")
            return []
        
        # Get all connected accounts and their transactions
        all_transactions = []
        accounts = teller_client.get_connected_accounts()
        for account in accounts:
            transactions = teller_client.get_transactions(account.id, limit=50)
            all_transactions.extend([tx.raw_data for tx in transactions])
        
        print(f"✅ Retrieved {len(all_transactions)} transactions from Teller.")
        return all_transactions

    def find_matches(self, receipt_data, bank_statements):
        """Find matching bank transactions for a receipt"""
        if not receipt_data or not bank_statements:
            return []
        
        matches = []
        receipt_amount = receipt_data.get('total_amount')
        receipt_date = self._parse_date(receipt_data.get('date'))
        receipt_merchant = receipt_data.get('merchant', '').lower()
        
        if not receipt_amount:
            logger.warning("No amount found in receipt, cannot match")
            return matches
        
        for statement in bank_statements:
            match_score = self._calculate_match_score(
                receipt_data, statement, receipt_amount, receipt_date, receipt_merchant
            )
            
            if match_score > 0.5:  # Threshold for considering a match
                matches.append({
                    'transaction': statement,
                    'confidence': match_score,
                    'match_reasons': self._get_match_reasons(
                        receipt_data, statement, receipt_amount, receipt_date, receipt_merchant
                    )
                })
        
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        logger.info(f"Found {len(matches)} potential matches for receipt")
        return matches

    def _calculate_match_score(self, receipt_data, statement, receipt_amount, receipt_date, receipt_merchant):
        """Calculate match confidence score between receipt and bank statement"""
        score = 0.0
        max_score = 3.0
        
        statement_amount = abs(float(statement.get('amount', 0)))
        if abs(receipt_amount - statement_amount) <= self.amount_tolerance:
            score += 1.5
        elif abs(receipt_amount - statement_amount) <= 5.0:
            score += 1.0
        elif abs(receipt_amount - statement_amount) <= 20.0:
            score += 0.5
        
        statement_date = self._parse_date(statement.get('date'))
        if receipt_date and statement_date:
            date_diff = abs((receipt_date - statement_date).days)
            if date_diff == 0:
                score += 1.0
            elif date_diff <= self.date_tolerance_days:
                score += 0.7
            elif date_diff <= 7:
                score += 0.3
        
        statement_desc = statement.get('description', '').lower()
        if receipt_merchant and statement_desc:
            similarity = self._text_similarity(receipt_merchant, statement_desc)
            score += similarity * 0.5
        
        return min(score / max_score, 1.0)

    def _get_match_reasons(self, receipt_data, statement, receipt_amount, receipt_date, receipt_merchant):
        """Get human-readable reasons for the match"""
        reasons = []
        
        statement_amount = abs(float(statement.get('amount', 0)))
        amount_diff = abs(receipt_amount - statement_amount)
        
        if amount_diff <= self.amount_tolerance:
            reasons.append(f"Exact amount match: ${receipt_amount:.2f}")
        elif amount_diff <= 5.0:
            reasons.append(f"Close amount match: ${receipt_amount:.2f} vs ${statement_amount:.2f}")
        
        statement_date = self._parse_date(statement.get('date'))
        if receipt_date and statement_date:
            date_diff = abs((receipt_date - statement_date).days)
            if date_diff == 0:
                reasons.append("Same date")
            elif date_diff <= self.date_tolerance_days:
                reasons.append(f"Date within {date_diff} days")
        
        statement_desc = statement.get('description', '').lower()
        if receipt_merchant and statement_desc:
            similarity = self._text_similarity(receipt_merchant, statement_desc)
            if similarity > 0.6:
                reasons.append(f"Merchant name similarity: {similarity:.1%}")
        
        return reasons

    def _parse_date(self, date_str):
        """Parse date string into datetime object"""
        if not date_str:
            return None
        
        formats = [
            '%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y',
            '%B %d, %Y', '%b %d, %Y', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S'
        ]
        
        date_str = str(date_str).strip()
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})', r'(\d{1,2}/\d{1,2}/\d{4})', r'(\d{1,2}-\d{1,2}-\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    date_part = match.group(1)
                    if '-' in date_part and len(date_part.split('-')[0]) == 4:
                        return datetime.strptime(date_part, '%Y-%m-%d')
                    elif '/' in date_part:
                        return datetime.strptime(date_part, '%m/%d/%Y')
                    elif '-' in date_part:
                        return datetime.strptime(date_part, '%m-%d-%Y')
                except ValueError:
                    continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None

    def _text_similarity(self, text1, text2):
        """Calculate text similarity between two strings"""
        if not text1 or not text2:
            return 0.0
        
        text1 = re.sub(r'[^\w\s]', '', text1.lower())
        text2 = re.sub(r'[^\w\s]', '', text2.lower())
        
        similarity = SequenceMatcher(None, text1, text2).ratio()
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if words1 and words2:
            common_words = words1.intersection(words2)
            word_similarity = len(common_words) / max(len(words1), len(words2))
            similarity = max(similarity, word_similarity)
        
        return similarity

    def generate_summary_report(self, matches):
        """Generate a summary report of matches"""
        if not matches:
            return "No matches found."
        
        report = f"Found {len(matches)} potential matches:\n\n"
        for i, match in enumerate(matches, 1):
            transaction = match['transaction']
            confidence = match['confidence']
            reasons = match.get('match_reasons', [])
            
            report += f"{i}. Match Confidence: {confidence:.1%}\n"
            report += f"   Transaction: {transaction.get('description', 'N/A')}\n"
            report += f"   Amount: ${abs(float(transaction.get('amount', 0))):.2f}\n"
            report += f"   Date: {transaction.get('date', 'N/A')}\n"
            if reasons:
                report += f"   Reasons: {', '.join(reasons)}\n"
            report += "\n"
        
        return report
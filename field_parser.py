#!/usr/bin/env python3
"""
Field Parser - Extract structured data from receipt text
"""

import re
import logging
from datetime import datetime
from typing import Dict, Optional, List
from decimal import Decimal, InvalidOperation

def parse_fields(text: str) -> Dict[str, str]:
    """
    Parse receipt text and extract structured fields
    """
    if not text:
        return {}
    
    # Clean text
    text = text.strip()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    fields = {
        'vendor': extract_vendor(text, lines),
        'amount': extract_amount(text, lines),
        'date': extract_date(text, lines),
        'tax': extract_tax(text, lines),
        'tip': extract_tip(text, lines),
        'items': extract_items(text, lines),
        'payment_method': extract_payment_method(text, lines),
        'receipt_number': extract_receipt_number(text, lines),
        'location': extract_location(text, lines),
        'full_text': text[:2000]  # Truncated for storage
    }
    
    # Clean empty fields
    return {k: v for k, v in fields.items() if v}

def extract_vendor(text: str, lines: List[str]) -> str:
    """Extract merchant/vendor name"""
    
    # Common vendor patterns
    vendor_patterns = [
        # Company names at top of receipt
        r'^([A-Z][A-Za-z\s&\.]{2,30}(?:LLC|INC|CORP|CO|LTD)?)',
        # Store names
        r'STORE[:\s]+([A-Za-z\s]{3,25})',
        r'MERCHANT[:\s]+([A-Za-z\s]{3,25})',
        # Restaurant patterns
        r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*$',
    ]
    
    # Check first few lines for vendor name
    for line in lines[:5]:
        for pattern in vendor_patterns:
            match = re.search(pattern, line)
            if match:
                vendor = match.group(1).strip()
                if len(vendor) > 2 and not re.match(r'^\d+$', vendor):
                    return vendor
    
    # Fallback: look for capitalized words
    for line in lines[:3]:
        if len(line) > 2 and line.isupper() and not re.search(r'\d', line):
            return line
    
    return ""

def extract_amount(text: str, lines: List[str]) -> str:
    """Extract total amount"""
    
    amount_patterns = [
        # Total patterns
        r'TOTAL[:\s]*\$?(\d+\.\d{2})',
        r'AMOUNT[:\s]*\$?(\d+\.\d{2})',
        r'BALANCE[:\s]*\$?(\d+\.\d{2})',
        r'CHARGED[:\s]*\$?(\d+\.\d{2})',
        # Generic dollar amounts
        r'\$(\d+\.\d{2})',
        # Amounts at end of lines
        r'(\d+\.\d{2})$',
    ]
    
    # Look for total-like keywords first
    for line in lines:
        line_upper = line.upper()
        if any(keyword in line_upper for keyword in ['TOTAL', 'AMOUNT DUE', 'BALANCE', 'CHARGED']):
            for pattern in amount_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        amount = float(match.group(1))
                        if 0.01 <= amount <= 10000:  # Reasonable range
                            return f"{amount:.2f}"
                    except (ValueError, InvalidOperation):
                        continue
    
    # Fallback: find largest reasonable dollar amount
    amounts = []
    for line in lines:
        for pattern in amount_patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                try:
                    amount = float(match)
                    if 0.01 <= amount <= 10000:
                        amounts.append(amount)
                except (ValueError, InvalidOperation):
                    continue
    
    if amounts:
        # Return the largest amount (likely the total)
        return f"{max(amounts):.2f}"
    
    return ""

def extract_date(text: str, lines: List[str]) -> str:
    """Extract transaction date"""
    
    date_patterns = [
        # MM/DD/YYYY formats
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{1,2}-\d{1,2}-\d{4})',
        # MM/DD/YY formats
        r'(\d{1,2}/\d{1,2}/\d{2})',
        r'(\d{1,2}-\d{1,2}-\d{2})',
        # Written dates
        r'([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',
        # ISO format
        r'(\d{4}-\d{2}-\d{2})',
    ]
    
    for line in lines[:10]:  # Check first 10 lines
        for pattern in date_patterns:
            match = re.search(pattern, line)
            if match:
                date_str = match.group(1)
                # Try to parse and validate
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    return parsed_date
    
    return ""

def parse_date_string(date_str: str) -> Optional[str]:
    """Parse various date formats and return YYYY-MM-DD"""
    
    date_formats = [
        '%m/%d/%Y', '%m-%d-%Y',
        '%m/%d/%y', '%m-%d-%y', 
        '%B %d, %Y', '%b %d, %Y',
        '%B %d %Y', '%b %d %Y',
        '%Y-%m-%d'
    ]
    
    for fmt in date_formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            # Handle 2-digit years
            if date_obj.year < 1950:
                date_obj = date_obj.replace(year=date_obj.year + 100)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return None

def extract_tax(text: str, lines: List[str]) -> str:
    """Extract tax amount"""
    
    tax_patterns = [
        r'TAX[:\s]*\$?(\d+\.\d{2})',
        r'SALES TAX[:\s]*\$?(\d+\.\d{2})',
        r'VAT[:\s]*\$?(\d+\.\d{2})',
    ]
    
    for line in lines:
        line_upper = line.upper()
        if 'TAX' in line_upper:
            for pattern in tax_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        tax = float(match.group(1))
                        if 0 <= tax <= 1000:
                            return f"{tax:.2f}"
                    except (ValueError, InvalidOperation):
                        continue
    
    return ""

def extract_tip(text: str, lines: List[str]) -> str:
    """Extract tip amount"""
    
    tip_patterns = [
        r'TIP[:\s]*\$?(\d+\.\d{2})',
        r'GRATUITY[:\s]*\$?(\d+\.\d{2})',
        r'SERVICE[:\s]*\$?(\d+\.\d{2})',
    ]
    
    for line in lines:
        line_upper = line.upper()
        if any(keyword in line_upper for keyword in ['TIP', 'GRATUITY', 'SERVICE']):
            for pattern in tip_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        tip = float(match.group(1))
                        if 0 <= tip <= 1000:
                            return f"{tip:.2f}"
                    except (ValueError, InvalidOperation):
                        continue
    
    return ""

def extract_items(text: str, lines: List[str]) -> str:
    """Extract item list"""
    
    items = []
    
    # Look for item patterns (name + price)
    item_pattern = r'^([A-Za-z][A-Za-z0-9\s]{2,30})\s+\$?(\d+\.\d{2})$'
    
    for line in lines:
        match = re.search(item_pattern, line.strip())
        if match:
            item_name = match.group(1).strip()
            item_price = match.group(2)
            # Skip lines that look like totals
            if not any(keyword in item_name.upper() for keyword in ['TOTAL', 'TAX', 'TIP', 'SUBTOTAL']):
                items.append(f"{item_name}: ${item_price}")
    
    return "; ".join(items[:10])  # Limit to first 10 items

def extract_payment_method(text: str, lines: List[str]) -> str:
    """Extract payment method"""
    
    payment_patterns = [
        r'CARD[:\s]*([A-Z0-9\*]{4,20})',
        r'CREDIT[:\s]*([A-Z0-9\*]{4,20})', 
        r'DEBIT[:\s]*([A-Z0-9\*]{4,20})',
        r'VISA[:\s]*([A-Z0-9\*]{4,20})',
        r'MASTERCARD[:\s]*([A-Z0-9\*]{4,20})',
        r'AMEX[:\s]*([A-Z0-9\*]{4,20})',
    ]
    
    # Check for cash
    if re.search(r'\bCASH\b', text, re.IGNORECASE):
        return "CASH"
    
    # Check for card patterns
    for line in lines:
        line_upper = line.upper()
        for pattern in payment_patterns:
            match = re.search(pattern, line_upper)
            if match:
                return f"CARD ({match.group(1)})"
    
    # Look for card keywords
    if re.search(r'\b(CARD|CREDIT|DEBIT|VISA|MASTERCARD|AMEX)\b', text, re.IGNORECASE):
        return "CARD"
    
    return ""

def extract_receipt_number(text: str, lines: List[str]) -> str:
    """Extract receipt number"""
    
    receipt_patterns = [
        r'RECEIPT[:\s#]*([A-Z0-9]{4,20})',
        r'TRANSACTION[:\s#]*([A-Z0-9]{4,20})',
        r'REF[:\s#]*([A-Z0-9]{4,20})',
        r'#([A-Z0-9]{4,20})',
    ]
    
    for line in lines:
        line_upper = line.upper()
        if any(keyword in line_upper for keyword in ['RECEIPT', 'TRANSACTION', 'REF', '#']):
            for pattern in receipt_patterns:
                match = re.search(pattern, line_upper)
                if match:
                    return match.group(1)
    
    return ""

def extract_location(text: str, lines: List[str]) -> str:
    """Extract store location"""
    
    # Look for address patterns
    address_patterns = [
        r'(\d+\s+[A-Za-z\s]+(?:ST|STREET|AVE|AVENUE|RD|ROAD|BLVD|BOULEVARD|DR|DRIVE))',
        r'([A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5})',  # City, State ZIP
    ]
    
    for line in lines:
        for pattern in address_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    # Look for phone numbers (often near location)
    phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    for i, line in enumerate(lines):
        if re.search(phone_pattern, line):
            # Check surrounding lines for location info
            context_lines = lines[max(0, i-2):i+3]
            for context_line in context_lines:
                for pattern in address_patterns:
                    match = re.search(pattern, context_line, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
    
    return ""

# Test the parser
if __name__ == "__main__":
    sample_text = """
    STARBUCKS STORE #12345
    123 MAIN STREET
    NASHVILLE TN 37203
    
    06/10/2025 3:45 PM
    
    GRANDE COFFEE        $4.85
    MUFFIN              $3.25
    
    SUBTOTAL            $8.10
    TAX                 $0.73
    TOTAL               $8.83
    
    CARD ****1234
    RECEIPT #ABC123
    """
    
    result = parse_fields(sample_text)
    print("🧪 Field Parser Test:")
    for key, value in result.items():
        print(f"  {key}: {value}")
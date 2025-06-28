#!/usr/bin/env python3
"""
Test script to see actual email subjects from personalized search
"""

import requests
import json

def test_email_subjects():
    """Test to see what email subjects we're getting"""
    
    # Call the personalized email search
    url = "http://localhost:10000/api/personalized-email-search"
    data = {
        "days_back": 30,
        "max_emails": 10
    }
    
    try:
        response = requests.post(url, json=data)
        result = response.json()
        
        print("🎯 Personalized Email Search Results:")
        print(f"Success: {result.get('success', False)}")
        print(f"Receipts Found: {result.get('receipts_found', 0)}")
        print(f"Receipts Matched: {result.get('receipts_matched', 0)}")
        print(f"Search Strategies: {result.get('search_strategies', 0)}")
        print(f"Average Confidence: {result.get('average_confidence', 0.0):.2f}")
        
        # Get processing details
        details = result.get('processing_details', {})
        print(f"\n📧 Processing Details:")
        print(f"Receipts Processed: {details.get('receipts_processed', 0)}")
        print(f"Receipts Matched: {details.get('receipts_matched', 0)}")
        print(f"Receipts Uploaded: {details.get('receipts_uploaded', 0)}")
        print(f"Errors: {len(details.get('errors', []))}")
        
        # Show sample subjects from matches
        matches = details.get('matches', [])
        if matches:
            print(f"\n✅ Matched Receipts:")
            for i, match in enumerate(matches[:5], 1):
                receipt_data = match.get('receipt_data', {})
                print(f"{i}. Subject: {receipt_data.get('subject', 'No subject')}")
                print(f"   Merchant: {receipt_data.get('merchant', 'Unknown')}")
                print(f"   Amount: ${receipt_data.get('amount', 0)}")
                print(f"   Confidence: {match.get('confidence', 0):.2f}")
                print()
        else:
            print(f"\n❌ No matches found")
            
            # Show some sample subjects from the search results
            print(f"\n📧 Sample Email Subjects (from search results):")
            # We need to modify the personalized search to return the actual subjects
            print("Need to modify search to return actual subjects")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_email_subjects() 
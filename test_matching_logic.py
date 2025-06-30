#!/usr/bin/env python3
"""
Test script to demonstrate smart matching between CSV and Teller transactions
"""

import os
import sys
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.mongo_service import MongoService

def test_matching_logic():
    """Test the smart matching logic"""
    print("🧪 Testing Smart CSV-Teller Transaction Matching")
    print("=" * 60)
    
    mongo = MongoService()
    
    # Get sample CSV transactions
    csv_transactions = mongo.get_bank_transactions(limit=10)
    
    print(f"📊 Found {len(csv_transactions)} CSV transactions")
    
    # Create sample Teller transactions that should match
    sample_teller_transactions = [
        {
            'id': 'teller_123',
            'amount': -384.14,
            'date': datetime(2025, 6, 1),
            'description': 'CAMBRIA HOTEL NASHVILLE DOWNTOWN',
            'user_id': 'default_user'
        },
        {
            'id': 'teller_456',
            'amount': -19.76,
            'date': datetime(2025, 6, 1),
            'description': 'ONLINE PURCHASE - AMAZON.COM',
            'user_id': 'default_user'
        },
        {
            'id': 'teller_789',
            'amount': -244.87,
            'date': datetime(2025, 6, 1),
            'description': 'GOOGLE *GSUITE_musicci',
            'user_id': 'default_user'
        }
    ]
    
    print(f"\n🔍 Testing matching for {len(sample_teller_transactions)} sample Teller transactions")
    
    for teller_tx in sample_teller_transactions:
        print(f"\n📋 Teller Transaction: {teller_tx['description']}")
        print(f"   Amount: ${teller_tx['amount']}")
        print(f"   Date: {teller_tx['date'].strftime('%Y-%m-%d')}")
        
        # Find potential matches
        amount = teller_tx['amount']
        date = teller_tx['date']
        description = teller_tx['description'].lower()
        
        # Look for CSV transactions with same amount and similar date (±3 days)
        date_start = date - timedelta(days=3)
        date_end = date + timedelta(days=3)
        
        potential_matches = []
        for csv_tx in csv_transactions:
            if (csv_tx.get('amount') == amount and 
                csv_tx.get('source') == 'csv_upload' and
                date_start <= csv_tx.get('date') <= date_end):
                
                csv_description = csv_tx.get('description', '').lower()
                similarity = SequenceMatcher(None, description, csv_description).ratio()
                
                potential_matches.append({
                    'csv_tx': csv_tx,
                    'similarity': similarity
                })
        
        if potential_matches:
            # Sort by similarity
            potential_matches.sort(key=lambda x: x['similarity'], reverse=True)
            best_match = potential_matches[0]
            
            print(f"✅ Found {len(potential_matches)} potential matches")
            print(f"   Best match: {best_match['csv_tx']['description']}")
            print(f"   Similarity: {best_match['similarity']:.2%}")
            
            if best_match['similarity'] > 0.6:
                print(f"   🎯 MATCHED! (Similarity > 60%)")
            else:
                print(f"   ❌ No good match (Similarity < 60%)")
        else:
            print(f"❌ No potential matches found")
    
    print(f"\n📈 Summary:")
    print(f"   - CSV transactions: {len(csv_transactions)}")
    print(f"   - Sample Teller transactions: {len(sample_teller_transactions)}")
    print(f"   - Matching logic uses: Amount + Date (±3 days) + Description similarity")
    print(f"   - Minimum similarity threshold: 60%")

if __name__ == "__main__":
    test_matching_logic() 
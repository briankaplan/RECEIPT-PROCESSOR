#!/usr/bin/env python3
"""
Import bank transactions from CSV to MongoDB
"""

import csv
import logging
from datetime import datetime
from pymongo import MongoClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def import_transactions():
    """Import transactions from CSV to MongoDB"""
    
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['expense']
    
    # Clear existing transactions
    db.bank_transactions.delete_many({})
    logger.info("🗑️ Cleared existing transactions")
    
    # Read CSV file
    transactions = []
    with open('bank_transactions.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                # Parse amount (remove negative sign for consistency)
                amount_str = row['Amount'].replace('$', '').replace(',', '')
                amount = float(amount_str)
                
                # Parse dates
                transaction_date = datetime.strptime(row['Transaction Date'], '%m/%d/%Y')
                post_date = datetime.strptime(row['Post Date'], '%m/%d/%Y')
                
                # Create transaction document
                transaction = {
                    'transaction_date': transaction_date,
                    'post_date': post_date,
                    'description': row['Description'],
                    'merchant': row['Description'],  # Use description as merchant
                    'category': row['Category'],
                    'type': row['Type'],
                    'amount': amount,
                    'memo': row['Memo'],
                    'imported_at': datetime.utcnow()
                }
                
                transactions.append(transaction)
                
            except Exception as e:
                logger.error(f"Error parsing row {row}: {e}")
    
    # Insert transactions
    if transactions:
        result = db.bank_transactions.insert_many(transactions)
        logger.info(f"✅ Imported {len(result.inserted_ids)} transactions")
        
        # Show sample transactions
        sample = list(db.bank_transactions.find().limit(5))
        logger.info("📊 Sample transactions:")
        for txn in sample:
            logger.info(f"  {txn['merchant']} - ${txn['amount']} - {txn['transaction_date'].strftime('%m/%d/%Y')}")
    else:
        logger.error("❌ No transactions to import")

if __name__ == "__main__":
    import_transactions() 
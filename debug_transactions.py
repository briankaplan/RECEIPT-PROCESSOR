#!/usr/bin/env python3

from app import create_app
from pymongo import MongoClient

app = create_app()

with app.app_context():
    print("=== Debug Transaction Service ===")
    
    # Check services
    print(f"Transaction service: {hasattr(app, 'transaction_service')}")
    print(f"Mongo service: {hasattr(app, 'mongo_service')}")
    
    if hasattr(app, 'mongo_service'):
        print(f"Mongo client: {hasattr(app.mongo_service, 'client')}")
        if hasattr(app.mongo_service, 'client'):
            print(f"DB: {app.mongo_service.client.db}")
    
    # Test direct database access
    try:
        client = MongoClient('mongodb+srv://kaplanbrian:tixvob-7Nefza-pijtaq@expense.1q8c63f.mongodb.net/?retryWrites=true&w=majority&appName=Expense')
        db = client['expense']
        count = db.transactions.count_documents({})
        print(f"Direct DB count: {count}")
        
        # Test transaction service
        if hasattr(app, 'transaction_service'):
            result = app.transaction_service.get_transactions(page=1, page_size=5)
            print(f"Transaction service result: {result}")
        else:
            print("No transaction service found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc() 
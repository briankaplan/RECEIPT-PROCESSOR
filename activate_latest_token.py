#!/usr/bin/env python3
"""
Activate the latest Teller token
"""

from app.services.mongo_service import MongoService

def activate_latest_token():
    mongo = MongoService()
    
    # Find the latest token
    latest_token = mongo.client.db.teller_tokens.find_one(sort=[('created_at', -1)])
    
    if latest_token:
        # Deactivate all tokens first
        mongo.client.db.teller_tokens.update_many({}, {'$set': {'active': False}})
        
        # Activate the latest token
        mongo.client.db.teller_tokens.update_one(
            {'_id': latest_token['_id']}, 
            {'$set': {'active': True}}
        )
        
        print(f"✅ Activated latest token: {latest_token['_id']}")
        print(f"Account: {latest_token.get('account_name', 'Unknown')}")
        print(f"Created: {latest_token.get('created_at', 'Unknown')}")
    else:
        print("❌ No tokens found")

if __name__ == "__main__":
    activate_latest_token() 
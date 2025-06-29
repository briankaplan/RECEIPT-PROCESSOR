#!/usr/bin/env python3
"""
Script to check and manage users in the database
"""

from app.services.mongo_service import MongoService
import json

def check_users():
    """Check what users exist in the database"""
    try:
        mongo_service = MongoService()
        
        # Get all users from the correct collection
        users = list(mongo_service.client.db.users.find({}, {'username': 1, 'email': 1, 'created_at': 1, '_id': 1}))
        
        print(f"Found {len(users)} users in database:")
        for user in users:
            print(f"- ID: {user['_id']}, Username: {user['username']}, Email: {user['email']}")
        
        # Also check if the collection exists
        collections = mongo_service.client.db.list_collection_names()
        print(f"\nCollections in database: {collections}")
        
        return users
        
    except Exception as e:
        print(f"Error checking users: {e}")
        return []

def clear_users():
    """Clear all users from the database (for testing)"""
    try:
        mongo_service = MongoService()
        
        result = mongo_service.client.db.users.delete_many({})
        print(f"Cleared {result.deleted_count} users from database")
        
    except Exception as e:
        print(f"Error clearing users: {e}")

if __name__ == "__main__":
    print("Checking users in database...")
    users = check_users()
    
    if users:
        response = input("\nDo you want to clear all users for testing? (y/N): ")
        if response.lower() == 'y':
            clear_users()
            print("Users cleared. You can now create new accounts.")
        else:
            print("Users not cleared.")
    else:
        print("No users found. You can create new accounts.") 
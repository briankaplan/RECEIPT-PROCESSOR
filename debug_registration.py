#!/usr/bin/env python3
"""
Debug script for registration process
"""

from app.services.mongo_service import MongoService
from app.utils.security import AuthenticationService
from bson import ObjectId

def debug_registration():
    """Debug the registration process"""
    try:
        print("🔍 Debugging registration process...")
        
        # Initialize services
        mongo_service = MongoService()
        auth_service = AuthenticationService(mongo_service)
        
        print(f"✅ MongoDB connected: {mongo_service.client.connected}")
        print(f"✅ Database: {mongo_service.client.db.name}")
        
        # Check if users collection exists
        collections = mongo_service.client.db.list_collection_names()
        print(f"📚 Collections: {collections}")
        
        # Check if users collection exists
        if 'users' in collections:
            print("✅ Users collection exists")
            user_count = mongo_service.client.db.users.count_documents({})
            print(f"👥 User count: {user_count}")
            
            if user_count > 0:
                users = list(mongo_service.client.db.users.find({}, {'username': 1, 'email': 1}))
                print("📋 Existing users:")
                for user in users:
                    print(f"  - {user['username']} ({user['email']})")
        else:
            print("❌ Users collection does not exist")
        
        # Test user creation
        test_username = "debug_test_user"
        test_email = "debug@test.com"
        test_password = "debugpass123"
        
        print(f"\n🧪 Testing user creation for: {test_username}")
        
        # Check if user exists
        existing_user = mongo_service.client.db.users.find_one({'username': test_username})
        if existing_user:
            print(f"❌ User {test_username} already exists")
            return False
        else:
            print(f"✅ User {test_username} does not exist")
        
        # Try to create user
        success = auth_service.create_user(test_username, test_password, test_email)
        
        if success:
            print(f"✅ User {test_username} created successfully!")
            
            # Verify user was created
            created_user = mongo_service.client.db.users.find_one({'username': test_username})
            if created_user:
                print(f"✅ User verified in database: {created_user['username']}")
                
                # Clean up - delete test user
                mongo_service.client.db.users.delete_one({'_id': created_user['_id']})
                print(f"🧹 Test user cleaned up")
            else:
                print(f"❌ User not found in database after creation")
        else:
            print(f"❌ User creation failed")
        
        return success
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_registration() 
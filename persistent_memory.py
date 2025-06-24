"""
Persistent Memory System for Receipt Processor
Maintains settings, connections, and user preferences across deployments and updates
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pymongo import MongoClient

logger = logging.getLogger(__name__)

@dataclass 
class UserSettings:
    """User preference settings"""
    user_id: str = "default"
    email_notifications: bool = True
    processing_frequency: str = "daily"
    auto_process_receipts: bool = True
    default_receipt_category: str = "Business Expense"
    amount_tolerance: float = 0.01
    date_tolerance_days: int = 3
    preferred_export_format: str = "google_sheets"
    theme: str = "light"
    dashboard_layout: str = "default"
    language: str = "en"
    timezone: str = "America/New_York"
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class SystemSettings:
    """System-wide configuration settings"""
    setting_id: str = "system_config"
    max_concurrent_processing: int = 3
    processing_batch_size: int = 50
    default_processing_days: int = 30
    auto_backup_enabled: bool = True
    backup_frequency: str = "weekly"
    maintenance_mode: bool = False
    debug_mode: bool = False
    auto_cleanup_old_data: bool = True
    data_retention_days: int = 365
    created_at: datetime = None
    updated_at: datetime = None

class PersistentMemory:
    """
    Comprehensive persistent memory system for Receipt Processor
    Manages settings, preferences, connections across deployments
    """
    
    def __init__(self, mongo_uri: str = None, database_name: str = "expense"):
        self.mongo_uri = mongo_uri or os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        self.database_name = database_name
        self.client = None
        self.db = None
        self.connected = False
        
        # Collections
        self.user_settings_collection = "user_settings"
        self.system_settings_collection = "system_settings"
        self.connection_states_collection = "connection_states"
        self.persistent_cache_collection = "persistent_cache"
        
        self._connect()
        
    def _connect(self) -> bool:
        """Connect to MongoDB with proper error handling"""
        try:
            if not self.mongo_uri:
                logger.warning("No MongoDB URI configured for persistent memory")
                return False
                
            self.client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                maxPoolSize=10,
                retryWrites=True
            )
            
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            self.connected = True
            
            # Initialize collections and indexes
            self._create_indexes()
            self._initialize_default_settings()
            
            logger.info("✅ Persistent Memory System connected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect Persistent Memory: {e}")
            self.connected = False
            return False
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            if not self.connected:
                return
                
            # User settings indexes
            self.db[self.user_settings_collection].create_index("user_id", unique=True)
            
            # System settings indexes  
            self.db[self.system_settings_collection].create_index("setting_id", unique=True)
            
            # Connection states indexes
            self.db[self.connection_states_collection].create_index("connection_id", unique=True)
            self.db[self.connection_states_collection].create_index([("service_type", 1), ("user_id", 1)])
            self.db[self.connection_states_collection].create_index("status")
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    def _initialize_default_settings(self):
        """Initialize default system settings if they don't exist"""
        try:
            if not self.connected:
                return
                
            # Check if system settings exist
            existing_settings = self.db[self.system_settings_collection].find_one({"setting_id": "system_config"})
            if not existing_settings:
                default_settings = SystemSettings()
                default_settings.created_at = datetime.utcnow()
                default_settings.updated_at = datetime.utcnow()
                
                self.db[self.system_settings_collection].insert_one(asdict(default_settings))
                logger.info("✅ Default system settings initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize default settings: {e}")
    
    def get_user_settings(self, user_id: str = "default") -> UserSettings:
        """Get user settings with fallback to defaults"""
        try:
            if not self.connected:
                return UserSettings(user_id=user_id)
                
            settings_doc = self.db[self.user_settings_collection].find_one({"user_id": user_id})
            if settings_doc:
                settings_doc.pop('_id', None)
                return UserSettings(**settings_doc)
            else:
                return UserSettings(user_id=user_id)
                
        except Exception as e:
            logger.error(f"Failed to get user settings for {user_id}: {e}")
            return UserSettings(user_id=user_id)
    
    def save_user_settings(self, settings: UserSettings) -> bool:
        """Save user settings to persistent storage"""
        try:
            if not self.connected:
                logger.warning("Cannot save user settings - not connected")
                return False
                
            settings.updated_at = datetime.utcnow()
            if not settings.created_at:
                settings.created_at = datetime.utcnow()
                
            result = self.db[self.user_settings_collection].replace_one(
                {"user_id": settings.user_id},
                asdict(settings),
                upsert=True
            )
            
            logger.info(f"✅ User settings saved for {settings.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user settings: {e}")
            return False
    
    def update_user_setting(self, user_id: str, setting_key: str, setting_value: Any) -> bool:
        """Update a specific user setting"""
        try:
            if not self.connected:
                return False
                
            result = self.db[self.user_settings_collection].update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        setting_key: setting_value,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            logger.info(f"✅ Updated {setting_key} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user setting: {e}")
            return False
    
    def get_system_settings(self) -> SystemSettings:
        """Get system-wide settings"""
        try:
            if not self.connected:
                return SystemSettings()
                
            settings_doc = self.db[self.system_settings_collection].find_one({"setting_id": "system_config"})
            if settings_doc:
                settings_doc.pop('_id', None)
                return SystemSettings(**settings_doc)
            else:
                return SystemSettings()
                
        except Exception as e:
            logger.error(f"Failed to get system settings: {e}")
            return SystemSettings()
    
    def save_system_settings(self, settings: SystemSettings) -> bool:
        """Save system settings"""
        try:
            if not self.connected:
                return False
                
            settings.updated_at = datetime.utcnow()
            if not settings.created_at:
                settings.created_at = datetime.utcnow()
                
            result = self.db[self.system_settings_collection].replace_one(
                {"setting_id": settings.setting_id},
                asdict(settings),
                upsert=True
            )
            
            logger.info("✅ System settings saved")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save system settings: {e}")
            return False
    
    def update_system_setting(self, setting_key: str, setting_value: Any) -> bool:
        """Update a specific system setting"""
        try:
            if not self.connected:
                return False
                
            result = self.db[self.system_settings_collection].update_one(
                {"setting_id": "system_config"},
                {
                    "$set": {
                        setting_key: setting_value,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            logger.info(f"✅ Updated system setting: {setting_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update system setting: {e}")
            return False
    
    def remember_bank_connection(self, user_id: str, access_token: str, enrollment_data: Dict) -> bool:
        """Remember bank connection for long-term persistence"""
        try:
            if not self.connected:
                return False
                
            # Store in both teller_tokens and connection_states for redundancy
            teller_record = {
                "access_token": access_token,
                "user_id": user_id,
                "enrollment_id": enrollment_data.get('enrollment_id'),
                "connected_at": datetime.utcnow(),
                "environment": os.getenv('TELLER_ENVIRONMENT', 'development'),
                "status": "active",
                "auto_reconnect": True,
                "last_sync_attempt": None,
                "last_successful_sync": None,
                "persistent_memory": True  # Flag for our memory system
            }
            
            # Update or insert
            self.db['teller_tokens'].update_one(
                {"user_id": user_id},
                {"$set": teller_record},
                upsert=True
            )
            
            logger.info(f"✅ Bank connection remembered for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remember bank connection: {e}")
            return False
    
    def get_remembered_bank_connections(self) -> List[Dict]:
        """Get all remembered bank connections"""
        try:
            if not self.connected:
                return []
                
            connections = list(self.db['teller_tokens'].find(
                {"status": "active"},
                {"_id": 0}
            ))
            
            return connections
            
        except Exception as e:
            logger.error(f"Failed to get remembered bank connections: {e}")
            return []
    
    def update_connection_sync_status(self, user_id: str, success: bool, error_message: str = None) -> bool:
        """Update the sync status for a bank connection"""
        try:
            if not self.connected:
                return False
                
            update_data = {
                "last_sync_attempt": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            if success:
                update_data["last_successful_sync"] = datetime.utcnow()
                update_data["status"] = "active"
                update_data["error_message"] = None
            else:
                update_data["error_message"] = error_message
                # Don't change status to error immediately, allow retries
                
            self.db['teller_tokens'].update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update connection sync status: {e}")
            return False
    
    def cache_set(self, key: str, value: Any, expires_minutes: int = 60) -> bool:
        """Set a value in persistent cache with expiration"""
        try:
            if not self.connected:
                return False
                
            expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
            
            cache_doc = {
                "cache_key": key,
                "cache_value": value,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at
            }
            
            result = self.db[self.persistent_cache_collection].replace_one(
                {"cache_key": key},
                cache_doc,
                upsert=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache: {e}")
            return False
    
    def cache_get(self, key: str) -> Any:
        """Get a value from persistent cache"""
        try:
            if not self.connected:
                return None
                
            # Clean expired entries first
            self.db[self.persistent_cache_collection].delete_many({
                "expires_at": {"$lt": datetime.utcnow()}
            })
            
            doc = self.db[self.persistent_cache_collection].find_one({"cache_key": key})
            if doc and doc.get("expires_at") > datetime.utcnow():
                return doc.get("cache_value")
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cache: {e}")
            return None
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about persistent memory usage"""
        try:
            if not self.connected:
                return {"connected": False}
                
            # Get counts
            user_settings_count = self.db[self.user_settings_collection].count_documents({})
            system_settings_count = self.db[self.system_settings_collection].count_documents({})
            active_connections = self.db['teller_tokens'].count_documents({"status": "active"})
            cache_entries = self.db[self.persistent_cache_collection].count_documents({})
            
            # Get recent activity
            recent_connections = list(self.db['teller_tokens'].find(
                {"status": "active"}, 
                {"user_id": 1, "connected_at": 1, "last_successful_sync": 1, "_id": 0}
            ).sort("connected_at", -1).limit(5))
            
            stats = {
                "connected": True,
                "database": self.database_name,
                "collections": {
                    "user_settings": user_settings_count,
                    "system_settings": system_settings_count,
                    "active_bank_connections": active_connections,
                    "cache_entries": cache_entries
                },
                "recent_connections": recent_connections,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"connected": False, "error": str(e)}

# =====================================================================
# GLOBAL INSTANCE AND HELPER FUNCTIONS
# =====================================================================

# Global persistent memory instance
persistent_memory = None

def get_persistent_memory() -> PersistentMemory:
    """Get global persistent memory instance"""
    global persistent_memory
    if persistent_memory is None:
        persistent_memory = PersistentMemory()
    return persistent_memory

def remember_user_setting(user_id: str, setting_key: str, value: Any) -> bool:
    """Convenient function to remember a user setting"""
    memory = get_persistent_memory()
    return memory.update_user_setting(user_id, setting_key, value)

def remember_system_setting(setting_key: str, value: Any) -> bool:
    """Convenient function to remember a system setting"""
    memory = get_persistent_memory()
    return memory.update_system_setting(setting_key, value)

def remember_bank_connection(user_id: str, access_token: str, enrollment_data: Dict) -> bool:
    """Convenient function to remember a bank connection"""
    memory = get_persistent_memory()
    return memory.remember_bank_connection(user_id, access_token, enrollment_data)

if __name__ == "__main__":
    # Test the persistent memory system
    print("🧠 Testing Persistent Memory System")
    print("=" * 50)
    
    memory = PersistentMemory()
    if memory.connected:
        print("✅ Connected to persistent storage")
        
        # Test stats
        stats = memory.get_memory_stats()
        print(f"📊 Memory Stats: {stats}")
        
        # Test user settings
        user_settings = memory.get_user_settings("test_user")
        user_settings.auto_process_receipts = True
        user_settings.processing_frequency = "daily"
        memory.save_user_settings(user_settings)
        print("✅ User settings test completed")
        
        # Test system settings
        system_settings = memory.get_system_settings()
        system_settings.max_concurrent_processing = 5
        memory.save_system_settings(system_settings)
        print("✅ System settings test completed")
        
    else:
        print("❌ Failed to connect to persistent storage")

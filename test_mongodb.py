#!/usr/bin/env python3
"""
Test MongoDB Connection
Tests connection to MongoDB and basic operations
"""

import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime
import logging
import dns.resolver

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from JSON file"""
    try:
        with open('config/expense_config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def test_dns_resolution(hostname):
    """Test DNS resolution for MongoDB hostname"""
    try:
        logger.info(f"🔍 Testing DNS resolution for {hostname}")
        answers = dns.resolver.resolve(hostname, 'A')
        for rdata in answers:
            logger.info(f"✅ DNS resolution successful: {hostname} -> {rdata}")
        return True
    except Exception as e:
        logger.error(f"❌ DNS resolution failed for {hostname}: {e}")
        return False

def test_mongodb_connection():
    """Test MongoDB connection and basic operations"""
    config = load_config()
    if not config:
        return False
        
    try:
        # Get MongoDB configuration
        mongo_uri = config['mongodb']['uri']
        database_name = config['mongodb']['database']
        
        # Extract hostname from URI for DNS test
        hostname = mongo_uri.split('://')[1].split('/')[0]
        if not test_dns_resolution(hostname):
            return False
        
        logger.info("🔌 Testing MongoDB connection...")
        logger.info(f"Using URI: {mongo_uri}")
        logger.info(f"Database: {database_name}")
        
        # Connect to MongoDB with additional options
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000,
            socketTimeoutMS=5000
        )
        
        # Test connection
        try:
            client.admin.command('ping')
            logger.info("✅ Successfully connected to MongoDB")
        except ConnectionFailure as e:
            logger.error(f"❌ Could not connect to MongoDB: {e}")
            return False
        except ServerSelectionTimeoutError as e:
            logger.error(f"❌ Server selection timeout: {e}")
            return False
        
        db = client[database_name]
        
        # Test basic operations
        test_collection = db['test_collection']
        
        # Insert test document
        test_doc = {
            'test_id': 'connection_test',
            'timestamp': datetime.now(),
            'status': 'success'
        }
        result = test_collection.insert_one(test_doc)
        logger.info(f"✅ Successfully inserted test document: {result.inserted_id}")
        
        # Read test document
        retrieved_doc = test_collection.find_one({'test_id': 'connection_test'})
        logger.info(f"✅ Successfully retrieved test document: {retrieved_doc}")
        
        # Clean up test document
        test_collection.delete_one({'test_id': 'connection_test'})
        logger.info("✅ Successfully cleaned up test document")
        
        # Test collections
        collections = db.list_collection_names()
        logger.info(f"📚 Available collections: {collections}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MongoDB connection test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_mongodb_connection()
    if success:
        logger.info("🎉 MongoDB connection test completed successfully")
    else:
        logger.error("❌ MongoDB connection test failed") 
#!/usr/bin/env python3
"""
Test R2 Storage Connection
Tests connection to Cloudflare R2 storage and basic operations
"""

import boto3
import logging
import json
import os
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from JSON file"""
    config_path = os.path.join('config', 'expense_config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return None

def test_r2_connection():
    """Test R2 storage connection and operations"""
    config = load_config()
    if not config:
        return False
        
    r2_config = config.get('r2', {})
    endpoint = r2_config.get('endpoint')
    access_key = r2_config.get('access_key')
    secret_key = r2_config.get('secret_key')
    bucket = r2_config.get('bucket')
    
    if not all([endpoint, access_key, secret_key, bucket]):
        logger.error("R2 configuration incomplete")
        return False
    
    logger.info("🔌 Testing R2 storage connection...")
    
    try:
        # Initialize R2 client
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        # Test bucket access
        s3.head_bucket(Bucket=bucket)
        logger.info("✅ Successfully connected to R2 storage")
        
        # Test file operations
        test_key = 'test/test.txt'
        test_content = b'This is a test file for R2 storage'
        
        # Upload test file
        s3.put_object(
            Bucket=bucket,
            Key=test_key,
            Body=test_content
        )
        logger.info("✅ Successfully uploaded test file")
        
        # Download test file
        response = s3.get_object(Bucket=bucket, Key=test_key)
        downloaded_content = response['Body'].read()
        if downloaded_content == test_content:
            logger.info("✅ Successfully downloaded test file")
        else:
            logger.error("❌ Downloaded content does not match uploaded content")
            return False
        
        # Delete test file
        s3.delete_object(Bucket=bucket, Key=test_key)
        logger.info("✅ Successfully deleted test file")
        
        return True
        
    except ClientError as e:
        logger.error(f"❌ R2 storage test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_r2_connection()
    if success:
        logger.info("🎉 R2 storage test completed successfully")
    else:
        logger.error("❌ R2 storage test failed") 
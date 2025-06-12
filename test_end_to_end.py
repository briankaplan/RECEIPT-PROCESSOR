#!/usr/bin/env python3
"""
End-to-End Integration Test
Tests the complete flow from Gmail to final storage/export
"""
import os
import json
import logging
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.cloud import vision
from google.oauth2 import service_account
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import boto3
from googleapiclient.discovery import build as sheets_build
from google.oauth2.service_account import Credentials as SheetsCredentials

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join('config', 'expense_config.json')

def load_config():
    """Load configuration from JSON file"""
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return None

def init_gmail(account_config, port):
    """Initialize Gmail API client for a specific account"""
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    creds = None
    
    # Use the client file from the account config
    credentials_path = account_config['client_file']
    if not os.path.exists(credentials_path):
        raise ValueError(f"Client configuration file not found: {credentials_path}")
    
    # Use the pickle file from the account config
    pickle_file = account_config['pickle_file']
    
    if os.path.exists(pickle_file):
        try:
            creds = Credentials.from_authorized_user_file(pickle_file, SCOPES)
        except Exception as e:
            logger.warning(f"Error loading credentials from {pickle_file}: {e}")
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.warning(f"Error refreshing credentials: {e}")
                creds = None
        
        if not creds:
            # Use the correct redirect URI based on the port
            redirect_uri = f'http://localhost:{port}'
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, 
                SCOPES,
                redirect_uri=redirect_uri
            )
            # Force consent screen to ensure we get a refresh token
            creds = flow.run_local_server(
                port=port,
                prompt='consent',
                authorization_prompt_message='Please authorize the application to access your Gmail account.'
            )
        
        # Save the credentials
        os.makedirs(os.path.dirname(pickle_file), exist_ok=True)
        with open(pickle_file, 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def init_vision(service_account_path):
    """Initialize Vision API client"""
    creds = service_account.Credentials.from_service_account_file(service_account_path)
    return vision.ImageAnnotatorClient(credentials=creds)

def init_huggingface():
    """Initialize Hugging Face model"""
    return SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

def init_mongodb(uri):
    """Initialize MongoDB client"""
    client = MongoClient(uri, server_api=ServerApi('1'))
    client.admin.command('ping')
    return client

def init_r2(config):
    """Initialize R2 client"""
    return boto3.client(
        's3',
        endpoint_url=config['endpoint'],
        aws_access_key_id=config['access_key'],
        aws_secret_access_key=config['secret_key']
    )

def init_sheets(service_account_path):
    """Initialize Google Sheets client"""
    creds = SheetsCredentials.from_service_account_file(service_account_path, 
        scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return sheets_build('sheets', 'v4', credentials=creds)

def test_end_to_end():
    """Run end-to-end test of all integrations"""
    config = load_config()
    if not config:
        return False

    try:
        # Initialize all services
        logger.info("Initializing services...")
        
        # Initialize Gmail for each account with their specific ports
        gmail_clients = {}
        port_map = {
            'kaplan.brian@gmail.com': 8080,
            'brian@downhome.com': 8082,
            'brian@musiccityrodeo.com': 8081
        }
        
        for account in config['gmail_accounts']:
            port = port_map[account['email']]
            logger.info(f"Initializing Gmail for {account['email']} on port {port}...")
            gmail_clients[account['email']] = init_gmail(
                account,
                port
            )
            logger.info(f"✅ Gmail API initialized for {account['email']}")

        # Vision API
        vision_client = init_vision(config['service_account_path'])
        logger.info("✅ Vision API initialized")

        # Hugging Face
        hf_model = init_huggingface()
        logger.info("✅ Hugging Face model loaded")

        # MongoDB
        mongo_client = init_mongodb(config['mongodb']['uri'])
        db = mongo_client[config['mongodb']['database']]
        logger.info("✅ MongoDB connected")

        # R2
        r2_client = init_r2(config['r2'])
        logger.info("✅ R2 storage initialized")

        # Google Sheets
        sheets = init_sheets(config['service_account_path'])
        logger.info("✅ Google Sheets API initialized")

        # Test Gmail search for each account
        for email, gmail in gmail_clients.items():
            logger.info(f"Searching Gmail for {email}...")
            query = "test OR sample"
            results = gmail.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} test messages for {email}")

            if messages:
                # Process first message
                msg = gmail.users().messages().get(userId='me', id=messages[0]['id']).execute()
                subject = next(h['value'] for h in msg['payload']['headers'] if h['name'] == 'Subject')
                logger.info(f"Processing message: {subject}")

                # Generate embeddings
                embedding = hf_model.encode(subject)
                logger.info(f"Generated embedding of shape: {embedding.shape}")

                # Store in MongoDB
                doc = {
                    'email': email,
                    'message_id': msg['id'],
                    'subject': subject,
                    'embedding': embedding.tolist(),
                    'timestamp': datetime.datetime.utcnow()
                }
                db.test_collection.insert_one(doc)
                logger.info(f"✅ Stored in MongoDB for {email}")

                # Upload test file to R2
                test_key = f"test/{email}/{msg['id']}.txt"
                r2_client.put_object(
                    Bucket=config['r2']['bucket'],
                    Key=test_key,
                    Body=subject.encode()
                )
                logger.info(f"✅ Uploaded to R2 for {email}")

                # Write to Google Sheets
                sheets.spreadsheets().values().append(
                    spreadsheetId=config['google_sheets']['spreadsheet_id'],
                    range=f"{config['google_sheets']['sheet_name']}!A1",
                    valueInputOption="RAW",
                    body={"values": [[email, subject, str(embedding.shape), datetime.datetime.utcnow().isoformat()]]}
                ).execute()
                logger.info(f"✅ Written to Google Sheets for {email}")

        logger.info("🎉 End-to-end test completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ End-to-end test failed: {e}")
        return False

if __name__ == "__main__":
    test_end_to_end() 
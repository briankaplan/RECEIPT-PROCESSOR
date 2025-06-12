#!/usr/bin/env python3
"""
Expense Processor Module
Main module for processing and matching expenses
"""

import asyncio
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import os
import mimetypes

import pandas as pd
from motor.motor_asyncio import AsyncIOMotorClient
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pymongo import MongoClient

from gmail_utils import GmailManager
from merchant_intelligence import MerchantIntelligenceSystem
from sheet_writer import ultra_robust_google_sheets_writer
from mongo_writer import EnhancedMongoWriter
from attachment_handler_fix import EnhancedAttachmentHandler

class ExpenseProcessor:
    def __init__(self, config_path: str):
        """Initialize expense processor"""
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # Initialize components
        self.gmail = None
        self.mongo = None
        self.merchant_intelligence = None
        self.attachment_handler = EnhancedAttachmentHandler()
        
        # Load credentials
        self.gmail_creds = None
        self.sheets_creds = None
        
        logging.info("Expense processor initialized")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load config: {e}")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config.get('logging', {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': 'expense_processor.log'
        })
        logging.basicConfig(
            level=getattr(logging, log_config['level']),
            format=log_config['format'],
            filename=log_config['file']
        )
    
    async def initialize(self):
        """Initialize all components"""
        try:
            # Initialize Gmail for all accounts
            self.gmail = {}
            for email, account in self.config['gmail'].items():
                if isinstance(account, dict):
                    account['email'] = email
                    manager = GmailManager(account['email'], account['token_file'])
                    if not await manager.initialize():
                        raise Exception(f"Failed to initialize Gmail for {email}")
                    self.gmail[email] = manager
                else:
                    print(f"WARNING: account for {email} is not a dict: {account} (type: {type(account)})")
            
            # Initialize MongoDB - Use the same pattern as working system test
            try:
                # Test connection with MongoClient first (this works in system test)
                test_client = MongoClient(self.config['mongodb']['uri'], serverSelectionTimeoutMS=5000)
                test_client.server_info()  # Force connection - this works in system test
                
                # Then initialize the EnhancedMongoWriter with the full config
                self.mongo = EnhancedMongoWriter(self.config)
                if not await self.mongo.initialize():
                    raise Exception("Failed to initialize MongoDB writer")
            except Exception as e:
                raise Exception(f"Failed to initialize MongoDB: {e}")
                
            # Initialize merchant intelligence
            self.merchant_intelligence = MerchantIntelligenceSystem()
            logging.info("All components initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize components: {e}")
            raise
    
    async def process_receipts(self):
        """Process receipts from Gmail"""
        try:
            total_messages = 0
            # Search for receipt emails in each Gmail account
            for email, gmail_manager in self.gmail.items():
                try:
                    # Search for receipt emails
                    query = "has:attachment (receipt OR invoice)"
                    messages = await gmail_manager.search_messages(query)
                    
                    for message in messages:
                        try:
                            # Extract receipt details
                            subject = gmail_manager.get_message_subject(message)
                            date = gmail_manager.get_message_date(message)
                            body = gmail_manager.get_message_body(message)
                            
                            # Process attachments
                            attachments = gmail_manager.get_message_attachments(message)
                            for attachment in attachments:
                                # Download attachment
                                data = await gmail_manager.download_attachment(
                                    message['id'],
                                    attachment['id']
                                )
                                if data:
                                    # Download and process attachment
                                    attachment_info = await self.attachment_handler.download_attachment_enhanced(
                                        gmail_manager.service,
                                        message['id'],
                                        attachment['id'],
                                        attachment['filename']
                                    )
                                    
                                    if attachment_info and attachment_info.is_safe:
                                        # Upload to R2
                                        r2_url = await self.upload_to_r2(
                                            attachment_info.file_path,
                                            f"receipts/{attachment_info.safe_filename}"
                                        )
                                        
                                        if r2_url:
                                            # Store receipt in MongoDB with R2 URL
                                            receipt = {
                                                'message_id': message['id'],
                                                'gmail_account': email,
                                                'subject': subject,
                                                'date': date,
                                                'body': body,
                                                'attachment': {
                                                    'filename': attachment_info.original_filename,
                                                    'r2_url': r2_url,
                                                    'mime_type': attachment_info.mime_type,
                                                    'size': attachment_info.file_size,
                                                    'hash': attachment_info.file_hash
                                                },
                                                'processed': False,
                                                'created_at': datetime.utcnow()
                                            }
                                            await self.mongo.collections['receipts'].insert_one(receipt)
                                            
                                            # Clean up local file after successful upload
                                            try:
                                                os.remove(attachment_info.file_path)
                                            except Exception as e:
                                                logging.warning(f"Failed to remove local file {attachment_info.file_path}: {e}")
                        
                        except Exception as e:
                            logging.error(f"Failed to process message {message['id']}: {e}")
                    
                    total_messages += len(messages)
                    
                except Exception as e:
                    logging.error(f"Failed to process Gmail account {email}: {e}")
            
            logging.info(f"Processed {total_messages} receipt messages across all accounts")
            
        except Exception as e:
            logging.error(f"Failed to process receipts: {e}")
            raise
    
    async def upload_to_r2(self, file_path: str, key: str) -> Optional[str]:
        """Upload file to R2 and return the URL"""
        try:
            import boto3
            from botocore.config import Config
            
            # Initialize R2 client
            s3 = boto3.client(
                's3',
                endpoint_url=self.config['r2']['endpoint'],
                aws_access_key_id=self.config['r2']['access_key_id'],
                aws_secret_access_key=self.config['r2']['secret_access_key'],
                config=Config(signature_version='s3v4'),
                region_name='auto'
            )
            
            # Upload file
            with open(file_path, 'rb') as f:
                s3.upload_fileobj(
                    f,
                    self.config['r2']['bucket'],
                    key,
                    ExtraArgs={
                        'ContentType': mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
                    }
                )
            
            # Generate URL
            url = f"{self.config['r2']['public_url']}/{key}"
            logging.info(f"Uploaded file to R2: {url}")
            return url
            
        except Exception as e:
            logging.error(f"Failed to upload to R2: {e}")
            return None
    
    async def match_transactions(self):
        """Match transactions with receipts"""
        try:
            # Get unprocessed receipts
            receipts = await self.mongo.collections['receipts'].find({'processed': False}).to_list(length=None)
            
            # Get transactions
            transactions = await self.mongo.collections['transactions'].find({}).to_list(length=None)
            
            for receipt in receipts:
                try:
                    # Extract receipt details
                    merchant = receipt.get('merchant', '')
                    amount = receipt.get('amount', 0)
                    date = receipt.get('date')
                    
                    best_match = None
                    best_score = 0
                    
                    # Find best matching transaction
                    for transaction in transactions:
                        # Calculate similarity scores
                        merchant_score = self.merchant_intelligence.calculate_similarity(
                            merchant,
                            transaction.get('merchant', '')
                        )
                        
                        amount_score = self._calculate_amount_score(
                            amount,
                            transaction.get('amount', 0)
                        )
                        
                        date_score = self._calculate_date_score(
                            date,
                            transaction.get('date')
                        )
                        
                        # Calculate overall score
                        overall_score = (
                            merchant_score * self.config['matching']['merchant']['weight'] +
                            amount_score * self.config['matching']['amount']['weight'] +
                            date_score * self.config['matching']['date']['weight']
                        )
                        
                        if overall_score > best_score:
                            best_score = overall_score
                            best_match = transaction
                    
                    # If good match found, store it
                    if best_match and best_score >= self.config['matching']['merchant']['threshold']:
                        match = {
                            'receipt_id': receipt['_id'],
                            'transaction_id': best_match['_id'],
                            'score': best_score,
                            'matched_at': datetime.utcnow()
                        }
                        await self.mongo.collections['matches'].insert_one(match)
                        
                        # Mark receipt as processed
                        await self.mongo.collections['receipts'].update_one(
                            {'_id': receipt['_id']},
                            {'$set': {'processed': True}}
                        )
                    
                except Exception as e:
                    logging.error(f"Failed to match receipt {receipt['_id']}: {e}")
            
            logging.info(f"Matched {len(receipts)} receipts")
            
        except Exception as e:
            logging.error(f"Failed to match transactions: {e}")
            raise
    
    def _calculate_amount_score(self, receipt_amount: float, transaction_amount: float) -> float:
        """Calculate amount similarity score"""
        try:
            if receipt_amount == 0 or transaction_amount == 0:
                return 0
            
            diff = abs(receipt_amount - transaction_amount)
            tolerance = self.config['matching']['amount']['tolerance']
            
            if diff <= tolerance:
                return 1.0
            elif diff <= tolerance * 2:
                return 0.8
            elif diff <= tolerance * 3:
                return 0.5
            else:
                return 0.0
            
        except Exception as e:
            logging.error(f"Failed to calculate amount score: {e}")
            return 0
    
    def _calculate_date_score(self, receipt_date: str, transaction_date: str) -> float:
        """Calculate date similarity score"""
        try:
            if not receipt_date or not transaction_date:
                return 0
            
            # Parse dates
            receipt_dt = datetime.strptime(receipt_date, "%Y-%m-%d")
            transaction_dt = datetime.strptime(transaction_date, "%Y-%m-%d")
            
            # Calculate difference in days
            diff_days = abs((receipt_dt - transaction_dt).days)
            max_days = self.config['matching']['date']['max_days_diff']
            
            if diff_days == 0:
                return 1.0
            elif diff_days <= max_days:
                return 1.0 - (diff_days / max_days)
            else:
                return 0
            
        except Exception as e:
            logging.error(f"Failed to calculate date score: {e}")
            return 0
    
    async def export_to_sheets(self):
        """Export matched transactions to Google Sheets"""
        try:
            # Get all matches
            matches = await self.mongo.collections['matches'].find({}).to_list(length=None)
            
            # Prepare data for export
            data = []
            for match in matches:
                # Get receipt and transaction details
                receipt = await self.mongo.collections['receipts'].find_one({'_id': match['receipt_id']})
                transaction = await self.mongo.collections['transactions'].find_one({'_id': match['transaction_id']})
                
                if receipt and transaction:
                    row = {
                        'Date': transaction.get('date', ''),
                        'Merchant': transaction.get('merchant', ''),
                        'Amount': transaction.get('amount', 0),
                        'Category': transaction.get('category', ''),
                        'Receipt': receipt.get('subject', ''),
                        'Receipt URL': receipt.get('attachment', {}).get('r2_url', ''),
                        'Match Score': match.get('score', 0)
                    }
                    data.append(row)
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Export to Google Sheets
            await ultra_robust_google_sheets_writer(
                df,
                self.config['sheets']['spreadsheet_id'],
                self.config['sheets']['sheet_name']
            )
            
            logging.info(f"Exported {len(data)} matches to Google Sheets")
            
        except Exception as e:
            logging.error(f"Failed to export to sheets: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            # Clean up attachments
            await self.attachment_handler.cleanup_old_attachments(
                self.config['processing']['cleanup_after_days']
            )
            
            # Close MongoDB connection
            if self.mongo:
                await self.mongo.close()
            
            logging.info("Cleanup completed")
            
        except Exception as e:
            logging.error(f"Failed to cleanup: {e}")
            raise

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Process expenses from Gmail and match with transactions")
    parser.add_argument("--transactions", required=True, help="Path to transactions CSV file")
    parser.add_argument("--config", default="config/config.json", help="Path to config file")
    parser.add_argument("--export", action="store_true", help="Export results to Google Sheets")
    
    args = parser.parse_args()
    
    processor = ExpenseProcessor(args.config)
    await processor.initialize()  # Initialize components first
    await processor.process_receipts()  # Process receipts
    await processor.match_transactions()  # Match with transactions
    if args.export:
        await processor.export_to_sheets()  # Export if requested
    await processor.cleanup()  # Clean up resources

if __name__ == "__main__":
    asyncio.run(main()) 
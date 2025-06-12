#!/usr/bin/env python3
"""
Test System Module
Tests all components of the expense processor system
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Tuple
import pandas as pd
from rich.console import Console
from rich.table import Table

from expense_processor import ExpenseProcessor
from merchant_intelligence import MerchantIntelligenceSystem
from gmail_utils import GmailManager
from sheet_writer import ultra_robust_google_sheets_writer
from mongo_writer import EnhancedMongoWriter

class SystemTester:
    def __init__(self, config_path: str):
        """Initialize system tester"""
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.console = Console()
        
        # Initialize components
        self.processor = None
        self.gmail = None
        self.mongo = None
        self.merchant_intelligence = None
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load config: {e}")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config['logging']
        logging.basicConfig(
            level=getattr(logging, log_config['level']),
            format=log_config['format'],
            filename=log_config['file']
        )
    
    async def test_all_components(self) -> Dict[str, Tuple[bool, str]]:
        """Test all system components"""
        results = {}
        
        # Test configuration
        results['config'] = await self._test_config()
        
        # Test Gmail
        results['gmail'] = await self._test_gmail()
        
        # Test merchant intelligence
        results['merchant_intelligence'] = await self._test_merchant_intelligence()
        
        # Test HuggingFace
        results['huggingface'] = await self._test_huggingface()
        
        # Test MongoDB
        results['mongodb'] = await self._test_mongodb()
        
        # Test Google Sheets
        results['sheets'] = await self._test_sheets()
        
        # Test expense processor
        results['processor'] = await self._test_processor()
        
        return results
    
    async def _test_config(self) -> Tuple[bool, str]:
        """Test configuration loading"""
        try:
            required_sections = [
                'gmail', 'mongodb', 'sheets', 'ai',
                'matching', 'logging', 'processing'
            ]
            
            for section in required_sections:
                if section not in self.config:
                    return False, f"Missing section: {section}"
            
            return True, "Configuration loaded successfully"
            
        except Exception as e:
            return False, f"Configuration error: {e}"
    
    async def _test_gmail(self) -> Tuple[bool, str]:
        """Test Gmail integration for all accounts"""
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            import json
            import os

            accounts = self.config["gmail"]
            for email, account in accounts.items():
                if isinstance(account, dict):
                    account['email'] = email
                    client_file = account['client_file']
                    token_file = account['token_file']
                    if not os.path.exists(client_file):
                        return False, f"Client file missing: {client_file}"
                    if not os.path.exists(token_file):
                        return False, f"Token file missing: {token_file}"
                    from gmail_utils import GmailManager
                    manager = GmailManager(account["email"], token_file)
                    if not await manager.initialize():
                        return False, f"Failed to initialize Gmail for {email}"
                    messages = await manager.search_messages("has:attachment", max_results=1)
                    if not isinstance(messages, list):
                        return False, f"Gmail search did not return a list for {email}"
                else:
                    print(f"WARNING: account for {email} is not a dict: {account} (type: {type(account)})")
            return True, "Gmail integration working for all accounts"
        except Exception as e:
            return False, f"Gmail error: {e}"
    
    async def _test_merchant_intelligence(self) -> Tuple[bool, str]:
        """Test merchant intelligence system"""
        try:
            self.merchant_intelligence = MerchantIntelligenceSystem(self.config)
            
            # Test similarity calculation
            score = self.merchant_intelligence.calculate_similarity(
                "Starbucks",
                "Starbucks Coffee"
            )
            
            if score < 0.8:  # Should be a high match
                return False, "Low similarity score for known match"
            
            return True, "Merchant intelligence working"
            
        except Exception as e:
            return False, f"Merchant intelligence error: {e}"
    
    async def _test_huggingface(self) -> Tuple[bool, str]:
        """Test HuggingFace integration"""
        try:
            if not self.config['ai']['huggingface']['api_key']:
                return False, "No HuggingFace API key"
            
            # Test model loading
            from transformers import pipeline
            classifier = pipeline(
                "text-classification",
                model=self.config['ai']['huggingface']['model']
            )
            
            return True, "HuggingFace integration working"
            
        except Exception as e:
            return False, f"HuggingFace error: {e}"
    
    async def _test_mongodb(self) -> Tuple[bool, str]:
        """Test MongoDB connection"""
        try:
            from pymongo import MongoClient
            uri = self.config["mongodb"]["uri"]
            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            client.server_info()  # Force connection
            return True, "MongoDB connected successfully"
        except Exception as e:
            return False, f"MongoDB error: {e}"
    
    async def _test_sheets(self) -> Tuple[bool, str]:
        """Test Google Sheets integration"""
        try:
            # Create test data
            sheets_result = await ultra_robust_google_sheets_writer(
                [["Test", "Data", "Row"]],
                self.config
            )
            if not sheets_result:
                return False, "Failed to write to sheets"
            return True, "Google Sheets integration working"
        except Exception as e:
            return False, f"Google Sheets error: {str(e)}"
    
    async def _test_processor(self) -> Tuple[bool, str]:
        """Test expense processor"""
        try:
            if 'gmail' not in self.config or 'mongodb' not in self.config:
                return False, "Missing required config sections for processor test"
                
            self.processor = ExpenseProcessor("config/config_perfect.json")
            await self.processor.initialize()
            return True, "Processor initialized successfully"
        except Exception as e:
            return False, f"Processor error: {e}"
    
    def display_results(self, results: Dict[str, Tuple[bool, str]]):
        """Display test results"""
        table = Table(title="System Test Results")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="blue")
        
        for component, (success, message) in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            table.add_row(component, status, message)
        
        self.console.print(table)
        
        # Summary
        total = len(results)
        passed = sum(1 for success, _ in results.values() if success)
        self.console.print(f"\nSummary: {passed}/{total} components passed")

async def main():
    """Main function"""
    try:
        tester = SystemTester('expense_config.json')
        results = await tester.test_all_components()
        tester.display_results(results)
        
    except Exception as e:
        logging.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 
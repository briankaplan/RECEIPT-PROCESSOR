import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
import gspread
from google.oauth2.service_account import Credentials
import json

logger = logging.getLogger(__name__)

class GoogleSheetsClient:
    """Google Sheets client for exporting receipt and bank matching data"""
    
    def __init__(self):
        self.client = None
        self.credentials = None
        self._connect()
    
    def _connect(self):
        """Connect to Google Sheets API"""
        try:
            # Get service account credentials from environment
            creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            
            if not creds_json:
                logger.warning("Google Sheets credentials not found in environment variables")
                return False
            
            # Parse credentials
            creds_data = json.loads(creds_json)
            
            # Create credentials object
            self.credentials = Credentials.from_service_account_info(
                creds_data,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
            
            # Create gspread client
            self.client = gspread.authorize(self.credentials)
            
            logger.info("Connected to Google Sheets API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {str(e)}")
            self.client = None
            return False
    
    def is_connected(self) -> bool:
        """Check if Google Sheets is connected"""
        return self.client is not None
    
    def create_or_get_spreadsheet(self, title: str) -> Optional[gspread.Spreadsheet]:
        """Create a new spreadsheet or get existing one"""
        if not self.is_connected():
            logger.error("Google Sheets not connected")
            return None
        
        try:
            # Try to open existing spreadsheet
            try:
                spreadsheet = self.client.open(title)
                logger.info(f"Opened existing spreadsheet: {title}")
                return spreadsheet
            except gspread.SpreadsheetNotFound:
                # Create new spreadsheet
                spreadsheet = self.client.create(title)
                logger.info(f"Created new spreadsheet: {title}")
                return spreadsheet
                
        except Exception as e:
            logger.error(f"Error creating/opening spreadsheet: {str(e)}")
            return None
    
    def export_receipts_to_sheet(self, receipts: List[Dict], spreadsheet_title: str = "Gmail Receipts Export") -> bool:
        """Export receipts data to Google Sheets"""
        if not self.is_connected():
            logger.error("Google Sheets not connected")
            return False
        
        if not receipts:
            logger.warning("No receipts to export")
            return False
        
        try:
            # Create or get spreadsheet
            spreadsheet = self.create_or_get_spreadsheet(spreadsheet_title)
            if not spreadsheet:
                return False
            
            # Create or get receipts worksheet
            try:
                worksheet = spreadsheet.worksheet("Receipts")
                worksheet.clear()
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title="Receipts", rows=1000, cols=15)
            
            # Prepare headers
            headers = [
                'Email ID', 'Account', 'Merchant', 'Date', 'Total Amount',
                'Payment Method', 'Source File', 'Tax Amount', 'Items Count',
                'Processed At', 'Raw Text Preview'
            ]
            
            # Prepare data rows
            rows = [headers]
            
            for receipt in receipts:
                receipt_data = receipt.get('receipt_data', {})
                items_count = len(receipt_data.get('items', []))
                raw_text_preview = (receipt_data.get('raw_text', '')[:100] + '...') if receipt_data.get('raw_text') else ''
                
                row = [
                    receipt.get('email_id', ''),
                    receipt.get('account', ''),
                    receipt_data.get('merchant', ''),
                    receipt_data.get('date', ''),
                    receipt_data.get('total_amount', ''),
                    receipt_data.get('payment_method', ''),
                    receipt_data.get('source_file', ''),
                    receipt_data.get('tax_amount', ''),
                    items_count,
                    receipt.get('processed_at', ''),
                    raw_text_preview
                ]
                rows.append(row)
            
            # Update worksheet
            worksheet.update('A1', rows)
            
            # Format headers
            worksheet.format('A1:K1', {
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 1.0},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            
            # Auto-resize columns
            worksheet.columns_auto_resize(0, len(headers) - 1)
            
            logger.info(f"Exported {len(receipts)} receipts to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting receipts to sheets: {str(e)}")
            return False
    
    def export_bank_matches_to_sheet(self, matches_data: List[Dict], spreadsheet_title: str = "Bank Statement Matches") -> bool:
        """Export bank statement matches to Google Sheets"""
        if not self.is_connected():
            logger.error("Google Sheets not connected")
            return False
        
        if not matches_data:
            logger.warning("No matches data to export")
            return False
        
        try:
            # Create or get spreadsheet
            spreadsheet = self.create_or_get_spreadsheet(spreadsheet_title)
            if not spreadsheet:
                return False
            
            # Create or get matches worksheet
            try:
                worksheet = spreadsheet.worksheet("Matches")
                worksheet.clear()
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title="Matches", rows=1000, cols=12)
            
            # Prepare headers
            headers = [
                'Receipt Email ID', 'Receipt Account', 'Receipt Merchant', 'Receipt Date',
                'Receipt Amount', 'Bank Description', 'Bank Date', 'Bank Amount',
                'Match Confidence', 'Match Reasons', 'Status'
            ]
            
            # Prepare data rows
            rows = [headers]
            
            for match_data in matches_data:
                receipt_data = match_data.get('receipt_data', {})
                matches = match_data.get('matches', [])
                
                if not matches:
                    # Add row for receipt with no matches
                    row = [
                        match_data.get('email_id', ''),
                        match_data.get('account', ''),
                        receipt_data.get('merchant', ''),
                        receipt_data.get('date', ''),
                        receipt_data.get('total_amount', ''),
                        '', '', '', '', '', 'No Match'
                    ]
                    rows.append(row)
                else:
                    # Add row for each match
                    for match in matches:
                        transaction = match.get('transaction', {})
                        confidence = match.get('confidence', 0)
                        reasons = ', '.join(match.get('match_reasons', []))
                        
                        row = [
                            match_data.get('email_id', ''),
                            match_data.get('account', ''),
                            receipt_data.get('merchant', ''),
                            receipt_data.get('date', ''),
                            receipt_data.get('total_amount', ''),
                            transaction.get('description', ''),
                            transaction.get('date', ''),
                            transaction.get('amount', ''),
                            f"{confidence:.1%}",
                            reasons,
                            'High Confidence' if confidence > 0.8 else 'Medium Confidence' if confidence > 0.6 else 'Low Confidence'
                        ]
                        rows.append(row)
            
            # Update worksheet
            worksheet.update('A1', rows)
            
            # Format headers
            worksheet.format('A1:K1', {
                'backgroundColor': {'red': 0.2, 'green': 0.8, 'blue': 0.2},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            
            # Auto-resize columns
            worksheet.columns_auto_resize(0, len(headers) - 1)
            
            logger.info(f"Exported {len(rows) - 1} match records to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting matches to sheets: {str(e)}")
            return False
    
    def create_summary_sheet(self, stats: Dict, spreadsheet_title: str = "Receipt Processing Summary") -> bool:
        """Create a summary sheet with processing statistics"""
        if not self.is_connected():
            logger.error("Google Sheets not connected")
            return False
        
        try:
            # Create or get spreadsheet
            spreadsheet = self.create_or_get_spreadsheet(spreadsheet_title)
            if not spreadsheet:
                return False
            
            # Create or get summary worksheet
            try:
                worksheet = spreadsheet.worksheet("Summary")
                worksheet.clear()
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title="Summary", rows=100, cols=5)
            
            # Prepare summary data
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            summary_data = [
                ['Gmail Receipt Processing Summary', '', '', ''],
                ['Generated on:', current_time, '', ''],
                ['', '', '', ''],
                ['Processing Statistics', '', '', ''],
                ['Total Receipts Processed:', stats.get('receipts_count', 0), '', ''],
                ['Total Bank Statements:', stats.get('bank_statements_count', 0), '', ''],
                ['Processed Emails:', stats.get('processed_emails_count', 0), '', ''],
                ['Failed Emails:', stats.get('failed_emails_count', 0), '', ''],
                ['', '', '', ''],
                ['Gmail Accounts', '', '', ''],
            ]
            
            # Add account information
            account_stats = stats.get('account_stats', {})
            for account, account_info in account_stats.items():
                status = 'Connected' if account_info.get('authenticated', False) else 'Not Connected'
                summary_data.append([account, status, '', ''])
            
            # Add storage information
            summary_data.extend([
                ['', '', '', ''],
                ['Storage Information', '', '', ''],
                ['MongoDB Connected:', 'Yes' if stats.get('mongo_connected', False) else 'No', '', ''],
                ['R2 Storage Connected:', 'Yes' if stats.get('r2_connected', False) else 'No', '', ''],
                ['Google Sheets Connected:', 'Yes' if self.is_connected() else 'No', '', ''],
            ])
            
            # Update worksheet
            worksheet.update('A1', summary_data)
            
            # Format title
            worksheet.format('A1', {
                'backgroundColor': {'red': 0.1, 'green': 0.1, 'blue': 0.8},
                'textFormat': {'bold': True, 'fontSize': 16, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            
            # Format section headers
            worksheet.format('A4', {'textFormat': {'bold': True}})
            worksheet.format('A10', {'textFormat': {'bold': True}})
            worksheet.format('A15', {'textFormat': {'bold': True}})
            
            # Auto-resize columns
            worksheet.columns_auto_resize(0, 3)
            
            logger.info("Created summary sheet")
            return True
            
        except Exception as e:
            logger.error(f"Error creating summary sheet: {str(e)}")
            return False
    
    def get_sheet_url(self, spreadsheet_title: str) -> Optional[str]:
        """Get the URL of a spreadsheet"""
        if not self.is_connected():
            return None
        
        try:
            spreadsheet = self.client.open(spreadsheet_title)
            return spreadsheet.url
        except Exception as e:
            logger.error(f"Error getting sheet URL: {str(e)}")
            return None
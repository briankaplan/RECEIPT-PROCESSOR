#!/usr/bin/env python3
"""
Google Sheets Sync - Synchronize expense data with Google Sheets
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd

class GoogleSheetsSync:
    """
    Synchronize expense data with Google Sheets for easy viewing and sharing
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.service = None
        self.spreadsheet_id = config.get('spreadsheet_id')
        self.sheet_name = config.get('sheet_name', 'Expenses')
        
        # Sync statistics
        self.sync_stats = {
            'last_sync': None,
            'records_synced': 0,
            'sync_errors': 0,
            'connection_status': 'disconnected'
        }
    
    async def initialize(self):
        """Initialize Google Sheets API connection"""
        
        try:
            # Load service account credentials
            creds_path = self.config.get('service_account_path', 'gmail_auth/service-account.json')
            
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            # Build the service
            self.service = build('sheets', 'v4', credentials=credentials)
            
            # Test connection
            await self._test_connection()
            
            self.sync_stats['connection_status'] = 'connected'
            logging.info(f"📊 Google Sheets sync initialized: {self.spreadsheet_id}")
            
        except Exception as e:
            logging.error(f"❌ Google Sheets sync initialization failed: {e}")
            raise
    
    async def _test_connection(self):
        """Test Google Sheets API connection"""
        
        try:
            # Get spreadsheet metadata
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            logging.info(f"✅ Connected to spreadsheet: {sheet_metadata.get('properties', {}).get('title', 'Unknown')}")
            
        except HttpError as e:
            if e.resp.status == 404:
                raise Exception(f"Spreadsheet not found: {self.spreadsheet_id}")
            elif e.resp.status == 403:
                raise Exception(f"Access denied to spreadsheet: {self.spreadsheet_id}")
            else:
                raise Exception(f"Google Sheets API error: {e}")
    
    async def sync_expenses(self, expenses: List[Dict]) -> bool:
        """
        Sync expense data to Google Sheets
        """
        
        if not expenses:
            logging.warning("⚠️ No expenses to sync")
            return False
        
        try:
            # Prepare data for sheets
            sheet_data = self._prepare_sheet_data(expenses)
            
            # Clear existing data
            await self._clear_sheet()
            
            # Write headers
            headers = [
                'Date', 'Merchant', 'Amount', 'Category', 'Subcategory',
                'Payment Method', 'Tax', 'Tip', 'Items', 'Location',
                'Gmail Account', 'Confidence', 'Status', 'Notes', 'Tags'
            ]
            
            # Combine headers and data
            all_data = [headers] + sheet_data
            
            # Write to sheet
            success = await self._write_to_sheet(all_data)
            
            if success:
                # Apply formatting
                await self._format_sheet(len(all_data))
                
                self.sync_stats['last_sync'] = datetime.now().isoformat()
                self.sync_stats['records_synced'] = len(expenses)
                
                logging.info(f"📊 Synced {len(expenses)} expenses to Google Sheets")
                return True
            else:
                self.sync_stats['sync_errors'] += 1
                return False
                
        except Exception as e:
            logging.error(f"❌ Sync to Google Sheets failed: {e}")
            self.sync_stats['sync_errors'] += 1
            return False
    
    def _prepare_sheet_data(self, expenses: List[Dict]) -> List[List[Any]]:
        """Prepare expense data for Google Sheets format"""
        
        sheet_data = []
        
        for expense in expenses:
            # Handle different data structures
            if hasattr(expense, '__dict__'):
                # ExpenseRecord object
                exp_dict = expense.__dict__
            else:
                # Dictionary
                exp_dict = expense
            
            # Extract items as string
            items = exp_dict.get('items', [])
            if isinstance(items, list):
                items_str = '; '.join(items)
            else:
                items_str = str(items) if items else ''
            
            # Extract tags as string
            tags = exp_dict.get('tags', [])
            if isinstance(tags, list):
                tags_str = ', '.join(tags)
            else:
                tags_str = str(tags) if tags else ''
            
            # Format amount
            amount = exp_dict.get('amount', 0)
            if isinstance(amount, (int, float)):
                amount_str = f"${amount:.2f}"
            else:
                amount_str = str(amount)
            
            # Format tax and tip
            tax_amount = exp_dict.get('tax_amount', 0)
            tip_amount = exp_dict.get('tip_amount', 0)
            
            row = [
                exp_dict.get('date', ''),
                exp_dict.get('merchant', ''),
                amount_str,
                exp_dict.get('category', ''),
                exp_dict.get('subcategory', ''),
                exp_dict.get('payment_method', ''),
                f"${tax_amount:.2f}" if isinstance(tax_amount, (int, float)) else str(tax_amount),
                f"${tip_amount:.2f}" if isinstance(tip_amount, (int, float)) else str(tip_amount),
                items_str,
                exp_dict.get('location', ''),
                exp_dict.get('gmail_account', ''),
                f"{exp_dict.get('confidence_score', 0):.2f}" if isinstance(exp_dict.get('confidence_score'), (int, float)) else '',
                exp_dict.get('status', ''),
                exp_dict.get('notes', ''),
                tags_str
            ]
            
            sheet_data.append(row)
        
        # Sort by date (newest first)
        sheet_data.sort(key=lambda x: x[0], reverse=True)
        
        return sheet_data
    
    async def _clear_sheet(self):
        """Clear existing data from the sheet"""
        
        try:
            # Get sheet properties to find the correct sheet ID
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            sheet_id = None
            for sheet in sheet_metadata['sheets']:
                if sheet['properties']['title'] == self.sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                # Create the sheet if it doesn't exist
                await self._create_sheet()
                return
            
            # Clear the sheet
            request = {
                'requests': [{
                    'updateCells': {
                        'range': {
                            'sheetId': sheet_id
                        },
                        'fields': 'userEnteredValue'
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=request
            ).execute()
            
        except Exception as e:
            logging.warning(f"⚠️ Failed to clear sheet: {e}")
    
    async def _create_sheet(self):
        """Create a new sheet if it doesn't exist"""
        
        try:
            request = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': self.sheet_name,
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': 15
                            }
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=request
            ).execute()
            
            logging.info(f"📄 Created new sheet: {self.sheet_name}")
            
        except Exception as e:
            logging.error(f"❌ Failed to create sheet: {e}")
            raise
    
    async def _write_to_sheet(self, data: List[List[Any]]) -> bool:
        """Write data to Google Sheets"""
        
        try:
            # Determine range
            num_rows = len(data)
            num_cols = len(data[0]) if data else 0
            range_name = f"{self.sheet_name}!A1:{chr(ord('A') + num_cols - 1)}{num_rows}"
            
            # Prepare the request
            body = {
                'values': data
            }
            
            # Write data
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            updated_cells = result.get('updatedCells', 0)
            logging.info(f"📝 Updated {updated_cells} cells in Google Sheets")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to write to sheet: {e}")
            return False
    
    async def _format_sheet(self, num_rows: int):
        """Apply formatting to the sheet"""
        
        try:
            # Get sheet ID
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            sheet_id = None
            for sheet in sheet_metadata['sheets']:
                if sheet['properties']['title'] == self.sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                return
            
            requests = []
            
            # Format header row
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.2,
                                'green': 0.6,
                                'blue': 0.9
                            },
                            'textFormat': {
                                'foregroundColor': {
                                    'red': 1.0,
                                    'green': 1.0,
                                    'blue': 1.0
                                },
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            })
            
            # Freeze header row
            requests.append({
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'gridProperties': {
                            'frozenRowCount': 1
                        }
                    },
                    'fields': 'gridProperties.frozenRowCount'
                }
            })
            
            # Auto-resize columns
            requests.append({
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 15
                    }
                }
            })
            
            # Apply alternating row colors
            requests.append({
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{
                            'sheetId': sheet_id,
                            'startRowIndex': 1,
                            'endRowIndex': num_rows
                        }],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=ISEVEN(ROW())'}]
                            },
                            'format': {
                                'backgroundColor': {
                                    'red': 0.95,
                                    'green': 0.95,
                                    'blue': 0.95
                                }
                            }
                        }
                    },
                    'index': 0
                }
            })
            
            # Execute formatting requests
            if requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': requests}
                ).execute()
                
                logging.info("🎨 Applied formatting to Google Sheets")
            
        except Exception as e:
            logging.warning(f"⚠️ Failed to format sheet: {e}")
    
    async def sync_summary_sheet(self, analytics: Dict):
        """Create a summary sheet with analytics"""
        
        try:
            summary_sheet_name = "Summary"
            
            # Prepare summary data
            summary_data = [
                ['Expense Summary', ''],
                ['', ''],
                ['Total Amount', f"${analytics.get('total_amount', 0):.2f}"],
                ['Total Transactions', str(analytics.get('total_count', 0))],
                ['Average Amount', f"${analytics.get('avg_amount', 0):.2f}"],
                ['Highest Amount', f"${analytics.get('max_amount', 0):.2f}"],
                ['Lowest Amount', f"${analytics.get('min_amount', 0):.2f}"],
                ['', ''],
                ['Top Categories', ''],
                ['', '']
            ]
            
            # Add category breakdown
            for item in analytics.get('category_breakdown', [])[:10]:
                summary_data.append([
                    item.get('_id', 'Unknown'),
                    f"${item.get('total', 0):.2f}"
                ])
            
            summary_data.extend([['', ''], ['Top Merchants', ''], ['', '']])
            
            # Add merchant breakdown
            for item in analytics.get('top_merchants', [])[:10]:
                summary_data.append([
                    item.get('_id', 'Unknown'),
                    f"${item.get('total', 0):.2f}"
                ])
            
            # Write to summary sheet
            range_name = f"{summary_sheet_name}!A1:B{len(summary_data)}"
            
            body = {
                'values': summary_data
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logging.info("📊 Updated summary sheet")
            
        except Exception as e:
            logging.warning(f"⚠️ Failed to create summary sheet: {e}")
    
    async def get_spreadsheet_url(self) -> str:
        """Get the public URL of the spreadsheet"""
        
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit"
    
    def get_sync_stats(self) -> Dict:
        """Get synchronization statistics"""
        
        return self.sync_stats.copy()
    
    async def backup_to_csv(self, filename: str = None) -> str:
        """Create a CSV backup of the sheet data"""
        
        try:
            if not filename:
                filename = f"expense_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # Read data from sheet
            range_name = f"{self.sheet_name}!A:O"  # All columns
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if values:
                # Convert to DataFrame and save as CSV
                df = pd.DataFrame(values[1:], columns=values[0])  # Skip header row
                df.to_csv(filename, index=False)
                
                logging.info(f"💾 Created CSV backup: {filename}")
                return filename
            else:
                logging.warning("⚠️ No data to backup")
                return ""
                
        except Exception as e:
            logging.error(f"❌ Backup failed: {e}")
            return ""

# Test the Google Sheets sync
if __name__ == "__main__":
    import asyncio
    
    async def test_google_sheets_sync():
        config = {
            "spreadsheet_id": "your-spreadsheet-id-here",
            "sheet_name": "Test Expenses",
            "service_account_path": "gmail_auth/service-account.json"
        }
        
        sync = GoogleSheetsSync(config)
        
        try:
            await sync.initialize()
            
            # Test data
            test_expenses = [
                {
                    'date': '2025-06-10',
                    'merchant': 'STARBUCKS',
                    'amount': 8.83,
                    'category': 'Food & Beverage',
                    'subcategory': 'Coffee',
                    'payment_method': 'CREDIT CARD',
                    'tax_amount': 0.73,
                    'tip_amount': 0.0,
                    'items': ['Grande Coffee', 'Muffin'],
                    'location': 'Nashville, TN',
                    'gmail_account': 'test@gmail.com',
                    'confidence_score': 0.95,
                    'status': 'processed',
                    'notes': 'Business meeting',
                    'tags': ['business', 'travel']
                }
            ]
            
            # Test sync
            success = await sync.sync_expenses(test_expenses)
            print(f"📊 Sync successful: {success}")
            
            # Test stats
            stats = sync.get_sync_stats()
            print(f"📈 Sync stats: {stats}")
            
            # Test URL
            url = await sync.get_spreadsheet_url()
            print(f"🔗 Spreadsheet URL: {url}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    # Note: This test requires valid Google Sheets credentials and spreadsheet ID
    print("📊 Google Sheets Sync Test")
    print("Note: Update spreadsheet_id and credentials path before running")
    # asyncio.run(test_google_sheets_sync())
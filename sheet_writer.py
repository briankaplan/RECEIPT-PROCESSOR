#!/usr/bin/env python3
"""
Enhanced Google Sheets Writer Module
Advanced Google Sheets operations with comprehensive features
"""

import logging
import pandas as pd
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, Dict, List, Any, Union
import asyncio
from datetime import datetime
import json
import time
from pathlib import Path

class EnhancedGoogleSheetsWriter:
    def __init__(self, config: Dict):
        """Initialize enhanced Google Sheets writer"""
        self.config = config
        self.service = None
        self.spreadsheet_id = None
        self.credentials = None
        
        # Performance tracking
        self.stats = {
            'cells_written': 0,
            'sheets_created': 0,
            'operations_completed': 0,
            'last_operation_time': None,
            'connection_status': 'disconnected'
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.request_interval = 0.1  # 100ms between requests
        
    async def initialize(self) -> bool:
        """Initialize Google Sheets service with comprehensive setup"""
        try:
            sheets_config = self.config.get('google_sheets', {})
            if not sheets_config:
                logging.error("❌ No Google Sheets configuration found")
                return False
            
            self.spreadsheet_id = sheets_config.get('spreadsheet_id')
            if not self.spreadsheet_id:
                logging.error("❌ No spreadsheet ID configured")
                return False
            
            # Load credentials (try service account first, then OAuth)
            if not await self._load_credentials():
                return False
            
            # Build service
            self.service = build('sheets', 'v4', credentials=self.credentials)
            
            # Test connection
            if not await self.test_connection():
                return False
            
            self.stats['connection_status'] = 'connected'
            logging.info(f"✅ Google Sheets writer initialized for spreadsheet: {self.spreadsheet_id}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Google Sheets initialization failed: {e}")
            return False
    
    async def _load_credentials(self) -> bool:
        """Load credentials with multiple methods"""
        sheets_config = self.config.get('google_sheets', {})
        
        # Method 1: Service Account (recommended for automated processing)
        service_account_path = self.config.get('service_account_path') or sheets_config.get('service_account_path')
        if service_account_path and Path(service_account_path).exists():
            try:
                self.credentials = service_account.Credentials.from_service_account_file(
                    service_account_path,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                logging.info("✅ Using service account credentials")
                return True
            except Exception as e:
                logging.warning(f"⚠️ Service account credentials failed: {e}")
        
        # Method 2: OAuth credentials from pickle file
        for account in self.config.get('gmail_accounts', []):
            pickle_file = account.get('pickle_file')
            if pickle_file and Path(pickle_file).exists():
                try:
                    import pickle
                    with open(pickle_file, 'rb') as token:
                        creds = pickle.load(token)
                    
                    # Check if credentials have Sheets scope
                    if creds and creds.valid:
                        self.credentials = creds
                        logging.info(f"✅ Using OAuth credentials from {pickle_file}")
                        return True
                except Exception as e:
                    logging.warning(f"⚠️ OAuth credentials failed: {e}")
        
        logging.error("❌ No valid credentials found for Google Sheets")
        return False
    
    async def test_connection(self) -> bool:
        """Test connection to Google Sheets"""
        try:
            await self._rate_limit()
            
            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            title = result.get('properties', {}).get('title', 'Unknown')
            logging.info(f"📊 Connected to spreadsheet: {title}")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                logging.error(f"❌ Spreadsheet not found: {self.spreadsheet_id}")
            elif e.resp.status == 403:
                logging.error(f"❌ Access denied to spreadsheet: {self.spreadsheet_id}")
            else:
                logging.error(f"❌ Google Sheets API error: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ Connection test failed: {e}")
            return False
    
    async def write_data_enhanced(self, data: Union[pd.DataFrame, List[Dict], List[List]], 
                                sheet_name: str = None, 
                                start_cell: str = "A1",
                                clear_existing: bool = True,
                                apply_formatting: bool = True) -> bool:
        """Enhanced data writing with multiple format support"""
        
        if not self.service:
            if not await self.initialize():
                return False
        
        try:
            # Use configured sheet name if not provided
            if not sheet_name:
                sheet_name = self.config.get('google_sheets', {}).get('sheet_name', 'Sheet1')
            
            # Convert data to list of lists format
            values = await self._prepare_data(data)
            if not values:
                logging.warning("⚠️ No data to write")
                return False
            
            # Ensure sheet exists
            await self._ensure_sheet_exists(sheet_name)
            
            # Clear existing data if requested
            if clear_existing:
                await self._clear_sheet(sheet_name)
            
            # Write data
            success = await self._write_values(sheet_name, start_cell, values)
            
            # Apply formatting if requested
            if success and apply_formatting:
                await self._apply_formatting(sheet_name, len(values), len(values[0]) if values else 0)
            
            if success:
                self.stats['cells_written'] += len(values) * (len(values[0]) if values else 0)
                self.stats['operations_completed'] += 1
                self.stats['last_operation_time'] = datetime.now()
                logging.info(f"✅ Successfully wrote {len(values)} rows to {sheet_name}")
            
            return success
            
        except Exception as e:
            logging.error(f"❌ Enhanced write failed: {e}")
            return False
    
    async def _prepare_data(self, data: Union[pd.DataFrame, List[Dict], List[List]]) -> List[List]:
        """Convert various data formats to list of lists"""
        
        if isinstance(data, pd.DataFrame):
            # DataFrame to list of lists
            values = [data.columns.tolist()]
            values.extend(data.values.tolist())
            return values
        
        elif isinstance(data, list) and data:
            if isinstance(data[0], dict):
                # List of dictionaries
                if not data:
                    return []
                
                headers = list(data[0].keys())
                values = [headers]
                
                for row in data:
                    row_values = []
                    for header in headers:
                        value = row.get(header, '')
                        # Convert various types to string
                        if value is None:
                            row_values.append('')
                        elif isinstance(value, (list, dict)):
                            row_values.append(str(value))
                        else:
                            row_values.append(str(value))
                    values.append(row_values)
                
                return values
                
            elif isinstance(data[0], list):
                # Already list of lists
                return data
            
            else:
                # List of other types
                return [[str(item)] for item in data]
        
        else:
            logging.error("❌ Unsupported data format")
            return []
    
    async def _ensure_sheet_exists(self, sheet_name: str) -> bool:
        """Ensure the specified sheet exists"""
        try:
            await self._rate_limit()
            
            # Get existing sheets
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
            
            if sheet_name not in existing_sheets:
                # Create new sheet
                await self._create_sheet(sheet_name)
                self.stats['sheets_created'] += 1
                logging.info(f"📄 Created new sheet: {sheet_name}")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Error ensuring sheet exists: {e}")
            return False
    
    async def _create_sheet(self, sheet_name: str):
        """Create a new sheet"""
        await self._rate_limit()
        
        request_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name,
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 26
                        }
                    }
                }
            }]
        }
        
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body=request_body
        ).execute()
    
    async def _clear_sheet(self, sheet_name: str):
        """Clear existing data from sheet"""
        try:
            await self._rate_limit()
            
            range_name = f"{sheet_name}!A:ZZ"
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
        except Exception as e:
            logging.warning(f"⚠️ Failed to clear sheet: {e}")
    
    async def _write_values(self, sheet_name: str, start_cell: str, values: List[List]) -> bool:
        """Write values to the sheet"""
        try:
            await self._rate_limit()
            
            # Determine range
            end_column = chr(ord('A') + len(values[0]) - 1) if values and values[0] else 'A'
            end_row = len(values)
            range_name = f"{sheet_name}!{start_cell}:{end_column}{end_row}"
            
            body = {
                'values': values,
                'majorDimension': 'ROWS'
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',  # Allows formulas and formatting
                body=body
            ).execute()
            
            updated_cells = result.get('updatedCells', 0)
            logging.info(f"📝 Updated {updated_cells} cells in range {range_name}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to write values: {e}")
            return False
    
    async def _apply_formatting(self, sheet_name: str, num_rows: int, num_cols: int):
        """Apply formatting to the sheet"""
        try:
            await self._rate_limit()
            
            # Get sheet ID
            sheet_id = await self._get_sheet_id(sheet_name)
            if sheet_id is None:
                return
            
            requests = []
            
            # Format header row
            if num_rows > 0:
                requests.append({
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': num_cols
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {
                                    'red': 0.2,
                                    'green': 0.6,
                                    'blue': 0.9
                                },
                                'textFormat': {
                                    'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},
                                    'bold': True,
                                    'fontSize': 11
                                },
                                'horizontalAlignment': 'CENTER'
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
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
                        'endIndex': num_cols
                    }
                }
            })
            
            # Apply alternating row colors
            if num_rows > 1:
                requests.append({
                    'addConditionalFormatRule': {
                        'rule': {
                            'ranges': [{
                                'sheetId': sheet_id,
                                'startRowIndex': 1,
                                'endRowIndex': num_rows,
                                'startColumnIndex': 0,
                                'endColumnIndex': num_cols
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
            
            # Execute formatting
            if requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': requests}
                ).execute()
                
                logging.info("🎨 Applied formatting to sheet")
            
        except Exception as e:
            logging.warning(f"⚠️ Failed to apply formatting: {e}")
    
    async def _get_sheet_id(self, sheet_name: str) -> Optional[int]:
        """Get the sheet ID for a given sheet name"""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            
            return None
            
        except Exception as e:
            logging.error(f"❌ Failed to get sheet ID: {e}")
            return None
    
    async def create_summary_sheet(self, analytics_data: Dict, sheet_name: str = "Summary") -> bool:
        """Create a summary sheet with analytics"""
        try:
            summary_data = [
                ['📊 Expense Summary', ''],
                ['', ''],
                ['Total Amount', f"${analytics_data.get('total_amount', 0):.2f}"],
                ['Total Transactions', str(analytics_data.get('total_count', 0))],
                ['Average Amount', f"${analytics_data.get('avg_amount', 0):.2f}"],
                ['Highest Amount', f"${analytics_data.get('max_amount', 0):.2f}"],
                ['Lowest Amount', f"${analytics_data.get('min_amount', 0):.2f}"],
                ['', ''],
                ['🏆 Top Categories', ''],
                ['', '']
            ]
            
            # Add category breakdown
            for item in analytics_data.get('category_breakdown', [])[:10]:
                summary_data.append([
                    item.get('_id', 'Unknown'),
                    f"${item.get('total', 0):.2f}"
                ])
            
            summary_data.extend([['', ''], ['🏪 Top Merchants', ''], ['', '']])
            
            # Add merchant breakdown
            for item in analytics_data.get('top_merchants', [])[:10]:
                summary_data.append([
                    item.get('_id', 'Unknown'),
                    f"${item.get('total', 0):.2f}"
                ])
            
            # Write summary data
            return await self.write_data_enhanced(
                data=summary_data,
                sheet_name=sheet_name,
                clear_existing=True,
                apply_formatting=True
            )
            
        except Exception as e:
            logging.error(f"❌ Failed to create summary sheet: {e}")
            return False
    
    async def append_data(self, data: Union[pd.DataFrame, List[Dict], List[List]], 
                         sheet_name: str = None) -> bool:
        """Append data to existing sheet without clearing"""
        
        if not self.service:
            if not await self.initialize():
                return False
        
        try:
            if not sheet_name:
                sheet_name = self.config.get('google_sheets', {}).get('sheet_name', 'Sheet1')
            
            # Convert data
            values = await self._prepare_data(data)
            if not values:
                return False
            
            # Skip header row for append
            if len(values) > 1:
                values = values[1:]
            
            await self._rate_limit()
            
            # Append data
            body = {'values': values}
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:A",
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            updates = result.get('updates', {})
            updated_cells = updates.get('updatedCells', 0)
            
            logging.info(f"📝 Appended {len(values)} rows ({updated_cells} cells)")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to append data: {e}")
            return False
    
    async def _rate_limit(self):
        """Implement rate limiting to avoid API quotas"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_interval:
            await asyncio.sleep(self.request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def get_spreadsheet_url(self) -> str:
        """Get the URL of the spreadsheet"""
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit"
    
    def get_stats(self) -> Dict:
        """Get writer statistics"""
        return {
            **self.stats,
            'spreadsheet_id': self.spreadsheet_id,
            'spreadsheet_url': self.get_spreadsheet_url() if self.spreadsheet_id else None
        }
    
    async def health_check(self) -> Dict:
        """Comprehensive health check"""
        health = {
            'status': 'unknown',
            'connection': False,
            'spreadsheet_accessible': False,
            'stats': self.get_stats(),
            'last_check': datetime.now().isoformat()
        }
        
        try:
            if await self.test_connection():
                health['connection'] = True
                health['spreadsheet_accessible'] = True
                health['status'] = 'healthy'
            else:
                health['status'] = 'unhealthy'
                
        except Exception as e:
            health['status'] = 'error'
            health['error'] = str(e)
        
        return health

# Integration helper for expense processor
async def save_to_enhanced_sheets(data: Union[pd.DataFrame, List[Dict]], config: Dict, 
                                 sheet_name: str = None, create_summary: bool = True) -> bool:
    """Helper function to save enhanced expense processor results to Google Sheets"""
    
    sheets_config = config.get('google_sheets', {})
    if not sheets_config.get('spreadsheet_id'):
        logging.info("ℹ️ Google Sheets not configured, skipping export")
        return True
    
    writer = EnhancedGoogleSheetsWriter(config)
    
    try:
        if not await writer.initialize():
            return False
        
        # Write main data
        success = await writer.write_data_enhanced(
            data=data,
            sheet_name=sheet_name or "Expense Matches",
            clear_existing=True,
            apply_formatting=True
        )
        
        if success:
            logging.info(f"✅ Data exported to Google Sheets: {writer.get_spreadsheet_url()}")
            
            # Create summary sheet if requested
            if create_summary and isinstance(data, (list, pd.DataFrame)):
                try:
                    # Generate summary analytics
                    if isinstance(data, list) and data:
                        df = pd.DataFrame(data)
                    elif isinstance(data, pd.DataFrame):
                        df = data
                    else:
                        df = None
                    
                    if df is not None and 'amount' in df.columns:
                        analytics = {
                            'total_amount': df['amount'].sum(),
                            'total_count': len(df),
                            'avg_amount': df['amount'].mean(),
                            'max_amount': df['amount'].max(),
                            'min_amount': df['amount'].min()
                        }
                        
                        await writer.create_summary_sheet(analytics)
                        
                except Exception as e:
                    logging.warning(f"⚠️ Failed to create summary sheet: {e}")
        
        return success
        
    except Exception as e:
        logging.error(f"❌ Google Sheets export failed: {e}")
        return False

# Legacy compatibility function
async def ultra_robust_google_sheets_writer(data: Any, config: Dict) -> bool:
    """Backward compatible function with enhanced features"""
    return await save_to_enhanced_sheets(data, config)

# Test the enhanced Google Sheets writer
if __name__ == "__main__":
    import asyncio
    
    async def test_sheets_writer():
        config = {
            "google_sheets": {
                "spreadsheet_id": "your-spreadsheet-id-here",
                "sheet_name": "Test Sheet"
            },
            "service_account_path": "path/to/service-account.json"
        }
        
        writer = EnhancedGoogleSheetsWriter(config)
        
        # Test initialization
        if await writer.initialize():
            print("✅ Google Sheets writer initialized")
            
            # Test health check
            health = await writer.health_check()
            print(f"🏥 Health check: {health}")
            
            # Test data writing
            test_data = [
                {'date': '2025-06-12', 'merchant': 'Test Store', 'amount': 25.99, 'category': 'Test'},
                {'date': '2025-06-12', 'merchant': 'Another Store', 'amount': 15.50, 'category': 'Test'}
            ]
            
            success = await writer.write_data_enhanced(
                data=test_data,
                sheet_name="Test Sheet",
                apply_formatting=True
            )
            
            print(f"📝 Write test: {'✅ Success' if success else '❌ Failed'}")
            
            if success:
                print(f"🔗 Spreadsheet URL: {writer.get_spreadsheet_url()}")
            
            # Test stats
            stats = writer.get_stats()
            print(f"📈 Stats: {stats}")
            
        else:
            print("❌ Google Sheets writer initialization failed")
    
    # Run test
    print("🧪 Testing Enhanced Google Sheets Writer")
    asyncio.run(test_sheets_writer())
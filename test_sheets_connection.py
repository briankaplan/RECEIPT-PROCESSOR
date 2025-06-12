#!/usr/bin/env python3
"""
Test Google Sheets Connection
Appends, reads, and deletes a test row in the configured Google Sheet
"""
import os
import json
import logging
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join('config', 'expense_config.json')


def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return None

def get_sheets_service(service_account_path, scopes):
    creds = Credentials.from_service_account_file(service_account_path, scopes=scopes)
    return build('sheets', 'v4', credentials=creds)

def test_sheets():
    config = load_config()
    if not config:
        return False
    sheets_cfg = config.get('google_sheets', {})
    spreadsheet_id = sheets_cfg.get('spreadsheet_id')
    sheet_name = sheets_cfg.get('sheet_name')
    service_account_path = config.get('service_account_path')
    if not (spreadsheet_id and sheet_name and service_account_path):
        logger.error("Google Sheets config incomplete")
        return False
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    try:
        service = get_sheets_service(service_account_path, scopes)
        sheet = service.spreadsheets()
        test_row = ["TEST_ROW", "This is a test", "✅"]
        range_ = f"{sheet_name}!A1:C1"
        # Append test row
        logger.info("Appending test row...")
        append_result = sheet.values().append(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption="RAW",
            body={"values": [test_row]}
        ).execute()
        logger.info(f"Append result: {append_result['updates']['updatedRange']}")
        # Read back the row
        logger.info("Reading back test row...")
        read_result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_
        ).execute()
        logger.info(f"Read result: {read_result.get('values')}")
        # Delete the test row (clear values)
        logger.info("Deleting test row...")
        clear_result = sheet.values().clear(
            spreadsheetId=spreadsheet_id,
            range=range_
        ).execute()
        logger.info(f"Clear result: {clear_result}")
        logger.info("🎉 Google Sheets test completed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Google Sheets test failed: {e}")
        return False

if __name__ == "__main__":
    test_sheets() 
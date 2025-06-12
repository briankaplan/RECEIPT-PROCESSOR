<<<<<<< HEAD
# Receipt Processor

An advanced expense processing system that automatically processes receipts from Gmail, matches them with transactions, and exports the results to Google Sheets.

## Features

- **Gmail Integration**: Automatically fetches and processes receipt emails from multiple Gmail accounts
- **R2 Storage**: Securely stores attachments in Cloudflare R2 with public URLs
- **MongoDB Integration**: Stores processed data with efficient querying capabilities
- **Google Sheets Export**: Exports matched transactions with receipt URLs
- **Merchant Intelligence**: Smart matching of receipts to transactions
- **HuggingFace Integration**: Advanced text processing and analysis
- **Vision Processing**: OCR capabilities for receipt images
- **Multi-Account Support**: Process receipts from multiple Gmail accounts
- **Automated Testing**: Comprehensive test suite for all components

## Prerequisites

- Python 3.11+
- MongoDB
- Cloudflare R2 Account
- Google Cloud Project with Gmail API enabled
- Google Sheets API access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/receipt-processor.git
cd receipt-processor
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up configuration:
- Copy `config/config_perfect.json.example` to `config/config_perfect.json`
- Update with your credentials and settings

## Configuration

The system requires several configuration files:

1. **Gmail Configuration**:
   - Client credentials for each Gmail account
   - Token files for authentication

2. **MongoDB Configuration**:
   - Connection URI
   - Database and collection names

3. **R2 Configuration**:
   - Endpoint URL
   - Access and secret keys
   - Bucket name
   - Public URL

4. **Google Sheets Configuration**:
   - Spreadsheet ID
   - Sheet name

## Usage

1. Authenticate Gmail accounts:
```bash
python3 auth_tool.py --setup
```

2. Process receipts:
```bash
python3 expense_processor.py --transactions bank_transactions.csv --config config/config_perfect.json
```

3. Run tests:
```bash
./run_all_tests.sh
```

## Project Structure

```
receipt-processor/
├── config/                 # Configuration files
├── gmail_auth/            # Gmail authentication
├── gmail_tokens/          # Gmail token storage
├── tests/                 # Test files
├── expense_processor.py   # Main processor
├── gmail_utils.py         # Gmail utilities
├── mongo_writer.py        # MongoDB operations
├── sheet_writer.py        # Google Sheets operations
└── README.md             # Documentation
```

## Testing

The project includes comprehensive tests:
- System tests
- End-to-end tests
- Integration tests
- Unit tests

Run all tests:
```bash
./run_all_tests.sh
```

## Security

- Credentials are stored securely
- R2 storage for attachments
- Secure MongoDB connection
- OAuth2 for Gmail authentication

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository. 
=======
# RECEIPT-PROCESSOR
>>>>>>> ccd7f3feee2087d9614a598559618c52abf6abc5

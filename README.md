# Receipt Processor

AI-powered receipt processing application with Gmail integration and banking automation.

## Features

- **Multi-Account Gmail Integration**: Process receipts from multiple Gmail accounts simultaneously
- **AI-Powered Analysis**: Advanced receipt categorization using OpenAI and HuggingFace
- **Banking Integration**: Live bank transaction feeds via Teller API
- **Intelligent Matching**: Automatic receipt-to-transaction matching
- **Cloud Storage**: Cloudflare R2 for secure file storage
- **Data Export**: Export to CSV and Google Sheets

## Quick Start

1. Install dependencies:
```bash
pip install -e .
```

2. Configure environment:
```bash
cp env.example .env
# Edit .env with your credentials
```

3. Set up security:
```bash
python setup_security.py
```

4. Run the application:
```bash
python app.py
```

5. Access dashboard at `http://localhost:5000`

## Services Configured

- ✅ Gmail API (3 accounts)
- ✅ MongoDB database
- ✅ Cloudflare R2 storage
- ✅ Google Vision API
- ✅ OpenAI API
- ✅ HuggingFace API
- ✅ Teller Banking API

## Security

All sensitive credentials are externalized to environment variables and secure credential files. See `SECURITY.md` for detailed configuration.

## License

MIT License 
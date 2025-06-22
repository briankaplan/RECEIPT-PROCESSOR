# Gmail Receipt Processor

## Overview

The Gmail Receipt Processor is a comprehensive Python web application that automatically processes email receipts from multiple Gmail accounts, extracts data using OCR (Optical Character Recognition), uses AI-powered categorization for intelligent expense classification, matches them with bank statement transactions, and exports results to Google Sheets. The application integrates with MongoDB for data persistence, Cloudflare R2 for file storage, Hugging Face AI for intelligent analysis, and provides a modern dashboard interface.

## System Architecture

The application follows a modular Flask-based architecture with cloud-native integrations:

- **Multi-Account Gmail Integration**: Supports 3 Gmail accounts with OAuth2 authentication
- **Cloud Storage**: MongoDB for structured data, Cloudflare R2 for file storage
- **Export Capabilities**: Google Sheets integration for data export and reporting
- **Microservices Design**: Separate clients for each external service
- **Fallback Mechanisms**: JSON file storage when cloud services are unavailable

## Key Components

### 1. Flask Web Application (`app.py`)
- **Purpose**: Main application entry point and route handling
- **Features**: Multi-service dashboard, API endpoints, comprehensive status monitoring
- **New Endpoints**: `/api/export_to_sheets` for Google Sheets export
- **Dependencies**: Flask framework with template rendering

### 2. Multi-Gmail Integration (`multi_gmail_client.py`)
- **Purpose**: Interface with Gmail API for multiple email accounts
- **Accounts**: kaplan.brian@gmail.com, brian@downhome.com, brian@musiccityrodeo.com
- **Authentication**: OAuth2 flow with individual token files per account
- **Token Storage**: Pickle files in `gmail_tokens/` directory
- **Fallback**: Graceful degradation when accounts are not authenticated

### 3. MongoDB Integration (`mongo_client.py`)
- **Purpose**: Primary data storage for receipts, bank statements, and processing history
- **Collections**: receipts, bank_statements, processed_emails
- **Features**: Automatic indexing, upsert operations, comprehensive statistics
- **Environment**: Requires MONGODB_URI and MONGODB_DATABASE variables

### 4. Cloudflare R2 Storage (`r2_client.py`)
- **Purpose**: File storage for receipt attachments and processed documents
- **Organization**: Structured file paths by account, date, and email ID
- **Features**: Automatic bucket creation, presigned URLs, metadata storage
- **Environment**: Requires R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME

### 5. Google Sheets Export (`sheets_client.py`)
- **Purpose**: Export receipt data and bank matches to Google Sheets
- **Features**: Automatic spreadsheet creation, formatted exports, summary reports
- **Authentication**: Service account credentials via GOOGLE_SHEETS_CREDENTIALS
- **Exports**: Receipt data, bank statement matches, processing summaries

### 6. Receipt Processing (`receipt_processor.py`)
- **Purpose**: Extract data from receipt images and PDFs using OCR
- **Technologies**: Tesseract OCR via pytesseract, PIL for image processing, PyPDF2 for PDF handling
- **File Detection**: Intelligent receipt file identification based on filename patterns and extensions
- **Supported Formats**: PDF, PNG, JPG, JPEG, GIF, BMP

### 7. Bank Statement Matching (`bank_matcher.py`)
- **Purpose**: Match extracted receipt data with bank statement transactions
- **Matching Logic**: Amount tolerance ($0.01), date tolerance (3 days), merchant name similarity
- **Confidence Scoring**: Algorithm to rank potential matches by confidence level
- **Fuzzy Matching**: Text similarity for merchant name matching

### 8. Hugging Face AI Integration (`huggingface_client.py`)
- **Purpose**: Intelligent receipt categorization and expense classification
- **Features**: Smart expense categorization, business purpose detection, tax deductibility analysis
- **Models**: Text classification for expense categories, merchant type analysis
- **Categories**: Office Supplies, Travel, Meals & Entertainment, Professional Services, etc.
- **Analysis**: Business context generation, confidence scoring, recommendations
- **Fallback**: Rule-based classification when AI is unavailable

### 9. Teller Bank Integration (`teller_client.py`)
- **Purpose**: Live bank transaction feeds with intelligent receipt matching
- **Features**: Real-time transaction access, historical data retrieval, automated receipt matching
- **Authentication**: SSL certificates with secure API connections
- **Capabilities**: Multi-account support, date range filtering, merchant similarity matching
- **Matching Logic**: Amount tolerance, date proximity, merchant name analysis, confidence scoring
- **UI Features**: Date selectors, account filtering, live transaction tables, match visualization

### 10. Google Photos Integration (`google_photos_client.py`)
- **Purpose**: Automatic receipt discovery from Google Photos
- **Features**: Photo search with receipt detection, intelligent image filtering, batch processing
- **Detection**: Receipt keywords, aspect ratio analysis, date-based filtering
- **Processing**: Automatic download, OCR processing, AI categorization integration
- **Authentication**: OAuth2 with Photos API access

### 11. URL Extraction System (`url_extractor.py`)
- **Purpose**: Extract and download receipts from URLs found in emails
- **Features**: Pattern matching for receipt URLs, automatic file download, content type detection
- **Domains**: Support for major receipt hosting services (Uber, Lyft, PayPal, etc.)
- **Processing**: Smart file extension detection, receipt validation, OCR integration
- **Automation**: Email content scanning, bulk URL processing

### 12. Camera Scanner Interface (`camera_scanner.py`)
- **Purpose**: Mobile-friendly receipt capture and batch photo upload
- **Features**: Real-time camera access, photo optimization for OCR, batch file processing
- **Camera**: Front/back camera selection, live preview, capture/retake functionality
- **Upload**: Multi-file selection, preview generation, size validation (10MB limit)
- **Processing**: Image optimization, format conversion, intelligent cropping

### 13. Enhanced MongoDB Schema
- **Export Fields**: ID, Date of Transaction, Merchant, Price, Description (auto), Receipt URL, Gmail ID, Gmail link to email, Match Status, Receipt Status, Category, Account, Is Subscription, Business
- **Auto Classification**: Business type detection (Personal, Music City Rodeo, Down Home)
- **Subscription Detection**: Intelligent identification of recurring services
- **Match Tracking**: Transaction matching status and confidence scoring
- **Source Tracking**: Gmail, Google Photos, camera capture, batch upload, URL extraction

### 14. Enhanced Frontend Interface
- **Technology**: Bootstrap 5 with custom CSS and JavaScript
- **Features**: Connection status indicators, multi-account support, AI status monitoring
- **New Cards**: Service connection status (MongoDB, R2, Google Sheets, AI Categorization)
- **AI Features**: Display of intelligent categorization capabilities
- **Icons**: Feather icons for consistent UI elements
- **AJAX**: Real-time status monitoring and asynchronous operations

## Data Flow

1. **Email Processing**: Multi-Gmail client retrieves emails with potential receipt attachments from 3 accounts
2. **File Filtering**: Receipt processor identifies relevant files based on patterns and extensions
3. **OCR Processing**: Text extraction from images and PDFs using Tesseract
4. **AI Analysis**: Hugging Face AI performs intelligent categorization and expense classification
5. **Data Enhancement**: AI adds business purpose, tax deductibility, and category confidence scores
6. **Cloud Storage**: Receipt files uploaded to Cloudflare R2 with organized structure
7. **Database Storage**: Enhanced receipt data saved to MongoDB with AI insights
8. **Bank Matching**: Compare receipt data against bank statement transactions
9. **Export Options**: Results exported to Google Sheets with comprehensive formatting
10. **Dashboard Update**: Frontend displays processing status, AI analysis, and results

## External Dependencies

### Google APIs
- **Gmail API**: Email access and attachment retrieval
- **OAuth2**: Authentication and authorization flow
- **Required Scopes**: `gmail.readonly` for safe email access

### OCR Services
- **Tesseract**: Open-source OCR engine for text extraction
- **System Dependencies**: freetype, lcms2, libimagequant, libjpeg, libtiff, libwebp, openjpeg

### Python Libraries
- **Flask**: Web framework and templating
- **PIL/Pillow**: Image processing and manipulation
- **PyPDF2**: PDF text extraction
- **Google API Client Libraries**: Gmail integration

## Deployment Strategy

### Development Environment
- **Platform**: Replit with Python 3.11 runtime
- **Auto-Install**: Dependency installation via pip during startup
- **Port**: Flask development server on port 5000
- **Hot Reload**: Automatic restart on code changes

### Production Considerations
- **Credentials**: Environment variables for OAuth2 tokens and API keys
- **File Storage**: Local JSON files (consider database migration for scale)
- **Security**: Secret key configuration and secure credential handling
- **Monitoring**: Application logging for debugging and monitoring

### File Structure
```
/
├── app.py                 # Main Flask application
├── gmail_client.py        # Gmail API integration
├── receipt_processor.py   # OCR and data extraction
├── bank_matcher.py        # Transaction matching logic
├── config.py              # Configuration management
├── templates/             # HTML templates
├── static/                # CSS, JS, and assets
├── data/                  # JSON data storage
└── downloads/             # Temporary file storage
```

## Changelog

- June 22, 2025: Initial setup with multi-Gmail integration, MongoDB, R2 storage, and Google Sheets
- June 22, 2025: Added Hugging Face AI integration for intelligent receipt categorization and expense classification
  - Implemented smart expense categorization with 12+ business categories
  - Added business purpose detection and tax deductibility analysis
  - Created merchant type classification and confidence scoring
  - Enhanced dashboard with AI connectivity status and features display
  - Integrated AI analysis into receipt processing workflow with fallback mechanisms

## User Preferences

Preferred communication style: Simple, everyday language.
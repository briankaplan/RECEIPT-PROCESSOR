#!/usr/bin/env python3
"""
Entry point for the Receipt Processor application
"""

import os
import sys
from app import create_app

def main():
    """Main application entry point"""
    # Set environment
    os.environ.setdefault('FLASK_ENV', 'development')
    
    # Create app with development configuration
    app = create_app('development')
    
    # Run the application
    port = int(os.environ.get('PORT', 10000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )

if __name__ == '__main__':
    main() 
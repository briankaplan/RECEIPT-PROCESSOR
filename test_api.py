#!/usr/bin/env python3

from app import create_app
import json

app = create_app()

with app.app_context():
    print("=== Testing API Directly ===")
    
    try:
        # Test transaction service directly
        result = app.transaction_service.get_transactions(page=1, page_size=3)
        print(f"Service result success: {result.get('success')}")
        print(f"Service result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Test JSON serialization
        try:
            json_str = json.dumps(result)
            print(f"JSON serialization successful, length: {len(json_str)}")
        except Exception as e:
            print(f"JSON serialization failed: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc() 
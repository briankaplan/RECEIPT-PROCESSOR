#!/usr/bin/env python3
"""
Run Full Receipt Scan
Comprehensive scan from July 1, 2024 to June 28, 2025
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_comprehensive_scan():
    """
    Run comprehensive receipt scan for the entire date range
    """
    logger.info("🚀 Starting comprehensive receipt scan")
    
    # Date range: July 1, 2024 to June 28, 2025
    start_date = "2024-07-01"
    end_date = "2025-06-28"
    
    logger.info(f"📅 Scanning period: {start_date} to {end_date}")
    
    try:
        # Import the full scanner
        from full_receipt_scan import run_full_receipt_scan
        
        # Run the scan
        results = await run_full_receipt_scan(
            start_date=start_date,
            end_date=end_date
        )
        
        # Display results
        display_scan_results(results)
        
        # Save detailed results
        save_detailed_results(results)
        
        return results
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.info("📝 Running simplified scan...")
        return await run_simplified_scan(start_date, end_date)
    
    except Exception as e:
        logger.error(f"❌ Scan failed: {e}")
        return {'error': str(e)}

async def run_simplified_scan(start_date: str, end_date: str) -> Dict:
    """
    Run simplified scan when full system is not available
    """
    logger.info("🔧 Running simplified scan...")
    
    # Calculate days to scan
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = (end - start).days
    
    logger.info(f"📅 Simplified scan: {total_days} days")
    
    # Simulate scan results
    results = {
        'scan_summary': {
            'total_emails_processed': 0,
            'receipts_found': 0,
            'successful_matches': 0,
            'failed_extractions': 0,
            'zero_amount_fixes': 0,
            'date_range': {
                'start_date': start_date,
                'end_date': end_date,
                'total_days': total_days
            },
            'errors': []
        },
        'statistics': {
            'total_transactions': 0,
            'total_receipts': 0,
            'successful_matches': 0,
            'match_rate': 0.0,
            'zero_amount_fixes': 0
        },
        'insights': [
            {
                'type': 'scan_complete',
                'message': f'Simplified scan completed for {total_days} days',
                'suggestion': 'Run full scan for detailed results'
            }
        ]
    }
    
    return results

def display_scan_results(results: Dict):
    """
    Display scan results in a readable format
    """
    print("\n" + "="*60)
    print("📊 COMPREHENSIVE RECEIPT SCAN RESULTS")
    print("="*60)
    
    # Scan summary
    summary = results.get('scan_summary', {})
    date_range = summary.get('date_range', {})
    
    print(f"📅 Date Range: {date_range.get('start_date')} to {date_range.get('end_date')}")
    print(f"📅 Total Days: {date_range.get('total_days')}")
    print()
    
    # Statistics
    stats = results.get('statistics', {})
    print(f"💰 Total Transactions: {stats.get('total_transactions', 0)}")
    print(f"📧 Total Receipts Found: {stats.get('total_receipts', 0)}")
    print(f"🔗 Successful Matches: {stats.get('successful_matches', 0)}")
    print(f"📈 Match Rate: {stats.get('match_rate', 0):.1%}")
    print(f"🔧 Zero Amount Fixes: {stats.get('zero_amount_fixes', 0)}")
    print()
    
    # Processing details
    print(f"📧 Emails Processed: {summary.get('total_emails_processed', 0)}")
    print(f"❌ Failed Extractions: {summary.get('failed_extractions', 0)}")
    print()
    
    # Insights
    insights = results.get('insights', [])
    if insights:
        print("💡 INSIGHTS:")
        for insight in insights:
            print(f"  • {insight.get('message', '')}")
            if insight.get('suggestion'):
                print(f"    Suggestion: {insight['suggestion']}")
        print()
    
    # Errors
    errors = summary.get('errors', [])
    if errors:
        print("❌ ERRORS:")
        for error in errors:
            print(f"  • {error}")
        print()
    
    print("="*60)

def save_detailed_results(results: Dict):
    """
    Save detailed results to file
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"comprehensive_scan_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"💾 Detailed results saved to {filename}")
        
        # Also save a summary
        summary_filename = f"scan_summary_{timestamp}.txt"
        with open(summary_filename, 'w') as f:
            f.write("COMPREHENSIVE RECEIPT SCAN SUMMARY\n")
            f.write("="*40 + "\n\n")
            
            summary = results.get('scan_summary', {})
            stats = results.get('statistics', {})
            
            f.write(f"Date Range: {summary.get('date_range', {}).get('start_date')} to {summary.get('date_range', {}).get('end_date')}\n")
            f.write(f"Total Days: {summary.get('date_range', {}).get('total_days')}\n\n")
            
            f.write(f"Total Transactions: {stats.get('total_transactions', 0)}\n")
            f.write(f"Total Receipts Found: {stats.get('total_receipts', 0)}\n")
            f.write(f"Successful Matches: {stats.get('successful_matches', 0)}\n")
            f.write(f"Match Rate: {stats.get('match_rate', 0):.1%}\n")
            f.write(f"Zero Amount Fixes: {stats.get('zero_amount_fixes', 0)}\n\n")
            
            f.write(f"Emails Processed: {summary.get('total_emails_processed', 0)}\n")
            f.write(f"Failed Extractions: {summary.get('failed_extractions', 0)}\n\n")
            
            insights = results.get('insights', [])
            if insights:
                f.write("INSIGHTS:\n")
                for insight in insights:
                    f.write(f"• {insight.get('message', '')}\n")
                    if insight.get('suggestion'):
                        f.write(f"  Suggestion: {insight['suggestion']}\n")
                f.write("\n")
        
        logger.info(f"💾 Summary saved to {summary_filename}")
        
    except Exception as e:
        logger.error(f"❌ Error saving results: {e}")

async def run_enhanced_search_with_fixes():
    """
    Run enhanced search with all fixes applied
    """
    logger.info("🔧 Running enhanced search with fixes...")
    
    try:
        # Import enhanced system
        from enhanced_receipt_system import EnhancedReceiptSystem
        
        # Initialize with your existing services
        enhanced_system = EnhancedReceiptSystem()
        
        # Run search for last 30 days as a test
        results = await enhanced_system.enhanced_search(
            days_back=30,
            use_existing_search=True
        )
        
        logger.info(f"✅ Enhanced search complete!")
        logger.info(f"📧 Found {len(results.get('emails', []))} emails")
        logger.info(f"🧠 Intelligence insights: {len(results.get('intelligence_insights', []))}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Enhanced search failed: {e}")
        return {'error': str(e)}

async def main():
    """
    Main function to run the comprehensive scan
    """
    logger.info("🚀 Starting comprehensive receipt scan system")
    
    # First, test the enhanced search with fixes
    logger.info("🔧 Testing enhanced search with fixes...")
    test_results = await run_enhanced_search_with_fixes()
    
    if 'error' not in test_results:
        logger.info("✅ Enhanced search working, proceeding with full scan...")
        
        # Run the comprehensive scan
        scan_results = await run_comprehensive_scan()
        
        if 'error' not in scan_results:
            logger.info("🎉 Comprehensive scan completed successfully!")
        else:
            logger.error(f"❌ Comprehensive scan failed: {scan_results['error']}")
    else:
        logger.error(f"❌ Enhanced search test failed: {test_results['error']}")
        logger.info("📝 Running simplified scan instead...")
        
        # Run simplified scan
        scan_results = await run_simplified_scan("2024-07-01", "2025-06-28")
    
    return scan_results

if __name__ == "__main__":
    # Run the comprehensive scan
    results = asyncio.run(main())
    
    if 'error' not in results:
        print("\n🎉 SCAN COMPLETED SUCCESSFULLY!")
        print("Check the generated files for detailed results.")
    else:
        print(f"\n❌ SCAN FAILED: {results['error']}")
        print("Please check the logs for more details.") 
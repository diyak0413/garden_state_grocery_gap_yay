#!/usr/bin/env python3
"""
Cache Build Progress Monitor
Tracks SearchAPI.io Walmart cache build toward all 734 NJ ZIP codes
"""

import sqlite3
import time
import datetime
import requests
import os

def get_cache_status():
    """Get current cache build status"""
    try:
        conn = sqlite3.connect('/app/data/walmart_cache.db')
        
        # Total ZIP codes processed
        cursor = conn.execute('SELECT COUNT(DISTINCT zip_code) FROM grocery_prices')
        total_zips = cursor.fetchone()[0]
        
        # Complete ZIP codes
        cursor = conn.execute('''
            SELECT COUNT(*)
            FROM (
                SELECT zip_code 
                FROM grocery_prices 
                GROUP BY zip_code 
                HAVING COUNT(*) = 8
            )
        ''')
        complete_zips = cursor.fetchone()[0]
        
        # Valid prices and API usage
        cursor = conn.execute('SELECT COUNT(*) FROM grocery_prices WHERE price != -1.0')
        valid_prices = cursor.fetchone()[0]
        
        cursor = conn.execute('SELECT call_count FROM api_usage ORDER BY last_updated DESC LIMIT 1')
        usage = cursor.fetchone()
        api_calls = usage[0] if usage else 0
        
        conn.close()
        
        return {
            'total_zips': total_zips,
            'complete_zips': complete_zips,
            'valid_prices': valid_prices,
            'api_calls': api_calls,
            'progress_pct': (complete_zips / 734) * 100,
            'quota_pct': (api_calls / 10000) * 100
        }
    except Exception as e:
        return {'error': str(e)}

def trigger_batch_if_needed():
    """Trigger new cache batch if needed"""
    try:
        response = requests.post(
            'http://localhost:8001/api/walmart/refresh-cache',
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return {'error': f'HTTP {response.status_code}'}
    except Exception as e:
        return {'error': str(e)}

def log_progress(status):
    """Log progress to file"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open('/app/cache_progress.log', 'a') as f:
        if 'error' in status:
            f.write(f"{timestamp} | ERROR: {status['error']}\n")
        else:
            f.write(f"{timestamp} | ZIP: {status['complete_zips']}/734 ({status['progress_pct']:.1f}%) | "
                   f"API: {status['api_calls']}/10K ({status['quota_pct']:.1f}%) | "
                   f"Valid: {status['valid_prices']:,}\n")

def main():
    """Main monitoring loop"""
    print("🚀 Starting Walmart Cache Build Monitor")
    print("Target: 734 NJ ZIP codes with SearchAPI.io pricing")
    print("="*60)
    
    # Initialize log
    with open('/app/cache_progress.log', 'w') as f:
        f.write("Cache Build Progress Log - Started at " + 
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n")
    
    last_complete = 0
    batch_interval = 300  # 5 minutes between auto-batches
    last_batch_time = 0
    
    while True:
        try:
            status = get_cache_status()
            log_progress(status)
            
            if 'error' not in status:
                complete = status['complete_zips']
                progress = status['progress_pct']
                
                print(f"Progress: {complete}/734 ZIP codes ({progress:.1f}%) | "
                      f"API: {status['api_calls']}/10K | Valid: {status['valid_prices']:,}")
                
                # Check if we've made progress
                if complete > last_complete:
                    print(f"✅ Progress! +{complete - last_complete} ZIP codes completed")
                    last_complete = complete
                
                # Auto-trigger batches every 5 minutes if progress is slow
                current_time = time.time()
                if current_time - last_batch_time > batch_interval:
                    if complete < 734:  # Not finished yet
                        print("🔄 Auto-triggering batch...")
                        batch_result = trigger_batch_if_needed()
                        if 'error' not in batch_result:
                            print("✅ Batch triggered successfully")
                        last_batch_time = current_time
                
                # Check completion
                if complete >= 734:
                    print("🎉 CACHE BUILD COMPLETE! All 734 ZIP codes processed!")
                    break
                elif progress >= 90:
                    print(f"🏆 Nearly complete! {progress:.1f}% done")
                elif complete >= 500:
                    print(f"🚀 Excellent progress! {complete} ZIP codes done")
            
            time.sleep(60)  # Check every minute
            
        except KeyboardInterrupt:
            print("\n⏸️ Monitor stopped by user")
            break
        except Exception as e:
            print(f"❌ Monitor error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
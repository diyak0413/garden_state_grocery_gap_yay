#!/usr/bin/env python3
"""
TURBO CACHE ACCELERATOR
Aggressively processes all remaining ZIP codes with maximum speed while maintaining quality
"""

import asyncio
import aiohttp
import sqlite3
import time
import json
from concurrent.futures import ThreadPoolExecutor

async def trigger_batch():
    """Trigger a single cache refresh batch"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://localhost:8001/api/walmart/refresh-cache',
                headers={'Content-Type': 'application/json'},
                timeout=120
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {'error': f'HTTP {response.status}'}
    except Exception as e:
        return {'error': str(e)}

def get_progress():
    """Get current cache progress"""
    try:
        conn = sqlite3.connect('/app/data/walmart_cache.db')
        cursor = conn.execute('SELECT COUNT(*) FROM (SELECT zip_code FROM grocery_prices GROUP BY zip_code HAVING COUNT(*) = 8)')
        complete = cursor.fetchone()[0]
        cursor = conn.execute('SELECT call_count FROM api_usage ORDER BY last_updated DESC LIMIT 1')
        usage = cursor.fetchone()
        api_calls = usage[0] if usage else 0
        conn.close()
        return complete, api_calls
    except:
        return 0, 0

async def turbo_acceleration():
    """Launch aggressive parallel batches"""
    print("🔥🔥 TURBO ACCELERATION MODE 🔥🔥")
    print("Target: Complete all 734 ZIP codes ASAP!")
    print("="*60)
    
    start_complete, start_calls = get_progress()
    start_time = time.time()
    
    print(f"Starting: {start_complete}/734 ZIP codes | {start_calls} API calls")
    
    # Launch 10 batches simultaneously every 30 seconds
    batch_count = 0
    while True:
        current_complete, current_calls = get_progress()
        progress_pct = (current_complete / 734) * 100
        elapsed = time.time() - start_time
        
        print(f"\nTime: {elapsed:.0f}s | Progress: {current_complete}/734 ({progress_pct:.1f}%) | API: {current_calls}")
        
        if current_complete >= 734:
            print("🎉 COMPLETE! All 734 ZIP codes processed!")
            break
            
        if current_complete >= 700:
            print("🏆 Nearly done! Final push...")
            batch_size = 5
        elif current_complete >= 600:
            print("🚀 Excellent progress! Maintaining speed...")
            batch_size = 8
        else:
            print("🔥 Full speed ahead!")
            batch_size = 10
        
        # Launch batch wave
        tasks = []
        for i in range(batch_size):
            task = asyncio.create_task(trigger_batch())
            tasks.append(task)
            batch_count += 1
        
        print(f"🚀 Launched {batch_size} batches (total: {batch_count})")
        
        # Wait for batches to complete or timeout
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=180)
            
            successful = 0
            for result in results:
                if isinstance(result, dict) and 'successful' in result:
                    successful += result.get('successful', 0)
            
            if successful > 0:
                print(f"✅ Batches completed: {successful} ZIP codes processed")
            
        except asyncio.TimeoutError:
            print("⏰ Batch timeout - continuing with next wave")
        
        # Brief pause before next wave
        await asyncio.sleep(10)
        
        # Safety check - don't run forever
        if elapsed > 3600:  # 1 hour max
            print("⏰ Time limit reached - stopping accelerator")
            break

if __name__ == "__main__":
    asyncio.run(turbo_acceleration())
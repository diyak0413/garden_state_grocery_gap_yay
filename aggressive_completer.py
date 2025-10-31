#!/usr/bin/env python3
"""
AGGRESSIVE CACHE COMPLETER - NO MORE DELAYS!
Complete ALL remaining ZIP codes in under 1 hour
"""

import asyncio
import aiohttp
import sqlite3
import time
import concurrent.futures

class AggressiveCompleter:
    def __init__(self):
        self.base_url = "http://localhost:8001/api/walmart/refresh-cache"
        self.max_concurrent = 50  # 50 parallel batches!
        
    async def trigger_batch(self, session, batch_id):
        """Trigger single batch with aggressive timeout"""
        try:
            async with session.post(
                self.base_url,
                headers={'Content-Type': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=60)  # 1 minute timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {'batch_id': batch_id, 'success': True, 'data': data}
                return {'batch_id': batch_id, 'success': False, 'error': f'HTTP {response.status}'}
        except Exception as e:
            return {'batch_id': batch_id, 'success': False, 'error': str(e)}
    
    def get_progress(self):
        """Get current completion status"""
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
    
    async def aggressive_completion(self):
        """Launch maximum speed completion"""
        print("🔥🔥🔥 AGGRESSIVE COMPLETION MODE 🔥🔥🔥")
        print("NO MORE DELAYS! COMPLETING ALL 734 ZIP CODES NOW!")
        print("="*70)
        
        start_complete, start_calls = self.get_progress()
        start_time = time.time()
        
        print(f"Starting: {start_complete}/734 ZIP codes | {start_calls} API calls")
        print(f"Target: Complete ALL {734 - start_complete} remaining ZIP codes in <1 hour")
        print()
        
        # Create persistent session
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=300)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            batch_wave = 1
            
            while True:
                current_complete, current_calls = self.get_progress()
                progress_pct = (current_complete / 734) * 100
                elapsed = time.time() - start_time
                rate = (current_complete - start_complete) / max(elapsed / 60, 1)  # per minute
                
                print(f"Wave {batch_wave} | {current_complete}/734 ({progress_pct:.1f}%) | "
                      f"Rate: {rate:.1f} ZIP/min | API: {current_calls:,}")
                
                if current_complete >= 734:
                    print("🎉 COMPLETE! All ZIP codes processed!")
                    break
                
                # Determine batch size based on remaining work
                remaining = 734 - current_complete
                if remaining > 200:
                    batch_size = 25  # Maximum aggressive
                elif remaining > 100:
                    batch_size = 20
                elif remaining > 50:
                    batch_size = 15
                else:
                    batch_size = 10  # Final push
                
                # Launch massive batch wave
                print(f"🚀 Launching {batch_size} parallel batches...")
                
                tasks = []
                for i in range(batch_size):
                    task = asyncio.create_task(
                        self.trigger_batch(session, f"{batch_wave}_{i}")
                    )
                    tasks.append(task)
                
                # Wait for wave completion with timeout
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=180  # 3 minutes max per wave
                    )
                    
                    successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
                    failed = len(results) - successful
                    
                    print(f"✅ Wave {batch_wave} complete: {successful} success, {failed} failed")
                    
                except asyncio.TimeoutError:
                    print(f"⚠️ Wave {batch_wave} timeout - continuing")
                
                batch_wave += 1
                
                # Very brief pause to prevent overwhelming
                await asyncio.sleep(2)
                
                # Safety check
                if elapsed > 3600:  # 1 hour absolute limit
                    print("⏰ 1 hour limit reached")
                    break
        
        # Final status
        final_complete, final_calls = self.get_progress()
        final_elapsed = time.time() - start_time
        
        print(f"\n🏁 AGGRESSIVE COMPLETION FINISHED")
        print(f"Final: {final_complete}/734 ZIP codes ({final_complete/734*100:.1f}%)")
        print(f"Added: {final_complete - start_complete} ZIP codes")
        print(f"Time: {final_elapsed/60:.1f} minutes")
        print(f"API calls: {final_calls:,}/10,000")

async def main():
    completer = AggressiveCompleter()
    await completer.aggressive_completion()

if __name__ == "__main__":
    asyncio.run(main())
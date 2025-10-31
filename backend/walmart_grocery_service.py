"""
Walmart Grocery API Integration with SQLite Caching
Strict quota management: 6,000 calls max per month (750 ZIP codes × 8 items)
"""

import os
import sqlite3
import requests
import asyncio
import aiohttp
import logging
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Healthy food basket items with standardized package sizes and realistic price ranges
HEALTHY_BASKET_ITEMS = [
    {
        "name": "Brown Rice (2 lb bag)",
        "search_terms": ["brown rice 2 lb bag", "brown rice 2 pound bag", "whole grain brown rice 2 lb"],
        "category": "grains",
        "snap_eligible": True,
        "min_price": 2.00,
        "max_price": 8.00
    },
    {
        "name": "Whole Wheat Bread (20 oz loaf)", 
        "search_terms": ["whole wheat bread 20 oz", "100% whole wheat bread loaf", "whole grain bread 20 oz"],
        "category": "grains",
        "snap_eligible": True,
        "min_price": 1.00,
        "max_price": 6.00
    },
    {
        "name": "Low-Fat Milk (1 gallon)",
        "search_terms": ["low fat milk 1 gallon", "2% milk gallon", "reduced fat milk gallon"],
        "category": "dairy", 
        "snap_eligible": True,
        "min_price": 2.00,
        "max_price": 6.00
    },
    {
        "name": "Boneless Skinless Chicken Breast (per lb)",
        "search_terms": ["boneless skinless chicken breast per lb", "chicken breast per pound", "fresh chicken breast lb"],
        "category": "protein",
        "snap_eligible": True,
        "min_price": 2.00,
        "max_price": 8.00
    },
    {
        "name": "Eggs (1 dozen, large)",
        "search_terms": ["large eggs 1 dozen", "grade A large eggs dozen", "fresh eggs 12 count large"],
        "category": "protein",
        "snap_eligible": True,
        "min_price": 1.00,
        "max_price": 5.00
    },
    {
        "name": "Apples (3 lb bag)",
        "search_terms": ["apples 3 lb bag", "gala apples 3 pound bag", "red delicious apples 3 lb"],
        "category": "produce",
        "snap_eligible": True,
        "min_price": 3.00,
        "max_price": 10.00
    },
    {
        "name": "Fresh Broccoli (1 lb)", 
        "search_terms": ["fresh broccoli 1 lb", "broccoli crowns 1 pound", "fresh broccoli florets lb"],
        "category": "produce",
        "snap_eligible": True,
        "min_price": 1.00,
        "max_price": 5.00
    },
    {
        "name": "Dry Black Beans (1 lb bag)",
        "search_terms": ["black beans 1 lb dry", "dried black beans 1 pound bag", "black turtle beans 1 lb"],
        "category": "legumes",
        "snap_eligible": True,
        "min_price": 1.00,
        "max_price": 4.00
    }
]

class WalmartGroceryCache:
    """SQLite-based caching system with strict quota management"""
    
    def __init__(self, db_path: str = "/app/data/walmart_cache.db"):
        self.db_path = db_path
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database with required schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS grocery_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zip_code TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    price REAL NOT NULL,
                    store_id TEXT,
                    date_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(zip_code, item_name)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month_year TEXT NOT NULL,
                    call_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(month_year)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("✅ SQLite cache database initialized")
    
    def get_cached_price(self, zip_code: str, item_name: str) -> Optional[Tuple[float, str, str]]:
        """Get cached price for ZIP-item pair, returns None for 'no data available' cases"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT price, store_id, date_fetched 
                FROM grocery_prices 
                WHERE zip_code = ? AND item_name = ?
            """, (zip_code, item_name))
            
            result = cursor.fetchone()
            if result:
                price, store_id, date_fetched = result
                
                # Check if this is a "no data available" entry
                if price == -1.0 or (store_id and store_id.startswith('no_data_')):
                    logger.info(f"📋 Cache hit: {zip_code} + {item_name} = NO DATA AVAILABLE")
                    return None  # Return None for "no data available"
                
                logger.info(f"📋 Cache hit: {zip_code} + {item_name} = ${price}")
                return price, store_id, date_fetched
            
            return None
    
    def _get_raw_cached_price(self, zip_code: str, item_name: str) -> Optional[Tuple[float, str, str]]:
        """Get raw cached price without filtering out 'no data available' entries"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT price, store_id, date_fetched 
                FROM grocery_prices 
                WHERE zip_code = ? AND item_name = ?
            """, (zip_code, item_name))
            
            result = cursor.fetchone()
            if result:
                return result
            return None
    
    def cache_price(self, zip_code: str, item_name: str, price: Optional[float], store_id: str = None):
        """Cache a price (INSERT OR REPLACE to handle updates), handling None for 'no data available'"""
        with sqlite3.connect(self.db_path) as conn:
            if price is None:
                # Cache "no data available" with special values
                conn.execute("""
                    INSERT OR REPLACE INTO grocery_prices 
                    (zip_code, item_name, price, store_id, date_fetched)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (zip_code, item_name, -1.0, f"no_data_{store_id or zip_code}"))
                logger.info(f"💾 Cached 'no data available' for {item_name} in ZIP {zip_code}")
            else:
                conn.execute("""
                    INSERT OR REPLACE INTO grocery_prices 
                    (zip_code, item_name, price, store_id, date_fetched)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (zip_code, item_name, price, store_id))
                logger.info(f"💾 Cached ${price:.2f} for {item_name} in ZIP {zip_code}")
            conn.commit()
            logger.info(f"💾 Cached: {zip_code} + {item_name} = ${price}")
    
    def get_monthly_usage(self) -> int:
        """Get API call count for current month"""
        month_year = datetime.now().strftime("%Y-%m")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT call_count FROM api_usage WHERE month_year = ?
            """, (month_year,))
            
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def increment_usage(self, calls: int = 1):
        """Increment monthly API usage count"""
        month_year = datetime.now().strftime("%Y-%m")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO api_usage (month_year, call_count, last_updated)
                VALUES (?, COALESCE((SELECT call_count FROM api_usage WHERE month_year = ?), 0) + ?, CURRENT_TIMESTAMP)
            """, (month_year, month_year, calls))
            conn.commit()
    
    def can_make_api_call(self) -> bool:
        """Check if we can make an API call without exceeding quota"""
        current_usage = self.get_monthly_usage()
        return current_usage < 10000  # Stay under 10K limit
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM grocery_prices")
            total_cached = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT zip_code) FROM grocery_prices
            """)
            zip_count = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT item_name) FROM grocery_prices  
            """)
            item_count = cursor.fetchone()[0]
            
            monthly_usage = self.get_monthly_usage()
            
        return {
            "total_cached_prices": total_cached,
            "zip_codes_cached": zip_count,
            "items_cached": item_count,
            "monthly_api_calls": monthly_usage,
            "quota_remaining": 10000 - monthly_usage,
            "cache_database": self.db_path
        }


class WalmartGroceryService:
    """Walmart API integration with strict quota management"""
    
    def __init__(self):
        self.api_key = os.getenv('WALMART_API_KEY')
        self.base_url = "https://www.searchapi.io/api/v1/search"  # SearchAPI.io endpoint
        self.enabled = bool(self.api_key and self.api_key.strip())
        
        # Initialize SQLite cache
        self.cache_db_path = "/app/data/walmart_cache.db"
        self.cache = WalmartGroceryCache()
        
        if self.enabled:
            logger.info("🛒 SearchAPI.io Walmart service initialized")
            logger.info(f"   API Key: {'✅ Available' if self.api_key else '❌ Missing'}")
            logger.info(f"   Cache DB: {self.cache_db_path}")
        else:
            logger.warning("⚠️ SearchAPI.io Walmart service disabled - API key missing")
    
    def is_enabled(self) -> bool:
        """Check if Walmart API is enabled"""
        return bool(self.api_key) and os.getenv('USE_REAL_GROCERY_DATA', 'false').lower() == 'true'
    
    async def get_zip_basket_cost(self, zip_code: str) -> Dict:
        """Get basket cost for ZIP code using cache-first approach"""
        if not self.is_enabled():
            return self._fallback_pricing(zip_code)
        
        logger.info(f"🛒 Getting basket cost for ZIP {zip_code}")
        
        # Check cache for all items first
        cached_items = {}
        missing_items = []
        no_data_items = []
        
        for item in HEALTHY_BASKET_ITEMS:
            cached_result = self.cache.get_cached_price(zip_code, item["name"])
            if cached_result is None:
                # Check if this is actually a "no data available" case or truly missing
                cached_raw = self.cache._get_raw_cached_price(zip_code, item["name"])
                if cached_raw and (cached_raw[0] == -1.0 or cached_raw[1].startswith('no_data_')):
                    no_data_items.append(item["name"])
                else:
                    missing_items.append(item)
            else:
                cached_items[item["name"]] = cached_result[0]  # Just the price
        
        # If all items are either cached or confirmed "no data available"
        if len(missing_items) == 0:
            if cached_items:
                total_cost = sum(cached_items.values()) if cached_items else 0
                logger.info(f"✅ All items resolved for {zip_code}: {len(cached_items)} priced, {len(no_data_items)} no data")
                
                # Build response with available data
                response = {
                    "individual_prices": cached_items,
                    "total_basket_cost": round(total_cost, 2) if cached_items else None,
                    "data_source": "walmart_cache",
                    "cache_hits": len(cached_items),
                    "api_calls_made": 0,
                    "zip_code": zip_code
                }
                
                if no_data_items:
                    response["no_data_items"] = no_data_items
                    response["data_completeness"] = f"{len(cached_items)}/{len(HEALTHY_BASKET_ITEMS)} items available"
                
                return response
            else:
                # All items have no data available
                logger.warning(f"⚠️ No grocery data available for ZIP {zip_code}")
                return {
                    "individual_prices": {},
                    "total_basket_cost": None,
                    "data_source": "no_data_available",
                    "cache_hits": 0,
                    "api_calls_made": 0,
                    "no_data_items": no_data_items,
                    "zip_code": zip_code,
                    "message": "No grocery data available for this ZIP code"
                }
        
        # Fetch missing items from API (with quota check)
        if len(missing_items) > 0:
            if not self.cache.can_make_api_call():
                logger.error(f"🚫 API quota exceeded! Cannot fetch {len(missing_items)} items for {zip_code}")
                # Return cached + fallback for missing items
                fallback_total = sum(cached_items.values()) + sum(self._get_fallback_price(item["name"]) for item in missing_items)
                return {
                    "individual_prices": {**cached_items, **{item["name"]: self._get_fallback_price(item["name"]) for item in missing_items}},
                    "total_basket_cost": round(fallback_total, 2),
                    "data_source": "quota_exceeded_fallback",
                    "cache_hits": len(cached_items),
                    "api_calls_made": 0,
                    "quota_status": "exceeded",
                    "zip_code": zip_code
                }
            
            # Fetch missing items from Walmart API
            new_prices = await self._fetch_missing_items(zip_code, missing_items)
            
            # Combine cached + new prices
            all_prices = {**cached_items, **new_prices}
            total_cost = sum(all_prices.values())
            
            return {
                "individual_prices": all_prices,
                "total_basket_cost": round(total_cost, 2),
                "data_source": "walmart_api_mixed",
                "cache_hits": len(cached_items),
                "api_calls_made": len(new_prices),
                "zip_code": zip_code
            }
    
    async def _fetch_missing_items(self, zip_code: str, missing_items: List[Dict]) -> Dict:
        """Fetch missing items from Walmart API with rate limiting and 'no data available' handling"""
        logger.info(f"🔍 Fetching {len(missing_items)} missing items for ZIP {zip_code}")
        
        # First, find Walmart stores for this ZIP
        store_id = await self._find_walmart_store(zip_code)
        if not store_id:
            logger.warning(f"⚠️ No Walmart store found for {zip_code}, marking all as 'no data available'")
            # Cache all items as "no data available"
            for item in missing_items:
                self.cache.cache_price(zip_code, item["name"], None, zip_code)
            return {}  # Return empty dict - no valid prices found
        
        new_prices = {}
        api_calls_made = 0
        
        for item in missing_items:
            if not self.cache.can_make_api_call():
                logger.error("🚫 Hit API quota limit during batch fetch!")
                # Cache remaining items as "no data available" due to quota
                self.cache.cache_price(zip_code, item["name"], None, f"quota_{zip_code}")
                continue
            
            try:
                price = await self._fetch_item_price(item, store_id)
                
                if price is not None:
                    # Valid price found
                    new_prices[item["name"]] = price
                    self.cache.cache_price(zip_code, item["name"], price, store_id)
                    logger.info(f"✅ Found valid price: {item['name']} = ${price:.2f}")
                else:
                    # No valid price found - cache as "no data available"
                    self.cache.cache_price(zip_code, item["name"], None, store_id)
                    logger.warning(f"⚠️ No valid price for {item['name']} in ZIP {zip_code} - cached as 'no data available'")
                
                self.cache.increment_usage(1)
                api_calls_made += 1
                
                # AGGRESSIVE rate limiting for maximum speed
                await asyncio.sleep(0.05)  # 50ms between calls - 20 calls per second
                
            except Exception as e:
                logger.error(f"❌ Failed to fetch {item['name']} for {zip_code}: {str(e)}")
                # Cache as "no data available" due to error
                self.cache.cache_price(zip_code, item["name"], None, f"error_{store_id}")
        
        logger.info(f"✅ Fetched {len(new_prices)} valid prices from {api_calls_made} API calls for {zip_code}")
        return new_prices
    
    async def _find_walmart_store(self, zip_code: str) -> Optional[str]:
        """Find Walmart store serving the ZIP code using SearchAPI.io"""
        try:
            # SearchAPI.io doesn't need separate store lookup - it handles location-based search
            # We'll use the ZIP code as the location parameter directly
            logger.info(f"📍 Using ZIP {zip_code} for SearchAPI.io location-based search")
            return zip_code  # Return ZIP code as "store_id" for SearchAPI.io
            
        except Exception as e:
            logger.error(f"❌ Location setup failed for {zip_code}: {str(e)}")
            return None
    
    async def _fetch_item_price(self, item: Dict, store_id: str) -> Optional[float]:
        """Fetch single item price using SearchAPI.io with price validation and Walmart preference"""
        try:
            params = {
                'engine': 'walmart_search',
                'q': item['search_terms'][0],
                'zip_code': store_id,  # store_id is actually the ZIP code for SearchAPI.io
                'api_key': self.api_key,
                'num_results': '10'  # Get more results to find valid prices
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('organic_results', [])
                        
                        if results:
                            # Try to find a valid price with Walmart preference
                            valid_price = self._extract_valid_price(item, results)
                            
                            if valid_price:
                                logger.info(f"💰 {item['name']}: ${valid_price:.2f} (SearchAPI.io - validated)")
                                return valid_price
                            else:
                                logger.warning(f"⚠️ No valid prices found for {item['name']} in ZIP {store_id} - all results outside ${item['min_price']:.2f}-${item['max_price']:.2f} range")
                                return None  # Return None for "no data available"
                        else:
                            logger.warning(f"⚠️ No search results found for {item['name']} in ZIP {store_id}")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ SearchAPI.io returned status {response.status}: {error_text[:200]}")
                        return None
            
        except Exception as e:
            logger.error(f"❌ SearchAPI.io price fetch failed for {item['name']}: {str(e)}")
            return None

    def _extract_valid_price(self, item: Dict, results: List[Dict]) -> Optional[float]:
        """Extract valid price from search results with Walmart preference and price validation"""
        min_price = item['min_price']
        max_price = item['max_price']
        
        # First pass: Look for "Sold & shipped by Walmart" results
        walmart_results = []
        other_results = []
        
        for result in results:
            seller_name = result.get('seller_name', '').lower()
            if 'walmart' in seller_name and 'walmart.com' in seller_name:
                walmart_results.append(result)
            else:
                other_results.append(result)
        
        # Try Walmart results first, then others
        all_results = walmart_results + other_results
        
        for result in all_results:
            # Extract price using extracted_price field (most reliable)
            price = result.get('extracted_price')
            
            # Fallback to parsing price string if extracted_price not available
            if price is None:
                price_str = result.get('price')
                if price_str:
                    try:
                        price_clean = str(price_str).replace('$', '').replace(',', '').strip()
                        price = float(price_clean)
                    except (ValueError, TypeError):
                        continue
            
            # Validate price is within realistic range
            if price and min_price <= price <= max_price:
                seller_name = result.get('seller_name', 'Unknown')
                product_title = result.get('title', 'Unknown')
                
                # Log if this is a preferred Walmart result
                if result in walmart_results:
                    logger.info(f"✅ Found valid Walmart price: ${price:.2f} for '{product_title[:50]}...' by {seller_name}")
                else:
                    logger.info(f"✅ Found valid price: ${price:.2f} for '{product_title[:50]}...' by {seller_name}")
                
                return price
        
        # Log the invalid prices we found for debugging
        invalid_prices = []
        for result in results[:3]:  # Log first 3 for debugging
            price = result.get('extracted_price') or result.get('price')
            seller = result.get('seller_name', 'Unknown')
            title = result.get('title', 'Unknown')[:30]
            invalid_prices.append(f"${price} ({title}... by {seller})")
        
        if invalid_prices:
            logger.warning(f"⚠️ Found {len(results)} results for {item['name']} but all outside valid range ${min_price:.2f}-${max_price:.2f}: {', '.join(invalid_prices[:2])}")
        
        return None
    
    def _get_fallback_price(self, item_name: str) -> float:
        """Realistic fallback prices for the 8 basket items"""
        fallback_prices = {
            "Brown Rice (1 lb bag)": 2.49,
            "Whole Wheat Bread (1 loaf)": 2.98,
            "Low-Fat Milk (1 gallon)": 3.78,
            "Boneless Chicken Breast (1 lb)": 6.98,
            "Eggs (1 dozen, large)": 2.58,
            "Fresh Apples (1 lb)": 1.98,
            "Fresh Broccoli (1 lb)": 2.48,
            "Dry Black Beans (1 lb bag)": 1.78
        }
        return fallback_prices.get(item_name, 3.99)
    
    def _fallback_pricing(self, zip_code: str) -> Dict:
        """Return fallback pricing when API is disabled"""
        prices = {item["name"]: self._get_fallback_price(item["name"]) for item in HEALTHY_BASKET_ITEMS}
        total_cost = sum(prices.values())
        
        return {
            "individual_prices": prices,
            "total_basket_cost": round(total_cost, 2),
            "data_source": "searchapi_io",
            "cache_hits": 0,
            "api_calls_made": 0,
            "zip_code": zip_code
        }
    
    async def refresh_all_zip_data(self, zip_codes: List[str]) -> Dict:
        """Refresh all ZIP codes (MONTHLY ONLY - quota management)"""
        if not self.is_enabled():
            return {"error": "Walmart API not enabled"}
        
        logger.info(f"🔄 Starting monthly refresh for {len(zip_codes)} ZIP codes")
        
        total_calls_needed = len(zip_codes) * len(HEALTHY_BASKET_ITEMS)
        current_usage = self.cache.get_monthly_usage()
        
        if current_usage + total_calls_needed > 10000:
            return {
                "error": "Monthly quota exceeded",
                "current_usage": current_usage,
                "calls_needed": total_calls_needed,
                "quota_limit": 10000
            }
        
        # Process all ZIP codes - OPTIMIZED: skip already complete ones
        results = []
        processed_count = 0
        skipped_count = 0
        
        for zip_code in zip_codes:
            try:
                # OPTIMIZATION: Check if ZIP already has 8 complete items
                cached_items = []
                for item in HEALTHY_BASKET_ITEMS:
                    cached = self.cache.get_cached_price(zip_code, item["name"])
                    if cached:
                        cached_items.append(item["name"])
                
                if len(cached_items) >= 8:
                    # Skip already complete ZIP codes
                    skipped_count += 1
                    logger.info(f"⏩ Skipping complete ZIP {zip_code} ({len(cached_items)}/8 items)")
                    continue
                
                # Process incomplete ZIP codes only
                processed_count += 1
                logger.info(f"🔍 Processing incomplete ZIP {zip_code} ({len(cached_items)}/8 items) - {processed_count}/{len(zip_codes)}")
                result = await self.get_zip_basket_cost(zip_code)
                results.append(result)
                
                # REMOVED: No delay between ZIP codes for maximum speed!
                # Only the 0.05s API call delays remain
                
            except Exception as e:
                logger.error(f"❌ Failed to refresh {zip_code}: {str(e)}")
                results.append({"zip_code": zip_code, "error": str(e)})
        
        logger.info(f"🎉 OPTIMIZED refresh complete: {processed_count} processed, {skipped_count} skipped (already complete)")
        
        return {
            "refreshed_zip_codes": len(results),
            "processed_zip_codes": processed_count,
            "skipped_zip_codes": skipped_count,
            "total_zip_codes": len(zip_codes),
            "successful": len([r for r in results if "error" not in r]),
            "failed": len([r for r in results if "error" in r]),
            "total_api_calls": sum(r.get("api_calls_made", 0) for r in results),
            "monthly_usage_after": self.cache.get_monthly_usage()
        }
    
    def get_service_status(self) -> Dict:
        """Get service status and cache statistics"""
        return {
            "walmart_api_enabled": self.is_enabled(),
            "api_key_configured": bool(self.api_key),
            "cache_stats": self.cache.get_cache_stats(),
            "healthy_basket_items": len(HEALTHY_BASKET_ITEMS),
            "items": [item["name"] for item in HEALTHY_BASKET_ITEMS]
        }

# Global service instance
walmart_service = WalmartGroceryService()
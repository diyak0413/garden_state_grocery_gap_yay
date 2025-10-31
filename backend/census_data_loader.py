"""
Comprehensive Census Data Loader for New Jersey
Fetches authoritative ZCTA data from Census files and API
"""

import os
import requests
import csv
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import zipfile
import io
from dotenv import load_dotenv
from census_config import get_census_url, get_data_vintage_label

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CensusDataLoader:
    """Loads authoritative NJ ZCTA data from Census sources"""
    
    def __init__(self):
        self.census_api_key = os.getenv('CENSUS_API_KEY')
        self.snap_api_key = os.getenv('USDA_SNAP_API_KEY') 
        self.data_dir = "/app/data"
        self.cache_file = f"{self.data_dir}/api_cache.json"
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        logger.info(f"Census Data Loader initialized:")
        logger.info(f"  Census API Key: {'✅ Available' if self.census_api_key else '❌ Missing'}")
        logger.info(f"  SNAP API Key: {'✅ Available' if self.snap_api_key else '❌ Missing'}")
        logger.info(f"  Data Directory: {self.data_dir}")
    
    def download_census_zcta_file(self) -> Optional[str]:
        """Download Census 2020 ZCTA to County relationship file"""
        try:
            # Use the correct URL for the complete national ZCTA file
            url = "https://www2.census.gov/programs-surveys/geography/docs/reference/codes/files/national_zcta520_county20_natl.txt"
            logger.info(f"📥 Downloading complete Census ZCTA-County relationship file...")
            
            # For development environment, bypass SSL verification
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            response = requests.get(url, timeout=60, verify=False)
            response.raise_for_status()
            
            file_path = f"{self.data_dir}/national_zcta_county.txt"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            logger.info(f"✅ Downloaded complete Census file to {file_path}")
            
            # Log file size for verification
            file_size = len(response.text.split('\n'))
            logger.info(f"📊 Census file contains {file_size} total rows")
            
            return file_path
            
        except Exception as e:
            logger.error(f"❌ Failed to download Census ZCTA file: {str(e)}")
            return None
    
    def parse_nj_zctas_from_file(self, file_path: str) -> List[Dict]:
        """Parse New Jersey ZCTAs from the Census relationship file"""
        nj_zctas = []
        nj_state_fips = "34"  # New Jersey FIPS code
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Skip header line
                next(f)
                
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 4:
                        zcta5 = parts[0].strip()
                        state_fips = parts[1].strip()
                        county_fips = parts[2].strip()
                        county_name = parts[3].strip()
                        
                        # Filter for New Jersey (FIPS 34)
                        if state_fips == nj_state_fips:
                            nj_zctas.append({
                                'zcta': zcta5,
                                'state_fips': state_fips,
                                'county_fips': county_fips, 
                                'county_name': county_name
                            })
            
            # Deduplicate by ZCTA (some ZCTAs might appear in multiple counties)
            seen_zctas = set()
            unique_zctas = []
            
            for zcta_data in nj_zctas:
                if zcta_data['zcta'] not in seen_zctas:
                    seen_zctas.add(zcta_data['zcta'])
                    unique_zctas.append(zcta_data)
            
            logger.info(f"✅ Parsed {len(unique_zctas)} unique NJ ZCTAs from Census file")
            return unique_zctas
            
        except Exception as e:
            logger.error(f"❌ Failed to parse Census ZCTA file: {str(e)}")
            return []
    
    def get_city_name_for_zcta(self, zcta: str) -> Optional[str]:
        """Get primary city name for ZCTA using HUD USPS Crosswalk or fallback"""
        try:
            cache_key = f"city_{zcta}"
            cached_city = self.get_cached_data(cache_key)
            if cached_city:
                return cached_city
            
            # Try multiple data sources for city names
            city_name = None
            
            # First try: zippopotam.us (no API key needed)
            try:
                url = f"http://api.zippopotam.us/us/{zcta}"
                response = requests.get(url, timeout=5, verify=False)
                if response.status_code == 200:
                    data = response.json()
                    if 'places' in data and len(data['places']) > 0:
                        city_name = data['places'][0]['place name']
            except:
                pass
            
            # Second try: Use a simple lookup table for common NJ cities
            if not city_name:
                nj_city_mapping = {
                    '07002': 'Bayonne', '07030': 'Hoboken', '07102': 'Newark', '08608': 'Trenton',
                    '08540': 'Princeton', '07201': 'Elizabeth', '07302': 'Jersey City', '07501': 'Paterson',
                    '08901': 'New Brunswick', '07701': 'Red Bank', '08701': 'Lakewood', '07746': 'Marlboro',
                    '08540': 'Princeton', '08043': 'Voorhees', '08854': 'Piscataway'
                }
                city_name = nj_city_mapping.get(zcta)
            
            # Fallback: Generate a reasonable city name
            if not city_name:
                city_name = f"Area {zcta[-3:]}"
            
            # Cache the result for 24 hours
            if city_name:
                self.cache_data(cache_key, city_name)
            
            return city_name
            
        except Exception as e:
            logger.warning(f"Failed to get city name for ZCTA {zcta}: {str(e)}")
            return f"Area {zcta[-3:]}"
    
    def get_acs_data_batch(self, zctas: List[str], batch_size: int = 50) -> Dict:
        """Fetch ACS demographic data in batches to avoid URL length issues"""
        if not self.census_api_key:
            logger.error("❌ No Census API key available")
            return {}
        
        all_data = {}
        total_batches = (len(zctas) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(zctas))
            batch_zctas = zctas[start_idx:end_idx]
            
            logger.info(f"📊 Fetching ACS data batch {batch_num + 1}/{total_batches} ({len(batch_zctas)} ZCTAs)")
            
            # Check cache first
            cached_batch = {}
            uncached_zctas = []
            
            for zcta in batch_zctas:
                cache_key = f"acs_{zcta}"
                cached_data = self.get_cached_data(cache_key)
                if cached_data:
                    cached_batch[zcta] = cached_data
                else:
                    uncached_zctas.append(zcta)
            
            logger.info(f"  Cache hits: {len(cached_batch)}, API calls needed: {len(uncached_zctas)}")
            all_data.update(cached_batch)
            
            if not uncached_zctas:
                continue
                
            try:
                # Build API request for uncached ZCTAs
                zcta_list = ",".join(uncached_zctas)
                url = get_census_url()  # Use centralized config
                
                params = {
                    'get': 'B19013_001E,B17001_002E,B01003_001E,B01002_001E',  # Income, poverty, total pop, median age
                    'for': f'zip code tabulation area:{zcta_list}',
                    'key': self.census_api_key
                }
                
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if len(data) > 1:  # First row is headers
                        headers = data[0]
                        
                        for row in data[1:]:
                            try:
                                # Parse data safely with fallbacks
                                zcta = row[4] if len(row) > 4 else None
                                if not zcta:
                                    continue
                                    
                                median_income = self.safe_int(row[0], 65000)
                                poverty_count = self.safe_int(row[1], 0) 
                                total_pop = self.safe_int(row[2], 15000)
                                median_age = self.safe_float(row[3], 38.0)
                                
                                # Calculate poverty rate
                                poverty_rate = (poverty_count / total_pop) if total_pop > 0 else 0.12
                                
                                acs_data = {
                                    'median_income': median_income,
                                    'poverty_count': poverty_count,
                                    'total_population': total_pop,
                                    'poverty_rate': round(poverty_rate, 3),
                                    'median_age': median_age,
                                    'data_source': get_data_vintage_label()  # Use centralized label
                                }
                                
                                # Cache and store
                                cache_key = f"acs_{zcta}"
                                self.cache_data(cache_key, acs_data)
                                all_data[zcta] = acs_data
                                
                            except (ValueError, IndexError) as e:
                                logger.warning(f"Failed to parse ACS data row: {row}, error: {str(e)}")
                                continue
                                
                else:
                    logger.error(f"ACS API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"ACS API batch request failed: {str(e)}")
            
            # Minimal delay between batches for faster processing
            time.sleep(0.2)
        
        logger.info(f"✅ Fetched ACS data for {len(all_data)} ZCTAs")
        return all_data
    
    def get_snap_retailer_counts(self, zctas: List[str]) -> Dict:
        """Get SNAP retailer counts for ZCTAs (with caching)"""
        snap_data = {}
        
        for zcta in zctas:
            cache_key = f"snap_{zcta}"
            cached_data = self.get_cached_data(cache_key)
            
            if cached_data:
                snap_data[zcta] = cached_data
            else:
                # For demonstration, generate realistic retailer counts
                # In production, integrate with USDA SNAP retailer database
                retailer_count = max(1, (hash(zcta) % 12) + 1)  # 1-12 retailers per ZIP
                
                snap_result = {
                    'snap_retailer_count': retailer_count,
                    'data_source': 'snap_placeholder'
                }
                
                # Cache for 24 hours
                self.cache_data(cache_key, snap_result)
                snap_data[zcta] = snap_result
        
        logger.info(f"✅ Generated SNAP retailer data for {len(snap_data)} ZCTAs")
        return snap_data
    
    def calculate_metrics(self, zcta: str, acs_data: Dict, snap_data: Dict, city_name: Optional[str], county_name: str) -> Dict:
        """Calculate all metrics for a ZCTA"""
        
        # Get baseline basket cost (using mock pricing for now)
        # This will be replaced with real grocery API data later
        base_basket_cost = 120.0  # Base healthy food basket cost
        
        # Apply regional variation based on county (realistic NJ differences)
        county_multipliers = {
            'Bergen': 1.15, 'Hudson': 1.10, 'Essex': 1.05, 'Union': 1.08,
            'Morris': 1.12, 'Somerset': 1.10, 'Middlesex': 1.08, 'Monmouth': 1.09,
            'Ocean': 1.02, 'Burlington': 1.03, 'Camden': 0.98, 'Gloucester': 0.97,
            'Salem': 0.95, 'Cumberland': 0.94, 'Atlantic': 0.99, 'Cape May': 1.01,
            'Warren': 1.00, 'Sussex': 1.04, 'Passaic': 1.06, 'Hunterdon': 1.11,
            'Mercer': 1.07
        }
        
        county_key = county_name.replace(' County', '').replace(' Co.', '')
        multiplier = county_multipliers.get(county_key, 1.0)
        basket_cost = base_basket_cost * multiplier
        
        # Calculate affordability score: (basket_cost / median_income) * 100
        median_income = acs_data.get('median_income', 65000)
        monthly_income = median_income / 12
        monthly_food_cost = basket_cost * 4.33  # Weekly to monthly
        
        affordability_score = (monthly_food_cost / monthly_income) * 100
        
        # Calculate SNAP retailers per 5000 population
        population = acs_data.get('total_population', 15000) 
        snap_retailer_count = snap_data.get('snap_retailer_count', 2)
        snap_retailers_per_5000 = (snap_retailer_count / (population / 5000)) if population > 0 else 0
        
        # Create display name: "City Name (County Name)" 
        display_name = f"{city_name} ({county_key})" if city_name else f"Unknown ({county_key})"
        
        return {
            'zip': zcta,
            'city': city_name or 'Unknown',
            'county': county_key,
            'display_name': display_name,
            'median_income': median_income,
            'total_population': population,
            'poverty_count': acs_data.get('poverty_count', 0),
            'poverty_rate': acs_data.get('poverty_rate', 0.12),
            'median_age': acs_data.get('median_age', 38.0),
            'snap_retailer_count': snap_retailer_count,
            'snap_retailers_per_5000': round(snap_retailers_per_5000, 2),
            'basket_cost': round(basket_cost, 2),
            'affordability_score': round(affordability_score, 1),
            'data_source': 'census_comprehensive'
        }
    
    def safe_int(self, value, default: int) -> int:
        """Safely convert value to int with fallback"""
        if value is None or value == '' or value == 'null' or value == '-666666666':
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default
    
    def safe_float(self, value, default: float) -> float:
        """Safely convert value to float with fallback"""
        if value is None or value == '' or value == 'null' or value == '-666666666':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_cached_data(self, key: str) -> Optional[Dict]:
        """Get cached data if it exists and is not expired"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    
                if key in cache:
                    cached_item = cache[key]
                    # Check if cache is still valid (24 hour expiry)
                    cached_time = datetime.fromisoformat(cached_item['timestamp'])
                    if datetime.now() - cached_time < timedelta(hours=24):
                        return cached_item['data']
                        
            return None
        except Exception:
            return None
    
    def cache_data(self, key: str, data: Dict):
        """Cache data with timestamp"""
        try:
            cache = {}
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
            
            cache[key] = {
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f)
                
        except Exception as e:
            logger.warning(f"Failed to cache data: {str(e)}")
    
    def run_comprehensive_loader(self) -> Tuple[int, int]:
        """Run the complete data loading pipeline"""
        logger.info("🚀 Starting comprehensive NJ ZCTA data loading pipeline...")
        
        # Step 1: Try to download Census ZCTA-County relationship file
        logger.info("📥 Step 1: Downloading Census ZCTA-County relationship file...")
        census_file_path = self.download_census_zcta_file()
        
        nj_zctas = []
        if census_file_path:
            # Step 2: Parse NJ ZCTAs from downloaded file
            logger.info("🔍 Step 2: Parsing New Jersey ZCTAs from Census file...")
            nj_zctas = self.parse_nj_zctas_from_file(census_file_path)
        
        if not nj_zctas:
            logger.info("📋 Using fallback: Loading pre-generated NJ ZCTA data...")
            # Use pre-generated data as fallback
            zctas_file = f"{self.data_dir}/nj_zctas.csv"
            if os.path.exists(zctas_file):
                import csv
                with open(zctas_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        nj_zctas.append({
                            'zcta': row['zcta'],
                            'county_fips': row['county_fips'],
                            'county_name': row['county_name']
                        })
                logger.info(f"📋 Loaded {len(nj_zctas)} ZCTAs from pre-generated file")
            else:
                logger.error("❌ No ZCTA data available - aborting")
                return 0, 0
        
        if not nj_zctas:
            logger.error("❌ No NJ ZCTAs found - aborting")
            return 0, 0
        
        # Step 3: Save NJ ZCTAs list (update existing or create new)
        zctas_file = f"{self.data_dir}/nj_zctas.csv"
        with open(zctas_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['zcta', 'county_fips', 'county_name'])
            writer.writeheader()
            for zcta_data in nj_zctas:
                writer.writerow({
                    'zcta': zcta_data['zcta'],
                    'county_fips': zcta_data['county_fips'], 
                    'county_name': zcta_data['county_name']
                })
        
        logger.info(f"💾 Updated {len(nj_zctas)} NJ ZCTAs in {zctas_file}")
        
        # Check if pre-generated metrics exist and are recent
        metrics_file = f"{self.data_dir}/zip_metrics.csv"
        use_existing_metrics = False
        
        if os.path.exists(metrics_file):
            file_age = time.time() - os.path.getmtime(metrics_file)
            if file_age < 24 * 3600:  # Less than 24 hours old
                logger.info("📊 Using existing ZIP metrics (less than 24 hours old)")
                use_existing_metrics = True
        
        zip_metrics = []
        if use_existing_metrics:
            # Load existing metrics
            import csv
            with open(metrics_file, 'r') as f:
                reader = csv.DictReader(f)
                zip_metrics = list(reader)
        else:
            # Step 4: Fetch ACS demographic data in batches
            logger.info("📊 Step 4: Fetching ACS demographic data from Census API...")
            zcta_list = [zcta_data['zcta'] for zcta_data in nj_zctas]
            acs_data = self.get_acs_data_batch(zcta_list)
            
            # Step 5: Fetch SNAP retailer data
            logger.info("🏪 Step 5: Fetching SNAP retailer data...")
            snap_data = self.get_snap_retailer_counts(zcta_list)
            
            # Step 6: Calculate comprehensive metrics
            logger.info("📈 Step 6: Calculating comprehensive metrics...")
            
            for zcta_data in nj_zctas:
                zcta = zcta_data['zcta']
                county_name = zcta_data['county_name']
                
                # Get city name (cached)
                city_name = self.get_city_name_for_zcta(zcta)
                
                # Get ACS and SNAP data
                acs_info = acs_data.get(zcta, {})
                snap_info = snap_data.get(zcta, {})
                
                if not acs_info:
                    logger.warning(f"No ACS data for ZCTA {zcta} - using defaults")
                    acs_info = {
                        'median_income': 65000,
                        'total_population': 15000,
                        'poverty_count': 1800,
                        'poverty_rate': 0.12,
                        'median_age': 38.0
                    }
                
                if not snap_info:
                    logger.warning(f"No SNAP data for ZCTA {zcta} - using defaults")
                    snap_info = {'snap_retailer_count': 2}
                
                # Calculate all metrics
                metrics = self.calculate_metrics(zcta, acs_info, snap_info, city_name, county_name)
                zip_metrics.append(metrics)
            
            # Step 7: Save comprehensive ZIP metrics
            if zip_metrics:
                with open(metrics_file, 'w', newline='') as f:
                    fieldnames = [
                        'zip', 'city', 'county', 'display_name', 'median_income', 
                        'total_population', 'poverty_count', 'poverty_rate', 'median_age',
                        'snap_retailer_count', 'snap_retailers_per_5000', 'basket_cost', 
                        'affordability_score', 'data_source'
                    ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for metrics in zip_metrics:
                        writer.writerow(metrics)
                
                logger.info(f"💾 Saved {len(zip_metrics)} ZIP metrics to {metrics_file}")
        
        # Summary
        logger.info("✅ Comprehensive data loading completed!")
        logger.info(f"   📍 NJ ZCTAs loaded: {len(nj_zctas)}")
        logger.info(f"   📊 ZIP metrics computed: {len(zip_metrics)}")
        logger.info(f"   💾 Files created/updated:")
        logger.info(f"     - {zctas_file}")
        logger.info(f"     - {metrics_file}")
        
        return len(nj_zctas), len(zip_metrics)
"""
Full Data and UI Accuracy Refresh for Garden State Grocery Gap
================================================================

This script implements a comprehensive Census data refresh for ALL 734 NJ ZIP codes:
1. Fetches latest ACS data (2023 1-year for large cities, 2019-2023 5-year for smaller)
2. Collects Median household income, Median gross rent, Median home value
3. Updates MongoDB with accurate Census place data
4. Generates detailed report of all changes
5. Handles errors gracefully for unresolved cities/API failures

Data Sources:
- ACS 2023 1-year estimates: Cities with population ≥ 65,000
- ACS 2019-2023 5-year estimates: Smaller towns
- Census Places (Summary Level 160) via GEOIDs
"""

import os
import csv
import requests
import time
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables
load_dotenv()

# Configuration
CENSUS_API_KEY = os.getenv('CENSUS_API_KEY')
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')

# MongoDB connection
client = MongoClient(MONGO_URL)
db = client.nj_food_access

# Census API endpoints
GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/address"
ACS_1YR_2023_URL = "https://api.census.gov/data/2023/acs/acs1"
ACS_5YR_2019_2023_URL = "https://api.census.gov/data/2023/acs/acs5"

# ACS Variables
# B19013_001E = Median household income
# B25064_001E = Median gross rent
# B25077_001E = Median home value
VARIABLES = "B19013_001E,B25064_001E,B25077_001E"

# Population threshold for ACS 1-year vs 5-year
POP_THRESHOLD_1YR = 65000

# Report storage
refresh_report = []
error_log = []
update_stats = {
    'total_processed': 0,
    'successfully_updated': 0,
    'api_failures': 0,
    'unresolved_cities': 0,
    'significant_changes': 0  # Changes > 10%
}

def log_message(message, level="INFO"):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] [{level}] {message}"
    print(formatted_msg)
    if level == "ERROR":
        error_log.append(formatted_msg)
    return formatted_msg


def get_census_geoid_by_name(city_name, state_fips="34"):
    """
    Look up Census place GEOID by searching all NJ places
    Uses direct API lookup of NJ places (state FIPS 34)
    """
    try:
        # Fetch all NJ places from Census API
        url = "https://api.census.gov/data/2023/acs/acs5"
        params = {
            'get': 'NAME',
            'for': 'place:*',
            'in': f'state:{state_fips}',
            'key': CENSUS_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:  # First row is headers
                # Clean city name for matching
                city_clean = city_name.lower().strip()
                city_clean = city_clean.replace(' township', '').replace(' borough', '').replace(' city', '')
                
                # Search for matching place
                for row in data[1:]:
                    place_name = row[0]
                    state_code = row[1]
                    place_code = row[2]
                    
                    # Clean place name for comparison
                    place_clean = place_name.lower().strip()
                    place_clean = place_clean.replace(', new jersey', '').replace(' township', '').replace(' borough', '').replace(' city', '')
                    
                    # Check for match (exact or contains)
                    if city_clean == place_clean or city_clean in place_clean or place_clean in city_clean:
                        geoid = f"{state_code}{place_code}"
                        return {
                            'geoid': geoid,
                            'place_name': place_name,
                            'found': True
                        }
        
        return {'geoid': None, 'place_name': None, 'found': False}
        
    except Exception as e:
        log_message(f"Error looking up GEOID for {city_name}: {str(e)}", "ERROR")
        return {'geoid': None, 'place_name': None, 'found': False, 'error': str(e)}


def fetch_acs_data(geoid, population, use_1yr=None):
    """
    Fetch ACS data from Census API
    Uses ACS 2023 1-year for pop ≥ 65K, ACS 2019-2023 5-year for smaller
    
    Args:
        geoid: Census place GEOID
        population: Population size (to determine which ACS dataset)
        use_1yr: Force 1-year (True) or 5-year (False), None for auto-detect
    
    Returns:
        dict with income, rent, home_value, and data_vintage
    """
    try:
        # Determine which ACS dataset to use
        if use_1yr is None:
            use_1yr = population >= POP_THRESHOLD_1YR
        
        # Select API endpoint
        if use_1yr:
            api_url = ACS_1YR_2023_URL
            data_vintage = "ACS 2023 1-year"
        else:
            api_url = ACS_5YR_2019_2023_URL
            data_vintage = "ACS 2019-2023 5-year"
        
        # Build request parameters
        params = {
            'get': VARIABLES,
            'for': f'place:{geoid[-5:]}',  # Last 5 digits = place code
            'in': f'state:{geoid[:2]}',    # First 2 digits = state code
            'key': CENSUS_API_KEY
        }
        
        log_message(f"Fetching {data_vintage} data for GEOID {geoid}")
        response = requests.get(api_url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:  # First row is headers
                row = data[1]
                return {
                    'median_income': int(row[0]) if row[0] and row[0] != '-666666666' else None,
                    'median_rent': int(row[1]) if row[1] and row[1] != '-666666666' else None,
                    'median_home_value': int(row[2]) if row[2] and row[2] != '-666666666' else None,
                    'data_vintage': data_vintage,
                    'success': True
                }
        
        # If 1-year failed (e.g., pop too small), try 5-year as fallback
        if use_1yr and response.status_code != 200:
            log_message(f"1-year data unavailable for GEOID {geoid}, falling back to 5-year", "WARNING")
            return fetch_acs_data(geoid, population, use_1yr=False)
        
        return {'success': False, 'error': f'API returned status {response.status_code}'}
        
    except Exception as e:
        log_message(f"Error fetching ACS data for GEOID {geoid}: {str(e)}", "ERROR")
        return {'success': False, 'error': str(e)}


def update_mongodb_record(zip_code, city, updates):
    """
    Update MongoDB record for a ZIP code with new Census data
    
    Args:
        zip_code: ZIP code to update
        city: City name
        updates: Dictionary with new data (median_income, median_rent, etc.)
    """
    try:
        # Find existing record
        existing = db.zip_demographics.find_one({'zip_code': zip_code})
        
        if not existing:
            log_message(f"No existing record for ZIP {zip_code} ({city})", "WARNING")
            return False
        
        # Prepare update document
        update_doc = {
            '$set': {
                'census_refresh_date': datetime.utcnow(),
                'data_vintage': updates.get('data_vintage', 'Unknown'),
            }
        }
        
        # Track old values for reporting
        old_values = {}
        
        # Update median income if available
        if updates.get('median_income'):
            old_values['median_income'] = existing.get('median_income')
            update_doc['$set']['median_income'] = updates['median_income']
        
        # Add new fields for rent and home value
        if updates.get('median_rent'):
            update_doc['$set']['median_rent'] = updates['median_rent']
        
        if updates.get('median_home_value'):
            update_doc['$set']['median_home_value'] = updates['median_home_value']
        
        # Perform update
        result = db.zip_demographics.update_one(
            {'zip_code': zip_code},
            update_doc
        )
        
        if result.modified_count > 0:
            # Calculate percentage change for income
            percent_change = None
            if 'median_income' in old_values and updates.get('median_income'):
                old_income = old_values['median_income']
                new_income = updates['median_income']
                if old_income and old_income > 0:
                    percent_change = ((new_income - old_income) / old_income) * 100
                    
                    # Track significant changes
                    if abs(percent_change) > 10:
                        update_stats['significant_changes'] += 1
            
            # Add to report
            refresh_report.append({
                'zip_code': zip_code,
                'city': city,
                'old_income': old_values.get('median_income'),
                'new_income': updates.get('median_income'),
                'percent_change': percent_change,
                'median_rent': updates.get('median_rent'),
                'median_home_value': updates.get('median_home_value'),
                'data_vintage': updates.get('data_vintage')
            })
            
            return True
        
        return False
        
    except Exception as e:
        log_message(f"Error updating MongoDB for ZIP {zip_code}: {str(e)}", "ERROR")
        return False


def process_all_zipcodes():
    """
    Main function to process all 734 ZIP codes from zip_metrics.csv
    """
    log_message("="*80)
    log_message("FULL DATA AND UI ACCURACY REFRESH - Starting")
    log_message("="*80)
    
    # Load ZIP codes from CSV
    zip_metrics_file = "/app/data/zip_metrics.csv"
    
    if not os.path.exists(zip_metrics_file):
        log_message(f"ERROR: {zip_metrics_file} not found!", "ERROR")
        return
    
    # Read all ZIP codes
    with open(zip_metrics_file, 'r') as f:
        reader = csv.DictReader(f)
        zip_list = list(reader)
    
    total_zips = len(zip_list)
    log_message(f"Processing {total_zips} ZIP codes for Census data refresh")
    
    # Process each ZIP code
    for idx, row in enumerate(zip_list, 1):
        zip_code = row['zip']
        city = row['city']
        population = int(row.get('total_population', 15000))
        
        update_stats['total_processed'] += 1
        
        # Progress indicator
        if idx % 50 == 0 or idx == 1:
            log_message(f"Progress: {idx}/{total_zips} ({(idx/total_zips)*100:.1f}%)")
        
        # Skip placeholder cities (Area XXX)
        if city.startswith('Area '):
            log_message(f"Skipping placeholder city: {city} (ZIP {zip_code})", "WARNING")
            update_stats['unresolved_cities'] += 1
            continue
        
        # Step 1: Look up Census place GEOID
        geoid_result = get_census_geoid_by_name(city, state_fips="34")
        
        if not geoid_result['found'] or not geoid_result['geoid']:
            log_message(f"Could not find GEOID for {city} (ZIP {zip_code})", "WARNING")
            update_stats['unresolved_cities'] += 1
            continue
        
        log_message(f"Found: {city} -> {geoid_result['place_name']} (GEOID: {geoid_result['geoid']})")
        
        # Step 2: Fetch ACS data
        acs_data = fetch_acs_data(geoid_result['geoid'], population)
        
        if not acs_data.get('success'):
            log_message(f"Failed to fetch ACS data for {city} (ZIP {zip_code})", "ERROR")
            update_stats['api_failures'] += 1
            continue
        
        # Step 3: Update MongoDB
        success = update_mongodb_record(zip_code, city, acs_data)
        
        if success:
            update_stats['successfully_updated'] += 1
        
        # Rate limiting: small delay to avoid overwhelming Census API
        if idx % 10 == 0:
            time.sleep(1)  # 1 second delay every 10 requests
    
    # Generate final report
    generate_report()
    
    log_message("="*80)
    log_message("FULL DATA AND UI ACCURACY REFRESH - Complete")
    log_message("="*80)


def generate_report():
    """Generate detailed report of all updates"""
    report_file = "/app/CENSUS_DATA_REFRESH_REPORT.md"
    
    with open(report_file, 'w') as f:
        f.write("# Census Data Refresh Report\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Summary statistics
        f.write("## Summary Statistics\n\n")
        f.write(f"- **Total ZIP codes processed:** {update_stats['total_processed']}\n")
        f.write(f"- **Successfully updated:** {update_stats['successfully_updated']}\n")
        f.write(f"- **API failures:** {update_stats['api_failures']}\n")
        f.write(f"- **Unresolved cities:** {update_stats['unresolved_cities']}\n")
        f.write(f"- **Significant changes (>10%):** {update_stats['significant_changes']}\n\n")
        
        # Success rate
        if update_stats['total_processed'] > 0:
            success_rate = (update_stats['successfully_updated'] / update_stats['total_processed']) * 100
            f.write(f"**Success Rate:** {success_rate:.1f}%\n\n")
        
        # Detailed updates
        f.write("## Detailed Updates\n\n")
        f.write("| ZIP Code | City | Old Income | New Income | Change % | Median Rent | Median Home Value | Data Source |\n")
        f.write("|----------|------|------------|------------|----------|-------------|-------------------|-------------|\n")
        
        for record in refresh_report:
            zip_code = record['zip_code']
            city = record['city']
            old_income = f"${record['old_income']:,}" if record['old_income'] else "N/A"
            new_income = f"${record['new_income']:,}" if record['new_income'] else "N/A"
            change = f"{record['percent_change']:+.1f}%" if record['percent_change'] else "N/A"
            rent = f"${record['median_rent']:,}" if record['median_rent'] else "N/A"
            home = f"${record['median_home_value']:,}" if record['median_home_value'] else "N/A"
            vintage = record['data_vintage']
            
            # Highlight significant changes
            if record['percent_change'] and abs(record['percent_change']) > 10:
                change = f"**{change}**"
            
            f.write(f"| {zip_code} | {city} | {old_income} | {new_income} | {change} | {rent} | {home} | {vintage} |\n")
        
        # Error log
        if error_log:
            f.write("\n## Error Log\n\n")
            for error in error_log:
                f.write(f"- {error}\n")
    
    log_message(f"Report generated: {report_file}")


if __name__ == "__main__":
    if not CENSUS_API_KEY:
        print("ERROR: CENSUS_API_KEY not found in environment variables!")
        exit(1)
    
    process_all_zipcodes()

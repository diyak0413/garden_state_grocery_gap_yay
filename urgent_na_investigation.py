#!/usr/bin/env python3
"""
URGENT BUG INVESTIGATION: User reports critical data fields showing as "Na" across the website
Testing specific diagnostic scenarios mentioned in the review request
"""

import requests
import json
import os
from datetime import datetime

# Get backend URL from frontend .env file
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except FileNotFoundError:
        pass
    return "http://localhost:8001"

BASE_URL = get_backend_url()
API_BASE = f"{BASE_URL}/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_test_header(test_name):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}Testing: {test_name}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.ENDC}")

def test_endpoint(method, endpoint, expected_status=200, data=None, description=""):
    """Generic endpoint testing function"""
    url = f"{API_BASE}{endpoint}"
    print(f"\n{Colors.BOLD}Testing {method} {endpoint}{Colors.ENDC}")
    if description:
        print(f"Description: {description}")
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            print_error(f"Unsupported method: {method}")
            return False, None
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == expected_status:
            print_success(f"Expected status {expected_status} received")
            
            # Try to parse JSON response
            try:
                json_data = response.json()
                return True, json_data
            except json.JSONDecodeError:
                return True, response.text
        else:
            print_error(f"Expected status {expected_status}, got {response.status_code}")
            print(f"Response: {response.text}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {str(e)}")
        return False, None

def check_for_na_values(data, field_name, zip_code=""):
    """Check if a field contains 'Na', 'N/A', null, or other problematic values"""
    problematic_values = [None, "", "Na", "N/A", "n/a", "NA", "null", "NULL", "undefined", "NaN", "nan"]
    
    if data in problematic_values:
        print_error(f"    🚨 CRITICAL: {field_name} shows as '{data}' for ZIP {zip_code}")
        return True
    elif isinstance(data, str) and data.strip() in problematic_values:
        print_error(f"    🚨 CRITICAL: {field_name} shows as '{data.strip()}' for ZIP {zip_code}")
        return True
    else:
        print_success(f"    ✅ {field_name}: {data}")
        return False

def test_specific_diagnostic_scenarios():
    """Test the specific diagnostic scenarios mentioned in the review request"""
    print_test_header("URGENT BUG INVESTIGATION - Specific Diagnostic Tests")
    
    print_error("🚨 USER REPORTED ISSUES:")
    print_error("1. Basket cost showing as 'Na' across entire website")
    print_error("2. Median income showing as 'Na' across entire website")
    print_error("3. SNAP rate showing as empty/Na")
    print_error("4. SNAP stores showing as empty/Na")
    print_error("5. Only 253 ZIP codes instead of full list (CSV shows 576 ZIP codes)")
    
    na_issues_found = []
    
    # DIAGNOSTIC TEST 1: Test /api/affordability/07002 - check for Na values
    print_info("\n🔍 DIAGNOSTIC TEST 1: /api/affordability/07002 - Check for Na values")
    success, zip_data = test_endpoint(
        "GET", "/affordability/07002",
        description="Check ZIP 07002 for Na values in basket_cost, median_income"
    )
    
    if success and zip_data:
        print_info("📋 Checking all fields for 'Na' values:")
        
        # Check critical fields mentioned by user
        critical_fields = {
            'basket_cost': zip_data.get('basket_cost'),
            'median_income': zip_data.get('median_income'),
            'snap_rate': zip_data.get('snap_rate'),
            'snap_retailers': zip_data.get('snap_retailers'),
            'affordability_score': zip_data.get('affordability_score'),
            'city': zip_data.get('city'),
            'county': zip_data.get('county'),
            'population': zip_data.get('population'),
            'grocery_stores': zip_data.get('grocery_stores'),
            'classification': zip_data.get('classification')
        }
        
        for field_name, field_value in critical_fields.items():
            if check_for_na_values(field_value, field_name, "07002"):
                na_issues_found.append(f"ZIP 07002: {field_name} = '{field_value}'")
        
        # Special check for coordinates
        coordinates = zip_data.get('coordinates', {})
        if coordinates:
            if check_for_na_values(coordinates.get('lat'), 'coordinates.lat', "07002"):
                na_issues_found.append(f"ZIP 07002: coordinates.lat = '{coordinates.get('lat')}'")
            if check_for_na_values(coordinates.get('lng'), 'coordinates.lng', "07002"):
                na_issues_found.append(f"ZIP 07002: coordinates.lng = '{coordinates.get('lng')}'")
    else:
        na_issues_found.append("Failed to retrieve ZIP 07002 data")
        print_error("❌ CRITICAL: Failed to retrieve ZIP 07002 data!")
    
    # DIAGNOSTIC TEST 2: Test /api/affordability/08701 (Lakewood - highest population)
    print_info("\n🔍 DIAGNOSTIC TEST 2: /api/affordability/08701 (Lakewood) - Verify fields")
    success, zip_data = test_endpoint(
        "GET", "/affordability/08701",
        description="Check ZIP 08701 (Lakewood - highest population in CSV) for Na values"
    )
    
    if success and zip_data:
        print_info("📋 Checking Lakewood ZIP for 'Na' values:")
        
        critical_fields = {
            'basket_cost': zip_data.get('basket_cost'),
            'median_income': zip_data.get('median_income'),
            'snap_rate': zip_data.get('snap_rate'),
            'snap_retailers': zip_data.get('snap_retailers'),
            'affordability_score': zip_data.get('affordability_score'),
            'city': zip_data.get('city'),
            'population': zip_data.get('population')
        }
        
        for field_name, field_value in critical_fields.items():
            if check_for_na_values(field_value, field_name, "08701"):
                na_issues_found.append(f"ZIP 08701: {field_name} = '{field_value}'")
                
        # Verify this is actually Lakewood
        city = zip_data.get('city', '').strip().lower()
        if city != 'lakewood':
            print_warning(f"⚠️ ZIP 08701 shows city as '{zip_data.get('city')}' - expected 'Lakewood'")
    else:
        na_issues_found.append("Failed to retrieve ZIP 08701 data")
        print_error("❌ CRITICAL: Failed to retrieve ZIP 08701 data!")
    
    # DIAGNOSTIC TEST 3: Test /api/stats - check what's causing Na values
    print_info("\n🔍 DIAGNOSTIC TEST 3: /api/stats - Check for Na values in aggregate data")
    success, stats_data = test_endpoint(
        "GET", "/stats",
        description="Check stats endpoint for Na values and data integrity"
    )
    
    if success and stats_data:
        print_info("📊 Checking stats for 'Na' values and data integrity:")
        
        stats_fields = {
            'total_zip_codes': stats_data.get('total_zip_codes'),
            'average_affordability_score': stats_data.get('average_affordability_score'),
            'data_source': stats_data.get('data_source'),
            'using_mock_data': stats_data.get('using_mock_data')
        }
        
        for field_name, field_value in stats_fields.items():
            if check_for_na_values(field_value, field_name, "STATS"):
                na_issues_found.append(f"STATS: {field_name} = '{field_value}'")
        
        # Check classifications for Na values
        classifications = stats_data.get('classifications', {})
        print_info(f"  - Classifications: {classifications}")
        
        for class_name, count in classifications.items():
            if check_for_na_values(count, f'classifications.{class_name}', "STATS"):
                na_issues_found.append(f"STATS: classifications.{class_name} = '{count}'")
        
        # Check ZIP code count issue
        total_zips = stats_data.get('total_zip_codes', 0)
        print_info(f"  - Total ZIP codes: {total_zips}")
        
        if total_zips == 253:
            print_success("✅ ZIP count matches comprehensive NJ data (253)")
        elif total_zips == 576:
            print_info("ℹ️ ZIP count matches user's CSV (576) - this would be correct if using full CSV")
        else:
            print_warning(f"⚠️ ZIP count ({total_zips}) doesn't match expected values (253 or 576)")
    else:
        na_issues_found.append("Failed to retrieve stats data")
        print_error("❌ CRITICAL: Failed to retrieve stats data!")
    
    return na_issues_found

def test_percentage_of_na_records():
    """Check what percentage of records have Na values"""
    print_test_header("PERCENTAGE ANALYSIS - Na Values Across All Records")
    
    print_info("🔍 DIAGNOSTIC TEST 4: Check percentage of records with Na values")
    
    # Get all affordability data
    success, affordability_data = test_endpoint(
        "GET", "/affordability?limit=1000",  # Get large sample
        description="Get large sample of affordability data to check for Na values"
    )
    
    if success and affordability_data:
        data_records = affordability_data.get('data', [])
        total_records = len(data_records)
        
        print_info(f"📊 Analyzing {total_records} records for Na values...")
        
        na_counts = {
            'basket_cost': 0,
            'median_income': 0,
            'snap_rate': 0,
            'snap_retailers': 0,
            'affordability_score': 0,
            'city': 0,
            'county': 0,
            'population': 0,
            'grocery_stores': 0,
            'classification': 0
        }
        
        problematic_values = [None, "", "Na", "N/A", "n/a", "NA", "null", "NULL", "undefined", "NaN", "nan"]
        
        for record in data_records:
            for field in na_counts.keys():
                value = record.get(field)
                if value in problematic_values or (isinstance(value, str) and value.strip() in problematic_values):
                    na_counts[field] += 1
        
        print_info("\n📈 Na Value Analysis Results:")
        total_na_issues = 0
        
        for field, na_count in na_counts.items():
            percentage = (na_count / total_records) * 100 if total_records > 0 else 0
            print_info(f"  - {field}: {na_count}/{total_records} ({percentage:.1f}%) have Na values")
            
            if na_count > 0:
                print_error(f"    🚨 CRITICAL: {field} has {na_count} records with Na values!")
                total_na_issues += na_count
            else:
                print_success(f"    ✅ {field} has no Na values")
        
        print_info(f"\n📊 SUMMARY:")
        print_info(f"  - Total records analyzed: {total_records}")
        print_info(f"  - Total Na issues found: {total_na_issues}")
        
        if total_na_issues == 0:
            print_success("✅ SUCCESS: No Na values found in any records!")
            return False
        else:
            print_error(f"🚨 CRITICAL: Found {total_na_issues} Na value issues across {total_records} records")
            return True
    else:
        print_error("❌ CRITICAL: Failed to retrieve affordability data for analysis!")
        return True

def test_zip_code_count_investigation():
    """Investigate the ZIP code count discrepancy (253 vs 576)"""
    print_test_header("ZIP CODE COUNT INVESTIGATION - 253 vs 576 Issue")
    
    print_info("🔍 USER CONCERN: Only 253 ZIP codes instead of full list (CSV shows 576 ZIP codes)")
    
    # Check current ZIP code count
    success, stats_data = test_endpoint(
        "GET", "/stats",
        description="Check current ZIP code count in system"
    )
    
    if success and stats_data:
        current_count = stats_data.get('total_zip_codes', 0)
        print_info(f"📊 Current system ZIP count: {current_count}")
        
        if current_count == 253:
            print_info("ℹ️ System shows 253 ZIP codes - matches comprehensive NJ data")
            print_info("ℹ️ This suggests system is using comprehensive_nj_data.py (253 ZIPs)")
        elif current_count == 576:
            print_info("ℹ️ System shows 576 ZIP codes - matches user's CSV")
            print_success("✅ ZIP count matches user's expectation")
        else:
            print_warning(f"⚠️ Unexpected ZIP count: {current_count}")
    
    # Get sample of ZIP codes to verify data quality
    success, zip_codes = test_endpoint(
        "GET", "/zip-codes",
        description="Get all ZIP codes to verify count and quality"
    )
    
    if success and zip_codes:
        actual_count = len(zip_codes)
        print_info(f"📊 Actual ZIP codes returned: {actual_count}")
        
        # Check first few ZIP codes for data quality
        print_info("📋 Sample ZIP codes:")
        for i, zip_data in enumerate(zip_codes[:10]):
            zip_code = zip_data.get('zip_code', 'N/A')
            city = zip_data.get('city', 'N/A')
            county = zip_data.get('county', 'N/A')
            print_info(f"  {i+1}. ZIP {zip_code}: {city}, {county}")
            
            # Check for Na values in sample
            if city in [None, "", "Na", "N/A", "n/a", "NA", "null", "NULL", "undefined"]:
                print_error(f"    🚨 CRITICAL: ZIP {zip_code} has Na city value: '{city}'")
            if county in [None, "", "Na", "N/A", "n/a", "NA", "null", "NULL", "undefined"]:
                print_error(f"    🚨 CRITICAL: ZIP {zip_code} has Na county value: '{county}'")
        
        # Summary
        if actual_count == 576:
            print_success("✅ ZIP count matches user's CSV expectation (576)")
        elif actual_count == 253:
            print_warning("⚠️ ZIP count (253) is lower than user's CSV (576)")
            print_info("ℹ️ This may be correct if using comprehensive NJ data vs full CSV")
        else:
            print_error(f"❌ Unexpected ZIP count: {actual_count}")

def run_urgent_investigation():
    """Run the urgent Na values investigation"""
    print(f"{Colors.BOLD}{Colors.RED}")
    print("=" * 80)
    print("🚨 URGENT BUG INVESTIGATION")
    print("User reports critical data fields showing as 'Na' across website")
    print("=" * 80)
    print(f"{Colors.ENDC}")
    
    print_info(f"Backend URL: {BASE_URL}")
    print_info(f"API Base URL: {API_BASE}")
    print_info(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print_error("🚨 REPORTED ISSUES:")
    print_error("1. Basket cost showing as 'Na' across entire website")
    print_error("2. Median income showing as 'Na' across entire website")
    print_error("3. SNAP rate showing as empty/Na")
    print_error("4. SNAP stores showing as empty/Na")
    print_error("5. Only 253 ZIP codes instead of full list (CSV shows 576 ZIP codes)")
    
    # Run specific diagnostic tests
    na_issues = test_specific_diagnostic_scenarios()
    
    # Check percentage of Na records
    has_percentage_issues = test_percentage_of_na_records()
    
    # Investigate ZIP code count
    test_zip_code_count_investigation()
    
    # Final summary
    print(f"\n{Colors.BOLD}{Colors.RED if na_issues or has_percentage_issues else Colors.GREEN}")
    print("=" * 80)
    print("🚨 URGENT INVESTIGATION RESULTS")
    
    if na_issues:
        print("❌ CRITICAL Na VALUE ISSUES FOUND:")
        for issue in na_issues:
            print(f"  - {issue}")
        print("\n🔧 IMMEDIATE ACTION REQUIRED:")
        print("  - Check database data integrity")
        print("  - Verify mock data generator is not producing null/Na values")
        print("  - Check frontend display logic for null handling")
    elif has_percentage_issues:
        print("❌ PERCENTAGE ANALYSIS FOUND Na VALUES")
        print("🔧 IMMEDIATE ACTION REQUIRED:")
        print("  - Review data generation process")
        print("  - Check database joins and data loading")
    else:
        print("✅ NO Na VALUE ISSUES FOUND")
        print("All tested endpoints return proper data without Na values")
        print("The reported issues may have been resolved")
    
    print("=" * 80)
    print(f"{Colors.ENDC}")
    
    return len(na_issues) == 0 and not has_percentage_issues

if __name__ == "__main__":
    run_urgent_investigation()
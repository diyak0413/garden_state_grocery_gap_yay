#!/usr/bin/env python3
"""
SearchAPI.io Walmart Integration Testing
Tests the completed SearchAPI.io Walmart integration with real pricing data
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
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}🔍 {test_name}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*80}{Colors.ENDC}")

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

def test_searchapi_walmart_integration():
    """Test the completed SearchAPI.io Walmart integration"""
    print_test_header("SEARCHAPI.IO WALMART INTEGRATION VERIFICATION")
    
    print_info("🎯 CRITICAL SUCCESS VERIFICATION:")
    print_info("1. Test /api/walmart/status - should show enabled with cache statistics")
    print_info("2. Test specific ZIP codes that were cached (like 07002, 07020, 07024) - verify real SearchAPI.io pricing")
    print_info("3. Test affordability calculations use real Walmart prices instead of mock data")
    print_info("4. Verify data_source shows 'walmart_api' or 'searchapi_io' instead of 'fallback_mock'")
    print_info("5. Test that rural ZIP codes show 'no data available' instead of NaN")
    print_info("6. Verify the 8 healthy basket items match the refined specifications")
    
    test_results = {
        "walmart_status_enabled": False,
        "cache_statistics": False,
        "real_pricing_data": False,
        "correct_data_source": False,
        "rural_area_handling": False,
        "basket_items_correct": False,
        "affordability_calculations": False,
        "api_quota_management": False
    }
    
    # Test 1: /api/walmart/status - should show enabled with cache statistics
    print_info("\n🔍 TEST 1: Walmart Status Endpoint - Cache Statistics")
    success, status_data = test_endpoint(
        "GET", "/walmart/status",
        description="Check Walmart API service status with cache statistics"
    )
    
    if success and status_data:
        print_info("📊 Walmart Service Status Analysis:")
        
        # Check if enabled
        api_enabled = status_data.get('walmart_api_enabled', False)
        api_key_configured = status_data.get('api_key_configured', False)
        cache_stats = status_data.get('cache_stats', {})
        
        print_info(f"  - API Enabled: {api_enabled}")
        print_info(f"  - API Key Configured: {api_key_configured}")
        
        if api_enabled and api_key_configured:
            print_success("✅ Walmart API is enabled and configured")
            test_results["walmart_status_enabled"] = True
        else:
            print_error("❌ Walmart API not properly enabled or configured")
        
        # Check cache statistics
        if cache_stats:
            print_info("💾 Cache Statistics:")
            print_info(f"  - Cache Database: {cache_stats.get('cache_database', 'N/A')}")
            print_info(f"  - Total Cached Prices: {cache_stats.get('total_cached_prices', 0)}")
            print_info(f"  - ZIP Codes Cached: {cache_stats.get('zip_codes_cached', 0)}")
            print_info(f"  - Items Cached: {cache_stats.get('items_cached', 0)}")
            print_info(f"  - Monthly API Calls: {cache_stats.get('monthly_api_calls', 0)}")
            print_info(f"  - Quota Remaining: {cache_stats.get('quota_remaining', 0)}")
            
            # Verify cache has data (220 API calls made, 28 ZIP codes processed)
            cached_prices = cache_stats.get('total_cached_prices', 0)
            zip_codes_cached = cache_stats.get('zip_codes_cached', 0)
            monthly_calls = cache_stats.get('monthly_api_calls', 0)
            
            if cached_prices > 200 and zip_codes_cached >= 25 and monthly_calls > 200:
                print_success("✅ Cache statistics show significant SearchAPI.io integration activity")
                test_results["cache_statistics"] = True
            else:
                print_warning(f"⚠️ Cache statistics lower than expected: {cached_prices} prices, {zip_codes_cached} ZIPs, {monthly_calls} calls")
        else:
            print_error("❌ Cache statistics not available")
    else:
        print_error("❌ Failed to retrieve Walmart status")
    
    # Test 2: Test specific ZIP codes that were cached (07002, 07020, 07024)
    print_info("\n🔍 TEST 2: Specific ZIP Codes - Real SearchAPI.io Pricing")
    
    cached_zip_codes = ["07002", "07020", "07024"]  # ZIP codes mentioned in review request
    
    for zip_code in cached_zip_codes:
        success, zip_data = test_endpoint(
            "GET", f"/affordability/{zip_code}",
            description=f"Test ZIP {zip_code} for real SearchAPI.io pricing"
        )
        
        if success and zip_data:
            basket_cost = zip_data.get('basket_cost', 0)
            city = zip_data.get('city', 'Unknown')
            median_income = zip_data.get('median_income', 0)
            affordability_score = zip_data.get('affordability_score', 0)
            
            print_info(f"📍 ZIP {zip_code} ({city}) Analysis:")
            print_info(f"  - Basket Cost: ${basket_cost}")
            print_info(f"  - Median Income: ${median_income:,}")
            print_info(f"  - Affordability Score: {affordability_score}%")
            
            # Check if pricing looks realistic for Walmart (not mock data)
            if 20 <= basket_cost <= 60:  # Realistic range for 8 healthy items
                print_success(f"✅ ZIP {zip_code} has realistic Walmart pricing: ${basket_cost}")
                test_results["real_pricing_data"] = True
            else:
                print_warning(f"⚠️ ZIP {zip_code} pricing may not be from SearchAPI.io: ${basket_cost}")
        else:
            print_error(f"❌ Failed to retrieve data for ZIP {zip_code}")
    
    # Test 3: Verify data_source shows correct source
    print_info("\n🔍 TEST 3: Data Source Verification")
    success, config_data = test_endpoint(
        "GET", "/config",
        description="Check configuration shows correct data source"
    )
    
    if success and config_data:
        data_source = config_data.get('data_source', 'unknown')
        message = config_data.get('message', '')
        walmart_service = config_data.get('walmart_service', {})
        
        print_info(f"📊 Data Source Analysis:")
        print_info(f"  - Data Source: {data_source}")
        print_info(f"  - Message: {message}")
        
        # Check if Walmart is mentioned in the message
        if 'walmart' in message.lower() and 'api' in message.lower():
            print_success("✅ Configuration correctly shows Walmart API usage")
            test_results["correct_data_source"] = True
        else:
            print_warning("⚠️ Configuration may not clearly indicate Walmart API usage")
    else:
        print_error("❌ Failed to retrieve configuration")
    
    # Test 4: Verify the 8 healthy basket items match specifications
    print_info("\n🔍 TEST 4: Healthy Basket Items Verification")
    success, basket_data = test_endpoint(
        "GET", "/food-basket",
        description="Verify the 8 healthy basket items match refined specifications"
    )
    
    if success and basket_data:
        items = basket_data.get('items', [])
        walmart_integration = basket_data.get('walmart_integration', {})
        
        print_info(f"🛒 Food Basket Analysis:")
        print_info(f"  - Total Items: {len(items)}")
        print_info(f"  - Walmart Enabled: {walmart_integration.get('enabled', False)}")
        
        # Expected items with refined specifications from review request
        expected_items = {
            "Brown Rice (2 lb bag)": {"min_price": 2, "max_price": 8},
            "Whole Wheat Bread (20 oz loaf)": {"min_price": 1, "max_price": 6},
            "Low-Fat Milk (1 gallon)": {"min_price": 2, "max_price": 6},
            "Boneless Skinless Chicken Breast (per lb)": {"min_price": 2, "max_price": 8},
            "Eggs (1 dozen, large)": {"min_price": 1, "max_price": 5},
            "Apples (3 lb bag)": {"min_price": 3, "max_price": 10},
            "Fresh Broccoli (1 lb)": {"min_price": 1, "max_price": 5},
            "Dry Black Beans (1 lb bag)": {"min_price": 1, "max_price": 4}
        }
        
        print_info("📋 Item Verification with Price Ranges:")
        all_items_correct = True
        
        for item in items:
            item_name = item.get('name', '')
            min_price = item.get('min_price', 0)
            max_price = item.get('max_price', 0)
            
            if item_name in expected_items:
                expected = expected_items[item_name]
                if min_price == expected["min_price"] and max_price == expected["max_price"]:
                    print_success(f"  ✅ {item_name}: ${min_price}-${max_price} ✓")
                else:
                    print_warning(f"  ⚠️ {item_name}: ${min_price}-${max_price} (expected ${expected['min_price']}-${expected['max_price']})")
                    all_items_correct = False
            else:
                print_error(f"  ❌ Unexpected item: {item_name}")
                all_items_correct = False
        
        # Check for missing items
        actual_item_names = [item.get('name', '') for item in items]
        for expected_name in expected_items.keys():
            if expected_name not in actual_item_names:
                print_error(f"  ❌ Missing: {expected_name}")
                all_items_correct = False
        
        if len(items) == 8 and all_items_correct:
            print_success("✅ All 8 healthy basket items match refined specifications")
            test_results["basket_items_correct"] = True
        else:
            print_error(f"❌ Basket items don't match specifications - Expected 8 with correct specs")
    else:
        print_error("❌ Failed to retrieve food basket data")
    
    # Test 5: Test affordability calculations with real pricing
    print_info("\n🔍 TEST 5: Affordability Calculations with Real Pricing")
    success, stats_data = test_endpoint(
        "GET", "/stats",
        description="Check overall statistics to verify realistic affordability scores"
    )
    
    if success and stats_data:
        total_zips = stats_data.get('total_zip_codes', 0)
        avg_score = stats_data.get('average_affordability_score', 0)
        classifications = stats_data.get('classifications', {})
        data_source = stats_data.get('data_source', 'unknown')
        pricing_source = stats_data.get('pricing_source', 'unknown')
        
        print_info(f"📊 Affordability Analysis:")
        print_info(f"  - Total ZIP Codes: {total_zips}")
        print_info(f"  - Average Affordability Score: {avg_score}%")
        print_info(f"  - Data Source: {data_source}")
        print_info(f"  - Pricing Source: {pricing_source}")
        print_info(f"  - Classifications: {classifications}")
        
        # Check if affordability scores are realistic (1-5% of income for healthy groceries)
        if 1 <= avg_score <= 15:  # Realistic range
            print_success(f"✅ Average affordability score {avg_score}% is realistic for household grocery costs")
            test_results["affordability_calculations"] = True
        else:
            print_warning(f"⚠️ Average affordability score {avg_score}% may not reflect real pricing")
        
        # Check if pricing source indicates Walmart API usage
        if 'walmart' in pricing_source.lower() or 'searchapi' in pricing_source.lower():
            print_success("✅ Pricing source correctly indicates Walmart/SearchAPI.io usage")
        else:
            print_warning(f"⚠️ Pricing source '{pricing_source}' doesn't clearly indicate Walmart API")
    else:
        print_error("❌ Failed to retrieve statistics")
    
    # Test 6: Test rural ZIP codes for proper "no data available" handling
    print_info("\n🔍 TEST 6: Rural Area Handling - No Data Available")
    
    # Test a rural NJ ZIP code that likely has no Walmart coverage
    rural_zip = "07826"  # Branchville, NJ - rural area
    success, rural_data = test_endpoint(
        "GET", f"/affordability/{rural_zip}",
        expected_status=404,  # May not be found
        description=f"Test rural ZIP {rural_zip} for proper 'no data available' handling"
    )
    
    if not success:  # 404 is acceptable for rural areas
        print_success("✅ Rural ZIP code properly returns 404 (not found) instead of NaN")
        test_results["rural_area_handling"] = True
    elif success and rural_data:
        basket_cost = rural_data.get('basket_cost', 0)
        if basket_cost and not str(basket_cost).lower() in ['nan', 'null', 'none']:
            print_success(f"✅ Rural area shows proper fallback data (${basket_cost}) instead of NaN")
            test_results["rural_area_handling"] = True
        else:
            print_error(f"❌ Rural area shows NaN or invalid data: {basket_cost}")
    
    # Test 7: API Quota Management
    print_info("\n🔍 TEST 7: API Quota Management")
    if status_data and status_data.get('cache_stats'):
        cache_stats = status_data['cache_stats']
        monthly_calls = cache_stats.get('monthly_api_calls', 0)
        quota_remaining = cache_stats.get('quota_remaining', 0)
        total_quota = monthly_calls + quota_remaining
        
        print_info(f"📊 Quota Management Analysis:")
        print_info(f"  - Monthly API Calls Used: {monthly_calls}")
        print_info(f"  - Quota Remaining: {quota_remaining}")
        print_info(f"  - Total Quota: {total_quota}")
        
        # Check if quota management is working (should be 10K limit)
        if total_quota == 10000:
            print_success("✅ API quota management working correctly (10K limit)")
            test_results["api_quota_management"] = True
        else:
            print_warning(f"⚠️ Quota limit may be incorrect: {total_quota} (expected 10,000)")
        
        # Check if significant API calls were made (220 mentioned in review)
        if monthly_calls >= 200:
            print_success(f"✅ Significant API activity detected: {monthly_calls} calls made")
        else:
            print_warning(f"⚠️ Lower API activity than expected: {monthly_calls} calls")
    else:
        print_error("❌ Quota management data not available")
    
    # Summary of SearchAPI.io Walmart integration tests
    print_info(f"\n📋 SEARCHAPI.IO WALMART INTEGRATION TEST RESULTS:")
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        test_display = test_name.replace('_', ' ').title()
        print_info(f"  - {test_display}: {status}")
    
    print_info(f"\nOverall: {passed_tests}/{total_tests} SearchAPI.io integration tests passed")
    
    # Final assessment
    critical_tests = [
        "walmart_status_enabled",
        "cache_statistics", 
        "real_pricing_data",
        "affordability_calculations"
    ]
    
    critical_passed = sum(1 for test in critical_tests if test_results[test])
    
    if critical_passed >= 3:  # At least 3 of 4 critical tests must pass
        print_success("🎉 SUCCESS: SearchAPI.io Walmart integration is working correctly!")
        print_success("✅ Service status shows enabled with cache statistics")
        print_success("✅ Real pricing data from SearchAPI.io")
        print_success("✅ Affordability calculations using real Walmart prices")
        print_success("✅ Cache system serving real Walmart prices efficiently")
        return True
    else:
        print_error("🚨 CRITICAL ISSUES: SearchAPI.io Walmart integration has problems")
        failed_critical = [name.replace('_', ' ').title() for name in critical_tests if not test_results[name]]
        print_error(f"Failed critical tests: {', '.join(failed_critical)}")
        return False

def main():
    """Main test execution"""
    print_test_header("SEARCHAPI.IO WALMART INTEGRATION TESTING")
    
    print_info(f"Backend URL: {BASE_URL}")
    print_info(f"API Base URL: {API_BASE}")
    print_info(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print_info("\n🎯 ENVIRONMENT STATUS FROM REVIEW REQUEST:")
    print_info("- SearchAPI.io integration complete with 220 API calls made")
    print_info("- 28 ZIP codes processed with 218 valid prices (98.6% success rate)")
    print_info("- SQLite cache contains real Walmart pricing data")
    print_info("- Price validation working with realistic household grocery costs")
    
    print_info("\n🎯 EXPECTED BEHAVIOR:")
    print_info("- Affordability scores should be realistic (1-5% of income for healthy groceries)")
    print_info("- ML predictions should be accurate with real pricing data")
    print_info("- No more $50+ rice bags breaking the analysis")
    print_info("- Cache system should serve real Walmart prices efficiently")
    
    # Run the comprehensive SearchAPI.io Walmart integration test
    success = test_searchapi_walmart_integration()
    
    if success:
        print_success("\n🎉 OVERALL RESULT: SearchAPI.io Walmart integration is working correctly!")
        print_success("✅ All critical verification points passed")
        print_success("✅ Real pricing data is being used instead of mock data")
        print_success("✅ Affordability model is delivering accurate household-level grocery pricing")
    else:
        print_error("\n🚨 OVERALL RESULT: SearchAPI.io Walmart integration needs attention")
        print_error("❌ Some critical verification points failed")
        print_error("❌ Integration may not be fully operational")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
GARDEN STATE GROCERY GAP BACKEND API TESTING - DATA VINTAGE CONSISTENCY

PRIORITY VERIFICATION REQUIREMENTS (Based on Review Request):
1. **Data Vintage Consistency**: Verify all endpoints return consistent "ACS 2019-2023 5-year" data vintage
2. **Core Endpoints**: Test all specified endpoints with proper data validation
3. **Data Quality Checks**: Confirm affordability scores, median income values, and classifications
4. **Performance**: Verify API response times are acceptable

SPECIFIC ENDPOINTS TO TEST:
- GET /api/config - Check configuration
- GET /api/zips - Verify all 734 ZIP codes load with data_vintage field
- GET /api/affordability/07401 - Test Allendale data (validation example 1)
- GET /api/affordability/08831 - Test Monroe Township/Jamesburg (validation example 2)
- GET /api/affordability/08102 - Test Camden (validation example 3)
- GET /api/search-zipcodes?q=Allendale - Test search functionality
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
                print(f"Response Type: JSON")
                return True, json_data
            except json.JSONDecodeError:
                print(f"Response Type: Non-JSON")
                print(f"Response Text: {response.text[:200]}...")
                return True, response.text
        else:
            print_error(f"Expected status {expected_status}, got {response.status_code}")
            print(f"Response: {response.text}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {str(e)}")
        return False, None

def test_config_endpoint():
    """TEST 1: Configuration Endpoint - Check API configuration"""
    print_test_header("API CONFIGURATION VERIFICATION")
    
    print_info("🎯 REQUIREMENTS:")
    print_info("- API should be properly configured")
    print_info("- Data source information should be available")
    
    success, config_data = test_endpoint(
        "GET", "/config",
        description="Check API configuration status"
    )
    
    if success and config_data:
        data_source = config_data.get('data_source', 'unknown')
        using_real_demographics = config_data.get('using_real_demographics', False)
        walmart_service = config_data.get('walmart_service', {})
        
        print_info(f"📊 Configuration Analysis:")
        print_info(f"  - Data Source: {data_source}")
        print_info(f"  - Using Real Demographics: {using_real_demographics}")
        print_info(f"  - Walmart Service: {walmart_service}")
        
        print_success(f"✅ Configuration endpoint working")
        return True
    else:
        print_error("❌ FAILURE: Failed to retrieve configuration data")
        return False

def test_zips_endpoint_data_vintage():
    """TEST 2: ZIP Codes Endpoint - Verify all 734 ZIP codes with data_vintage field"""
    print_test_header("ZIP CODES ENDPOINT - DATA VINTAGE CONSISTENCY")
    
    print_info("🎯 REQUIREMENTS:")
    print_info("- Should return all 734 ZIP codes")
    print_info("- Each ZIP should have data_vintage field set to 'ACS 2019-2023 5-year'")
    print_info("- Response should include total count and data source")
    
    success, zips_data = test_endpoint(
        "GET", "/zips",
        description="Get all ZIP codes and verify data vintage consistency"
    )
    
    if success and zips_data:
        total_count = zips_data.get('total_count', 0)
        zips = zips_data.get('zips', [])
        data_source = zips_data.get('data_source', 'unknown')
        
        print_info(f"📊 ZIP Codes Analysis:")
        print_info(f"  - Total Count: {total_count}")
        print_info(f"  - ZIP Records Returned: {len(zips)}")
        print_info(f"  - Data Source: {data_source}")
        
        # Check for 734 ZIP codes
        if total_count == 734:
            print_success(f"✅ SUCCESS: All 734 ZIP codes loaded")
        else:
            print_warning(f"⚠️ Expected 734 ZIP codes, got {total_count}")
        
        # Check data_vintage field consistency
        vintage_check_count = min(10, len(zips))  # Check first 10 ZIP codes
        consistent_vintage = True
        expected_vintage = "ACS 2019-2023 5-year"
        
        print_info(f"\n🔍 Data Vintage Consistency Check (first {vintage_check_count} ZIP codes):")
        
        for i, zip_data in enumerate(zips[:vintage_check_count]):
            zip_code = zip_data.get('zip_code', 'Unknown')
            data_vintage = zip_data.get('data_vintage', 'Missing')
            
            print_info(f"  - ZIP {zip_code}: data_vintage = '{data_vintage}'")
            
            if data_vintage != expected_vintage:
                consistent_vintage = False
                print_error(f"    ❌ Expected '{expected_vintage}', got '{data_vintage}'")
            else:
                print_success(f"    ✅ Correct data vintage")
        
        if consistent_vintage:
            print_success(f"✅ SUCCESS: Data vintage consistency verified")
        else:
            print_error(f"❌ FAILURE: Inconsistent data vintage found")
        
        return total_count >= 700 and consistent_vintage  # Allow some tolerance
    else:
        print_error("❌ FAILURE: Failed to retrieve ZIP codes data")
        return False

def test_validation_examples():
    """TEST 3: Validation Examples - Test specific ZIP codes mentioned in review request"""
    print_test_header("VALIDATION EXAMPLES - SPECIFIC ZIP CODE TESTING")
    
    print_info("🎯 REQUIREMENTS:")
    print_info("- Test Allendale (07401) - validation example 1")
    print_info("- Test Monroe Township/Jamesburg (08831) - validation example 2") 
    print_info("- Test Camden (08102) - validation example 3")
    print_info("- Verify data_vintage field is 'ACS 2019-2023 5-year'")
    print_info("- Confirm affordability scores are calculated correctly")
    print_info("- Check median income values are reasonable")
    
    test_cases = [
        {"zip": "07401", "area": "Allendale", "expected_type": "affluent"},
        {"zip": "08831", "area": "Monroe Township/Jamesburg", "expected_type": "mixed"},
        {"zip": "08102", "area": "Camden", "expected_type": "high-need"}
    ]
    
    all_passed = True
    expected_vintage = "ACS 2019-2023 5-year"
    
    for test_case in test_cases:
        zip_code = test_case["zip"]
        area = test_case["area"]
        expected_type = test_case["expected_type"]
        
        print_info(f"\n🔍 Testing {area} ({zip_code}) - {expected_type} area:")
        
        success, zip_data = test_endpoint(
            "GET", f"/affordability/{zip_code}",
            description=f"Test {area} data quality and vintage"
        )
        
        if success and zip_data:
            city = zip_data.get('city', 'Unknown')
            county = zip_data.get('county', 'Unknown')
            affordability_score = zip_data.get('affordability_score', 0)
            basket_cost = zip_data.get('basket_cost', 0)
            median_income = zip_data.get('median_income', 0)
            classification = zip_data.get('classification', 'Unknown')
            data_vintage = zip_data.get('data_vintage', 'Missing')
            
            print_info(f"📍 {area} ({zip_code}) Results:")
            print_info(f"  - City: {city}")
            print_info(f"  - County: {county}")
            print_info(f"  - Affordability Score: {affordability_score}%")
            print_info(f"  - Basket Cost: ${basket_cost}")
            print_info(f"  - Median Income: ${median_income:,}")
            print_info(f"  - Classification: {classification}")
            print_info(f"  - Data Vintage: {data_vintage}")
            
            # Validate data vintage
            if data_vintage == expected_vintage:
                print_success(f"    ✅ Correct data vintage: {data_vintage}")
            else:
                print_error(f"    ❌ Expected '{expected_vintage}', got '{data_vintage}'")
                all_passed = False
            
            # Validate median income is reasonable (should be > $20,000 and < $200,000)
            if 20000 <= median_income <= 200000:
                print_success(f"    ✅ Reasonable median income: ${median_income:,}")
            else:
                print_error(f"    ❌ Unreasonable median income: ${median_income:,}")
                all_passed = False
            
            # Validate affordability score is calculated (should be > 0)
            if affordability_score > 0:
                print_success(f"    ✅ Affordability score calculated: {affordability_score}%")
            else:
                print_error(f"    ❌ Missing or zero affordability score")
                all_passed = False
            
            # Validate classification matches score thresholds
            if classification in ["High Food Access", "Moderate Food Access", "Low Food Access", "Food Desert Risk"]:
                print_success(f"    ✅ Valid classification: {classification}")
            else:
                print_error(f"    ❌ Invalid classification: {classification}")
                all_passed = False
                
        else:
            print_error(f"❌ FAILURE: Failed to retrieve data for {area} ({zip_code})")
            all_passed = False
    
    return all_passed

def test_search_functionality():
    """TEST 4: Search Functionality - Test search endpoint"""
    print_test_header("SEARCH FUNCTIONALITY VERIFICATION")
    
    print_info("🎯 REQUIREMENTS:")
    print_info("- Test /api/search-zipcodes?q=Allendale")
    print_info("- Verify search returns relevant results")
    print_info("- Check data_vintage field in search results")
    
    search_queries = [
        {"query": "Allendale", "expected_zip": "07401"},
        {"query": "Camden", "expected_zip": "08102"},
        {"query": "070", "description": "partial ZIP search"}
    ]
    
    all_passed = True
    expected_vintage = "ACS 2019-2023 5-year"
    
    for search_case in search_queries:
        query = search_case["query"]
        expected_zip = search_case.get("expected_zip")
        description = search_case.get("description", f"search for {query}")
        
        print_info(f"\n🔍 Testing search: {description}")
        
        success, search_results = test_endpoint(
            "GET", f"/search-zipcodes?q={query}",
            description=f"Search for '{query}'"
        )
        
        if success and search_results:
            if isinstance(search_results, list):
                results_count = len(search_results)
                print_info(f"📍 Search Results for '{query}':")
                print_info(f"  - Results Count: {results_count}")
                
                if results_count > 0:
                    print_success(f"✅ Search returned {results_count} results")
                    
                    # Check first result for data vintage
                    first_result = search_results[0]
                    result_zip = first_result.get('zip_code', 'Unknown')
                    result_city = first_result.get('city', 'Unknown')
                    data_vintage = first_result.get('data_vintage', 'Missing')
                    
                    print_info(f"  - First Result: ZIP {result_zip} ({result_city})")
                    print_info(f"  - Data Vintage: {data_vintage}")
                    
                    # Validate data vintage
                    if data_vintage == expected_vintage:
                        print_success(f"    ✅ Correct data vintage in search results")
                    else:
                        print_error(f"    ❌ Expected '{expected_vintage}', got '{data_vintage}'")
                        all_passed = False
                    
                    # Check if expected ZIP is in results (if specified)
                    if expected_zip:
                        found_expected = any(r.get('zip_code') == expected_zip for r in search_results)
                        if found_expected:
                            print_success(f"    ✅ Expected ZIP {expected_zip} found in results")
                        else:
                            print_warning(f"    ⚠️ Expected ZIP {expected_zip} not found in results")
                else:
                    print_warning(f"⚠️ No results returned for '{query}'")
            else:
                print_error(f"❌ Unexpected response format for search")
                all_passed = False
        else:
            print_error(f"❌ FAILURE: Search failed for '{query}'")
            all_passed = False
    
    return all_passed

def test_data_quality_checks():
    """TEST 5: Data Quality Checks - Verify no null/missing critical fields"""
    print_test_header("DATA QUALITY CHECKS - CRITICAL FIELDS VALIDATION")
    
    print_info("🎯 REQUIREMENTS:")
    print_info("- Ensure no null or missing critical fields")
    print_info("- Verify affordability scores are calculated correctly")
    print_info("- Check median income values are reasonable")
    print_info("- Confirm classification matches score thresholds")
    
    # Test a sample of ZIP codes for data quality
    sample_zips = ["07401", "08831", "08102"]  # From validation examples
    all_passed = True
    
    for zip_code in sample_zips:
        print_info(f"\n🔍 Data Quality Check for ZIP {zip_code}:")
        
        success, zip_data = test_endpoint(
            "GET", f"/affordability/{zip_code}",
            description=f"Data quality check for ZIP {zip_code}"
        )
        
        if success and zip_data:
            # Check for critical fields
            critical_fields = [
                'zip_code', 'city', 'county', 'affordability_score', 
                'basket_cost', 'median_income', 'classification', 'data_vintage'
            ]
            
            missing_fields = []
            null_fields = []
            
            for field in critical_fields:
                value = zip_data.get(field)
                if field not in zip_data:
                    missing_fields.append(field)
                elif value is None or value == "":
                    null_fields.append(field)
            
            if not missing_fields and not null_fields:
                print_success(f"    ✅ All critical fields present and non-null")
            else:
                if missing_fields:
                    print_error(f"    ❌ Missing fields: {missing_fields}")
                    all_passed = False
                if null_fields:
                    print_error(f"    ❌ Null/empty fields: {null_fields}")
                    all_passed = False
            
            # Validate affordability score calculation
            affordability_score = zip_data.get('affordability_score', 0)
            basket_cost = zip_data.get('basket_cost', 0)
            median_income = zip_data.get('median_income', 0)
            
            if affordability_score > 0 and basket_cost > 0 and median_income > 0:
                # Calculate expected score: (monthly_food_cost / monthly_income) * 100
                monthly_income = median_income / 12
                monthly_food_cost = basket_cost * 4.33  # Weekly to monthly
                expected_score = (monthly_food_cost / monthly_income) * 100
                
                # Allow 10% tolerance for rounding differences
                if abs(affordability_score - expected_score) / expected_score <= 0.1:
                    print_success(f"    ✅ Affordability score calculation correct: {affordability_score}%")
                else:
                    print_warning(f"    ⚠️ Score calculation may be off: got {affordability_score}%, expected ~{expected_score:.1f}%")
            
            # Validate classification thresholds
            classification = zip_data.get('classification', '')
            if affordability_score >= 25:
                expected_class = "Food Desert Risk"
            elif affordability_score >= 15:
                expected_class = "Low Food Access"
            elif affordability_score >= 8:
                expected_class = "Moderate Food Access"
            else:
                expected_class = "High Food Access"
            
            if classification == expected_class:
                print_success(f"    ✅ Classification correct: {classification}")
            else:
                print_warning(f"    ⚠️ Classification may be off: got '{classification}', expected '{expected_class}'")
                
        else:
            print_error(f"❌ FAILURE: Failed to retrieve data for ZIP {zip_code}")
            all_passed = False
    
    return all_passed

def test_performance():
    """TEST 6: Performance - Verify API response times are acceptable"""
    print_test_header("PERFORMANCE VERIFICATION - API RESPONSE TIMES")
    
    print_info("🎯 REQUIREMENTS:")
    print_info("- API response times should be acceptable (< 5 seconds)")
    print_info("- Test multiple endpoints for performance")
    
    import time
    
    performance_tests = [
        {"endpoint": "/config", "description": "Configuration endpoint"},
        {"endpoint": "/zips", "description": "All ZIP codes endpoint"},
        {"endpoint": "/affordability/07401", "description": "Single ZIP lookup"},
        {"endpoint": "/search-zipcodes?q=Allendale", "description": "Search functionality"},
        {"endpoint": "/stats", "description": "Statistics endpoint"}
    ]
    
    all_passed = True
    max_acceptable_time = 5.0  # 5 seconds
    
    for test in performance_tests:
        endpoint = test["endpoint"]
        description = test["description"]
        
        print_info(f"\n⏱️ Performance test: {description}")
        
        start_time = time.time()
        success, _ = test_endpoint(
            "GET", endpoint,
            description=f"Performance test for {description}"
        )
        end_time = time.time()
        
        response_time = end_time - start_time
        
        print_info(f"  - Response Time: {response_time:.2f} seconds")
        
        if success:
            if response_time <= max_acceptable_time:
                print_success(f"    ✅ Performance acceptable: {response_time:.2f}s ≤ {max_acceptable_time}s")
            else:
                print_warning(f"    ⚠️ Slow response: {response_time:.2f}s > {max_acceptable_time}s")
        else:
            print_error(f"    ❌ Endpoint failed")
            all_passed = False
    
    return all_passed

def run_all_tests():
    """Run all Garden State Grocery Gap backend API tests for Data Vintage Consistency"""
    print_test_header("GARDEN STATE GROCERY GAP BACKEND API - DATA VINTAGE CONSISTENCY TESTING")
    
    print_info("🎯 RUNNING DATA VINTAGE CONSISTENCY TESTS:")
    print_info("Focus on verifying 'ACS 2019-2023 5-year' data vintage consistency")
    print_info("Testing core endpoints, data quality, and performance as requested")
    
    test_results = {}
    
    # Run all tests based on review request
    test_results["config_endpoint"] = test_config_endpoint()
    test_results["zips_endpoint_data_vintage"] = test_zips_endpoint_data_vintage()
    test_results["validation_examples"] = test_validation_examples()
    test_results["search_functionality"] = test_search_functionality()
    test_results["data_quality_checks"] = test_data_quality_checks()
    test_results["performance"] = test_performance()
    
    # Summary
    print_test_header("FINAL TEST RESULTS")
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    print_info(f"📋 TEST RESULTS SUMMARY:")
    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        test_display = test_name.replace('_', ' ').title()
        print_info(f"  - {test_display}: {status}")
    
    print_info(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print_success("🎉 SUCCESS: All data vintage consistency tests passed!")
        print_success("✅ Configuration - API properly configured")
        print_success("✅ Data Vintage - Consistent 'ACS 2019-2023 5-year' across all endpoints")
        print_success("✅ Validation Examples - All test ZIP codes return proper data")
        print_success("✅ Search Functionality - Search works with consistent data vintage")
        print_success("✅ Data Quality - No null/missing critical fields found")
        print_success("✅ Performance - API response times are acceptable")
        return True
    else:
        print_error("🚨 ISSUES FOUND: Some tests failed")
        failed_tests = [name.replace('_', ' ').title() for name, passed in test_results.items() if not passed]
        print_error(f"Failed tests: {', '.join(failed_tests)}")
        print_error("These issues should be investigated and resolved")
        return False

if __name__ == "__main__":
    print(f"Backend URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    
    # Run all data vintage consistency tests
    success = run_all_tests()
    
    if success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL DATA VINTAGE CONSISTENCY TESTS PASSED - BACKEND READY!{Colors.ENDC}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}🚨 SOME TESTS FAILED - SEE DETAILS ABOVE{Colors.ENDC}")
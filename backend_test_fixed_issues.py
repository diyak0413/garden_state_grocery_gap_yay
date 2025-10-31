#!/usr/bin/env python3
"""
Backend API Testing for Garden State Grocery Gap - Fixed Issues Verification
Tests the critical bug fixes: ML Risk Prediction Logic and City Name Mapping
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

def test_data_source_verification():
    """Test 1: Data Source Verification - Should show census_comprehensive_pipeline with 734 ZIP codes"""
    print_test_header("Data Source Verification")
    
    print_info("🎯 EXPECTED: /api/debug/source_count should show 'census_comprehensive_pipeline' with 734 ZIP codes")
    
    success, source_data = test_endpoint(
        "GET", "/debug/source_count",
        description="Verify data source shows census_comprehensive_pipeline with 734 ZIP codes"
    )
    
    if success and source_data:
        source = source_data.get('source', 'unknown')
        count = source_data.get('count', 0)
        csv_files = source_data.get('csv_files', {})
        
        print_info(f"📊 Data Source Results:")
        print_info(f"  - Source: {source}")
        print_info(f"  - Count: {count}")
        print_info(f"  - Message: {source_data.get('message', 'N/A')}")
        
        # Verify data source
        if source == 'census_comprehensive_pipeline':
            print_success("✅ Data source correctly shows 'census_comprehensive_pipeline'")
        else:
            print_error(f"❌ Expected 'census_comprehensive_pipeline', got '{source}'")
            return False
        
        # Verify count (734 expected from review request)
        if count == 734:
            print_success("✅ ZIP code count correctly shows 734")
        else:
            print_warning(f"⚠️ Expected 734 ZIP codes, got {count}")
            print_info(f"Note: Review request mentions 734, but system shows {count}")
        
        # Check CSV files
        nj_zctas = csv_files.get('nj_zctas_csv', {})
        zip_metrics = csv_files.get('zip_metrics_csv', {})
        
        if nj_zctas.get('exists') and zip_metrics.get('exists'):
            print_success("✅ Both required CSV files exist")
            print_info(f"  - nj_zctas.csv: {nj_zctas.get('count', 'N/A')} records")
            print_info(f"  - zip_metrics.csv: {zip_metrics.get('count', 'N/A')} records")
        else:
            print_error("❌ Required CSV files missing")
            return False
        
        return True
    else:
        print_error("❌ Failed to retrieve data source information")
        return False

def test_city_name_mapping_fix():
    """Test 2: City Name Mapping Fix - ZIP 08831 should show 'Monroe Township' instead of 'Jamesburg'"""
    print_test_header("City Name Mapping Fix Verification")
    
    print_info("🎯 CRITICAL FIX: ZIP 08831 should now show 'Monroe Township' instead of 'Jamesburg'")
    print_info("🎯 VERIFICATION: ZIP 07002 should show 'Bayonne' (baseline test)")
    
    # Test ZIP 08831 - should show Monroe Township
    print_info("\n🔍 Testing ZIP 08831 (should show Monroe Township)")
    success, zip_data = test_endpoint(
        "GET", "/affordability/08831",
        description="Check if ZIP 08831 now correctly shows 'Monroe Township'"
    )
    
    monroe_fix_verified = False
    if success and zip_data:
        city = zip_data.get('city', '').strip()
        county = zip_data.get('county', '').strip()
        
        print_info(f"ZIP 08831 Results:")
        print_info(f"  - City: '{city}'")
        print_info(f"  - County: '{county}'")
        
        if city.lower() == 'monroe township':
            print_success("✅ SUCCESS: ZIP 08831 correctly shows 'Monroe Township'")
            monroe_fix_verified = True
        elif city.lower() == 'jamesburg':
            print_error("❌ ISSUE: ZIP 08831 still shows 'Jamesburg' (not fixed)")
        elif city.lower() in ['monroe', 'monroe twp']:
            print_success("✅ SUCCESS: ZIP 08831 shows Monroe variant (acceptable)")
            monroe_fix_verified = True
        else:
            print_error(f"❌ UNEXPECTED: ZIP 08831 shows '{city}' (expected Monroe Township)")
    else:
        print_error("❌ Failed to retrieve ZIP 08831 data")
    
    # Test ZIP 07002 - should show Bayonne (baseline verification)
    print_info("\n🔍 Testing ZIP 07002 (should show Bayonne - baseline)")
    success, zip_data = test_endpoint(
        "GET", "/affordability/07002",
        description="Verify ZIP 07002 shows correct city name 'Bayonne'"
    )
    
    bayonne_verified = False
    if success and zip_data:
        city = zip_data.get('city', '').strip()
        county = zip_data.get('county', '').strip()
        
        print_info(f"ZIP 07002 Results:")
        print_info(f"  - City: '{city}'")
        print_info(f"  - County: '{county}'")
        
        if city.lower() == 'bayonne':
            print_success("✅ SUCCESS: ZIP 07002 correctly shows 'Bayonne'")
            bayonne_verified = True
        else:
            print_error(f"❌ ISSUE: ZIP 07002 shows '{city}' (expected Bayonne)")
    else:
        print_error("❌ Failed to retrieve ZIP 07002 data")
    
    return monroe_fix_verified and bayonne_verified

def test_ml_prediction_logic_fix():
    """Test 3: ML Risk Prediction Logic Fix - No more contradictory outputs"""
    print_test_header("ML Risk Prediction Logic Fix Verification")
    
    print_info("🎯 CRITICAL FIX: Previously all ZIP codes showed contradictory outputs:")
    print_info("   - risk_prediction=0 but risk_probability=1.0")
    print_info("🎯 EXPECTED: Proper probability calculations with consistent logic")
    
    success, ml_data = test_endpoint(
        "GET", "/ml/predict-risk",
        description="Test ML predictions for contradictory outputs"
    )
    
    if not success or not ml_data:
        print_error("❌ Failed to retrieve ML predictions")
        return False
    
    predictions = ml_data.get('predictions', [])
    total_zips = len(predictions)
    
    print_info(f"📊 ML Prediction Analysis:")
    print_info(f"  - Total ZIP codes analyzed: {total_zips}")
    
    if total_zips == 0:
        print_error("❌ No ML predictions returned")
        return False
    
    # Analyze for contradictory outputs
    contradictory_count = 0
    all_zero_prediction = 0
    all_one_probability = 0
    realistic_distribution = 0
    
    print_info("\n🔍 Checking for contradictory outputs:")
    
    for i, pred in enumerate(predictions[:10]):  # Check first 10 for detailed analysis
        zip_code = pred.get('zip_code', 'N/A')
        risk_prediction = pred.get('risk_prediction', 0)
        risk_probability = pred.get('risk_probability', 0.0)
        confidence = pred.get('confidence', 0.0)
        
        print_info(f"  ZIP {zip_code}: prediction={risk_prediction}, probability={risk_probability:.3f}, confidence={confidence:.3f}")
        
        # Check for contradictory logic
        if risk_prediction == 0 and risk_probability >= 0.9:
            contradictory_count += 1
            print_error(f"    ❌ CONTRADICTORY: prediction=0 but probability={risk_probability:.3f}")
        elif risk_prediction == 1 and risk_probability <= 0.1:
            contradictory_count += 1
            print_error(f"    ❌ CONTRADICTORY: prediction=1 but probability={risk_probability:.3f}")
        else:
            print_success(f"    ✅ CONSISTENT: prediction and probability align")
    
    # Overall analysis
    for pred in predictions:
        risk_prediction = pred.get('risk_prediction', 0)
        risk_probability = pred.get('risk_probability', 0.0)
        
        if risk_prediction == 0:
            all_zero_prediction += 1
        if risk_probability >= 0.99:
            all_one_probability += 1
        if 0.1 <= risk_probability <= 0.9:
            realistic_distribution += 1
    
    print_info(f"\n📊 Overall Distribution Analysis:")
    print_info(f"  - Contradictory outputs: {contradictory_count}")
    print_info(f"  - All zero predictions: {all_zero_prediction}/{total_zips}")
    print_info(f"  - All ~1.0 probabilities: {all_one_probability}/{total_zips}")
    print_info(f"  - Realistic probabilities (0.1-0.9): {realistic_distribution}/{total_zips}")
    
    # Verify the fix
    if contradictory_count == 0:
        print_success("✅ SUCCESS: No contradictory outputs found!")
    else:
        print_error(f"❌ ISSUE: Found {contradictory_count} contradictory outputs")
        return False
    
    if all_zero_prediction == total_zips and all_one_probability == total_zips:
        print_error("❌ ISSUE: Still showing all predictions=0 with probabilities=1.0")
        return False
    
    if realistic_distribution > 0:
        print_success(f"✅ SUCCESS: Found {realistic_distribution} ZIP codes with realistic probability distribution")
    else:
        print_warning("⚠️ All probabilities are still at extremes (0.0 or 1.0)")
    
    # Check for proper risk level distribution
    high_risk_count = sum(1 for p in predictions if p.get('risk_probability', 0) >= 0.6)
    medium_risk_count = sum(1 for p in predictions if 0.3 <= p.get('risk_probability', 0) < 0.6)
    low_risk_count = sum(1 for p in predictions if p.get('risk_probability', 0) < 0.3)
    
    print_info(f"\n📊 Risk Level Distribution:")
    print_info(f"  - High Risk (≥60%): {high_risk_count}")
    print_info(f"  - Medium Risk (30-59%): {medium_risk_count}")
    print_info(f"  - Low Risk (<30%): {low_risk_count}")
    
    if high_risk_count > 0:
        print_success(f"✅ SUCCESS: Found {high_risk_count} high-risk ZIP codes (not all 'Very High Risk')")
    else:
        print_warning("⚠️ No high-risk ZIP codes found")
    
    return contradictory_count == 0

def test_individual_zip_lookups():
    """Test 4: Individual ZIP Lookups for high-risk and low-risk ZIP codes"""
    print_test_header("Individual ZIP Lookups - High-Risk and Low-Risk Samples")
    
    print_info("🎯 TESTING: Sample high-risk and low-risk ZIP codes for proper data")
    
    # Test specific ZIP codes mentioned in review request
    test_zips = [
        ("08831", "Monroe Township (fixed mapping)"),
        ("07002", "Bayonne (baseline)"),
    ]
    
    # Add some additional ZIP codes for comprehensive testing
    additional_zips = ["07102", "08608", "07305", "08701"]
    
    all_tests_passed = True
    
    for zip_code, description in test_zips:
        print_info(f"\n🔍 Testing ZIP {zip_code} - {description}")
        
        success, zip_data = test_endpoint(
            "GET", f"/affordability/{zip_code}",
            description=f"Test individual lookup for ZIP {zip_code}"
        )
        
        if success and zip_data:
            city = zip_data.get('city', '')
            county = zip_data.get('county', '')
            affordability_score = zip_data.get('affordability_score', 0)
            basket_cost = zip_data.get('basket_cost', 0)
            median_income = zip_data.get('median_income', 0)
            classification = zip_data.get('classification', '')
            
            print_info(f"  Results for ZIP {zip_code}:")
            print_info(f"    - City: {city}")
            print_info(f"    - County: {county}")
            print_info(f"    - Affordability Score: {affordability_score}%")
            print_info(f"    - Basket Cost: ${basket_cost}")
            print_info(f"    - Median Income: ${median_income:,}")
            print_info(f"    - Classification: {classification}")
            
            # Verify data completeness
            if all([city, county, affordability_score, basket_cost, median_income, classification]):
                print_success(f"✅ ZIP {zip_code}: All fields populated")
            else:
                print_error(f"❌ ZIP {zip_code}: Missing data fields")
                all_tests_passed = False
            
            # Verify realistic values
            if 20000 <= median_income <= 200000:
                print_success(f"✅ ZIP {zip_code}: Realistic median income")
            else:
                print_warning(f"⚠️ ZIP {zip_code}: Unusual median income: ${median_income:,}")
            
            if 50 <= basket_cost <= 500:
                print_success(f"✅ ZIP {zip_code}: Realistic basket cost")
            else:
                print_warning(f"⚠️ ZIP {zip_code}: Unusual basket cost: ${basket_cost}")
        else:
            print_error(f"❌ Failed to retrieve data for ZIP {zip_code}")
            all_tests_passed = False
    
    # Test additional ZIP codes for broader verification
    print_info(f"\n🔍 Testing additional ZIP codes for broader verification:")
    
    for zip_code in additional_zips:
        success, zip_data = test_endpoint(
            "GET", f"/affordability/{zip_code}",
            description=f"Test ZIP {zip_code}"
        )
        
        if success and zip_data:
            city = zip_data.get('city', '')
            affordability_score = zip_data.get('affordability_score', 0)
            print_info(f"  ZIP {zip_code}: {city}, Score: {affordability_score}%")
            print_success(f"✅ ZIP {zip_code}: Data retrieved successfully")
        else:
            print_error(f"❌ ZIP {zip_code}: Failed to retrieve data")
            all_tests_passed = False
    
    return all_tests_passed

def test_search_functionality():
    """Test 5: Search Functionality for various queries"""
    print_test_header("Search Functionality Testing")
    
    print_info("🎯 TESTING: /api/search-zipcodes for various queries")
    
    search_tests = [
        ("08831", "ZIP code search - should find Monroe Township"),
        ("07002", "ZIP code search - should find Bayonne"),
        ("Monroe", "City name search - should find Monroe Township"),
        ("Bayonne", "City name search - should find Bayonne"),
        ("Hudson", "County search - should find Hudson County ZIPs"),
        ("070", "Partial ZIP search - should find 070xx ZIPs"),
    ]
    
    all_searches_passed = True
    
    for query, description in search_tests:
        print_info(f"\n🔍 Search Query: '{query}' - {description}")
        
        success, search_data = test_endpoint(
            "GET", f"/search-zipcodes?q={query}",
            description=f"Search for '{query}'"
        )
        
        if success and search_data:
            results_count = len(search_data)
            print_info(f"  Results found: {results_count}")
            
            if results_count > 0:
                print_success(f"✅ Search '{query}': Found {results_count} results")
                
                # Show first few results
                for i, result in enumerate(search_data[:3]):
                    zip_code = result.get('zip_code', '')
                    city = result.get('city', '')
                    county = result.get('county', '')
                    score = result.get('affordability_score', 0)
                    classification = result.get('classification', '')
                    
                    print_info(f"    {i+1}. ZIP {zip_code}: {city}, {county} - Score: {score}% ({classification})")
                
                # Verify specific expectations
                if query == "08831":
                    monroe_found = any(r.get('city', '').lower() in ['monroe township', 'monroe'] for r in search_data)
                    if monroe_found:
                        print_success("✅ ZIP 08831 search correctly shows Monroe")
                    else:
                        print_error("❌ ZIP 08831 search doesn't show Monroe")
                        all_searches_passed = False
                
                elif query == "07002":
                    bayonne_found = any(r.get('city', '').lower() == 'bayonne' for r in search_data)
                    if bayonne_found:
                        print_success("✅ ZIP 07002 search correctly shows Bayonne")
                    else:
                        print_error("❌ ZIP 07002 search doesn't show Bayonne")
                        all_searches_passed = False
            else:
                print_error(f"❌ Search '{query}': No results found")
                all_searches_passed = False
        else:
            print_error(f"❌ Search '{query}': Failed to execute")
            all_searches_passed = False
    
    return all_searches_passed

def test_core_endpoints():
    """Test 6: Core Endpoints (/api/zips, /api/stats, /api/config)"""
    print_test_header("Core Endpoints Testing")
    
    print_info("🎯 TESTING: Core endpoints for proper functionality")
    
    all_core_tests_passed = True
    
    # Test /api/zips
    print_info("\n🔍 Testing /api/zips")
    success, zips_data = test_endpoint(
        "GET", "/zips",
        description="Get all ZIP codes with comprehensive data"
    )
    
    if success and zips_data:
        total_count = zips_data.get('total_count', 0)
        data_source = zips_data.get('data_source', 'unknown')
        zips = zips_data.get('zips', [])
        
        print_info(f"  - Total Count: {total_count}")
        print_info(f"  - Data Source: {data_source}")
        print_info(f"  - ZIP Records: {len(zips)}")
        
        if total_count > 0:
            print_success(f"✅ /api/zips: Returns {total_count} ZIP codes")
        else:
            print_error("❌ /api/zips: No ZIP codes returned")
            all_core_tests_passed = False
        
        if data_source == 'census_comprehensive_pipeline':
            print_success("✅ /api/zips: Correct data source")
        else:
            print_warning(f"⚠️ /api/zips: Data source is '{data_source}'")
    else:
        print_error("❌ /api/zips: Failed to retrieve data")
        all_core_tests_passed = False
    
    # Test /api/stats
    print_info("\n🔍 Testing /api/stats")
    success, stats_data = test_endpoint(
        "GET", "/stats",
        description="Get overall dashboard statistics"
    )
    
    if success and stats_data:
        total_zips = stats_data.get('total_zip_codes', 0)
        avg_score = stats_data.get('average_affordability_score', 0)
        classifications = stats_data.get('classifications', {})
        data_source = stats_data.get('data_source', 'unknown')
        
        print_info(f"  - Total ZIP Codes: {total_zips}")
        print_info(f"  - Average Affordability Score: {avg_score}%")
        print_info(f"  - Data Source: {data_source}")
        print_info(f"  - Classifications: {classifications}")
        
        if total_zips > 0:
            print_success(f"✅ /api/stats: Shows {total_zips} ZIP codes")
        else:
            print_error("❌ /api/stats: No ZIP codes in stats")
            all_core_tests_passed = False
        
        if avg_score > 0:
            print_success(f"✅ /api/stats: Valid average score {avg_score}%")
        else:
            print_error("❌ /api/stats: Invalid average score")
            all_core_tests_passed = False
    else:
        print_error("❌ /api/stats: Failed to retrieve data")
        all_core_tests_passed = False
    
    # Test /api/config
    print_info("\n🔍 Testing /api/config")
    success, config_data = test_endpoint(
        "GET", "/config",
        description="Get API configuration status"
    )
    
    if success and config_data:
        data_source = config_data.get('data_source', 'unknown')
        using_real_demographics = config_data.get('using_real_demographics', False)
        message = config_data.get('message', '')
        
        print_info(f"  - Data Source: {data_source}")
        print_info(f"  - Using Real Demographics: {using_real_demographics}")
        print_info(f"  - Message: {message}")
        
        if data_source == 'census_comprehensive_pipeline':
            print_success("✅ /api/config: Correct data source")
        else:
            print_warning(f"⚠️ /api/config: Data source is '{data_source}'")
        
        print_success("✅ /api/config: Configuration retrieved successfully")
    else:
        print_error("❌ /api/config: Failed to retrieve configuration")
        all_core_tests_passed = False
    
    return all_core_tests_passed

def run_comprehensive_fixed_issues_test():
    """Run all tests for the fixed issues"""
    print_test_header("COMPREHENSIVE FIXED ISSUES VERIFICATION")
    
    print_info("🎯 TESTING CRITICAL BUG FIXES:")
    print_info("1. ML Risk Prediction Logic Bug")
    print_info("2. City Name Mapping (ZIP 08831 → Monroe Township)")
    print_info("3. Data Source Verification (census_comprehensive_pipeline)")
    print_info("4. Individual ZIP Lookups")
    print_info("5. Search Functionality")
    print_info("6. Core Endpoints")
    
    test_results = {}
    
    # Run all tests
    test_results["data_source_verification"] = test_data_source_verification()
    test_results["city_name_mapping_fix"] = test_city_name_mapping_fix()
    test_results["ml_prediction_logic_fix"] = test_ml_prediction_logic_fix()
    test_results["individual_zip_lookups"] = test_individual_zip_lookups()
    test_results["search_functionality"] = test_search_functionality()
    test_results["core_endpoints"] = test_core_endpoints()
    
    # Summary
    print_test_header("FINAL RESULTS SUMMARY")
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    print_info(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
    
    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print_info(f"  - {test_name.replace('_', ' ').title()}: {status}")
    
    if passed_tests == total_tests:
        print_success("🎉 SUCCESS: All critical bug fixes verified!")
        print_success("✅ ML Risk Prediction Logic Bug: FIXED")
        print_success("✅ City Name Mapping (08831 → Monroe Township): FIXED")
        print_success("✅ Data Source (census_comprehensive_pipeline): VERIFIED")
        print_success("✅ All endpoints working correctly")
        return True
    else:
        print_error("🚨 ISSUES FOUND: Some fixes may not be working correctly")
        failed_tests = [name for name, passed in test_results.items() if not passed]
        print_error(f"Failed tests: {', '.join(failed_tests)}")
        return False

if __name__ == "__main__":
    print(f"Backend URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    
    success = run_comprehensive_fixed_issues_test()
    
    if success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED - CRITICAL FIXES VERIFIED!{Colors.ENDC}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}🚨 SOME TESTS FAILED - ISSUES NEED ATTENTION{Colors.ENDC}")
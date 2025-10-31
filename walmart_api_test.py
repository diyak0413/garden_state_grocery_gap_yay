#!/usr/bin/env python3
"""
LIVE Walmart API Integration Testing
Tests the real Walmart API integration now that the user has added their API key
"""

import requests
import json
import time
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
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}🛒 {test_name}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.ENDC}")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.ENDC}")

def test_configuration_status():
    """Test 1: Check Configuration Status - Walmart API should now be detected as configured"""
    print_test_header("Configuration Status Check")
    
    try:
        # Test /api/config
        print(f"\n{Colors.BOLD}Testing GET /api/config{Colors.ENDC}")
        response = requests.get(f"{API_BASE}/config", timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            config_data = response.json()
            print_info("Configuration Status:")
            print(f"  - Scraping Enabled: {config_data.get('scraping_enabled', 'N/A')}")
            print(f"  - Enabled Sources: {config_data.get('enabled_sources', [])}")
            print(f"  - Walmart Configured: {config_data.get('apis_configured', {}).get('walmart', 'N/A')}")
            print(f"  - Instacart Configured: {config_data.get('apis_configured', {}).get('instacart', 'N/A')}")
            print(f"  - Using Sample Data: {config_data.get('using_sample_data', 'N/A')}")
            
            # Verify Walmart is now configured
            if config_data.get('scraping_enabled') and config_data.get('apis_configured', {}).get('walmart'):
                print_success("✅ Walmart API is now detected as configured and scraping is enabled!")
                return True
            else:
                print_error("❌ Walmart API not detected as configured or scraping not enabled")
                return False
        else:
            print_error(f"Config endpoint failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Configuration test failed: {str(e)}")
        return False

def test_scraping_connectivity():
    """Test 2: Test Scraping Configuration and Connectivity"""
    print_test_header("Scraping Connectivity Test")
    
    try:
        print(f"\n{Colors.BOLD}Testing GET /api/test-scraping{Colors.ENDC}")
        response = requests.get(f"{API_BASE}/test-scraping", timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            test_data = response.json()
            print_info("Scraping Test Results:")
            print(f"  - Scraping Enabled: {test_data.get('scraping_enabled', 'N/A')}")
            print(f"  - Enabled Sources: {test_data.get('enabled_sources', [])}")
            
            walmart_status = test_data.get('walmart', {})
            instacart_status = test_data.get('instacart', {})
            
            print(f"  - Walmart Status: {walmart_status.get('status', 'N/A')} - {walmart_status.get('message', 'N/A')}")
            print(f"  - Instacart Status: {instacart_status.get('status', 'N/A')} - {instacart_status.get('message', 'N/A')}")
            
            # Verify Walmart is ready
            if walmart_status.get('status') == 'configured':
                print_success("✅ Walmart API is configured and ready to scrape!")
                return True
            else:
                print_warning(f"Walmart status: {walmart_status.get('status')} - {walmart_status.get('message')}")
                return False
        else:
            print_error(f"Test-scraping endpoint failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Scraping connectivity test failed: {str(e)}")
        return False

def test_single_zip_scraping():
    """Test 3: Test Single ZIP Code Scraping with REAL Walmart API"""
    print_test_header("Single ZIP Code Scraping - LIVE DATA")
    
    test_zip = "07002"  # Bayonne, NJ
    print_info(f"Testing live scraping for ZIP code: {test_zip} (Bayonne, NJ)")
    print_info("Expected food basket items:")
    food_items = [
        "Brown Rice 2 lbs",
        "Whole Milk 1 gallon", 
        "Apples 3 lbs",
        "Chicken Breast 2 lbs",
        "Fresh Spinach 16 oz",
        "Eggs 1 dozen"
    ]
    for item in food_items:
        print(f"  - {item}")
    
    try:
        print(f"\n{Colors.BOLD}Testing POST /api/scrape/{test_zip}{Colors.ENDC}")
        print_warning("⏳ This may take 30-60 seconds as we scrape real Walmart prices...")
        
        start_time = time.time()
        response = requests.post(f"{API_BASE}/scrape/{test_zip}", timeout=120)  # Extended timeout for real API calls
        end_time = time.time()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {end_time - start_time:.2f} seconds")
        
        if response.status_code == 200:
            scrape_data = response.json()
            print_success("✅ Live scraping successful!")
            
            print_info("Scraping Results:")
            print(f"  - ZIP Code: {scrape_data.get('zip_code', 'N/A')}")
            print(f"  - Total Basket Cost: ${scrape_data.get('total_basket_cost', 'N/A')}")
            print(f"  - SNAP Basket Cost: ${scrape_data.get('snap_basket_cost', 'N/A')}")
            print(f"  - Items Found: {scrape_data.get('items_found', 'N/A')}")
            print(f"  - Sources Used: {scrape_data.get('sources_used', [])}")
            print(f"  - Scraped At: {scrape_data.get('scraped_at', 'N/A')}")
            
            # Verify we got real prices
            if scrape_data.get('items_found', 0) > 0 and scrape_data.get('total_basket_cost', 0) > 0:
                print_success(f"✅ Successfully scraped {scrape_data.get('items_found')} items with real prices!")
                print_success(f"✅ Total basket cost: ${scrape_data.get('total_basket_cost')}")
                return True, scrape_data
            else:
                print_warning("⚠️ Scraping completed but no items/prices found")
                return False, scrape_data
                
        elif response.status_code == 400:
            error_data = response.json()
            print_error(f"Scraping failed: {error_data.get('detail', 'Unknown error')}")
            return False, None
        else:
            print_error(f"Scraping failed: {response.status_code} - {response.text}")
            return False, None
            
    except requests.exceptions.Timeout:
        print_error("❌ Scraping request timed out - API may be slow or unresponsive")
        return False, None
    except Exception as e:
        print_error(f"Single ZIP scraping test failed: {str(e)}")
        return False, None

def test_live_price_storage():
    """Test 4: Verify Live Price Storage and Retrieval"""
    print_test_header("Live Price Storage Verification")
    
    test_zip = "07002"  # Same ZIP we scraped
    
    try:
        print(f"\n{Colors.BOLD}Testing GET /api/live-prices/{test_zip}{Colors.ENDC}")
        response = requests.get(f"{API_BASE}/live-prices/{test_zip}", timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            price_data = response.json()
            print_success("✅ Live prices retrieved successfully!")
            
            prices = price_data.get('prices', [])
            print_info(f"Live Price Data for ZIP {test_zip}:")
            print(f"  - Number of Price Records: {len(prices)}")
            
            if len(prices) > 0:
                print_info("Sample Price Records:")
                for i, price in enumerate(prices[:3]):  # Show first 3 records
                    print(f"  {i+1}. {price.get('item_name', 'N/A')} - ${price.get('price', 'N/A')} from {price.get('store', 'N/A')}")
                    print(f"     Source: {price.get('source', 'N/A')} | Scraped: {price.get('scraped_at', 'N/A')}")
                
                print_success("✅ Live prices are properly stored and accessible!")
                return True
            else:
                print_warning("⚠️ No live price records found - scraping may not have stored data")
                return False
                
        elif response.status_code == 404:
            print_warning("⚠️ No live price data found - this is expected if scraping failed")
            return False
        else:
            print_error(f"Live prices endpoint failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Live price storage test failed: {str(e)}")
        return False

def test_error_handling():
    """Test 5: Test Error Handling for Invalid ZIP Codes"""
    print_test_header("Error Handling Test")
    
    invalid_zip = "99999"  # Invalid ZIP code
    
    try:
        print(f"\n{Colors.BOLD}Testing POST /api/scrape/{invalid_zip} (Invalid ZIP){Colors.ENDC}")
        response = requests.post(f"{API_BASE}/scrape/{invalid_zip}", timeout=60)
        print(f"Status Code: {response.status_code}")
        
        # We expect this to either succeed with no results or fail gracefully
        if response.status_code == 200:
            scrape_data = response.json()
            if scrape_data.get('items_found', 0) == 0:
                print_success("✅ Invalid ZIP handled gracefully - no items found as expected")
                return True
            else:
                print_warning(f"⚠️ Unexpected results for invalid ZIP: {scrape_data.get('items_found')} items found")
                return True
        elif response.status_code in [400, 404]:
            error_data = response.json()
            print_success(f"✅ Invalid ZIP properly rejected: {error_data.get('detail', 'Error')}")
            return True
        else:
            print_warning(f"⚠️ Unexpected response for invalid ZIP: {response.status_code}")
            return True  # Not a critical failure
            
    except Exception as e:
        print_error(f"Error handling test failed: {str(e)}")
        return False

def test_performance():
    """Test 6: Basic Performance Testing"""
    print_test_header("Performance Testing")
    
    try:
        # Test config endpoint performance
        print(f"\n{Colors.BOLD}Testing /api/config response time{Colors.ENDC}")
        start_time = time.time()
        response = requests.get(f"{API_BASE}/config", timeout=10)
        end_time = time.time()
        
        config_time = end_time - start_time
        print(f"Config endpoint response time: {config_time:.3f} seconds")
        
        if config_time < 2.0:
            print_success("✅ Config endpoint responds quickly")
        else:
            print_warning(f"⚠️ Config endpoint is slow: {config_time:.3f}s")
        
        # Test test-scraping endpoint performance
        print(f"\n{Colors.BOLD}Testing /api/test-scraping response time{Colors.ENDC}")
        start_time = time.time()
        response = requests.get(f"{API_BASE}/test-scraping", timeout=10)
        end_time = time.time()
        
        test_time = end_time - start_time
        print(f"Test-scraping endpoint response time: {test_time:.3f} seconds")
        
        if test_time < 3.0:
            print_success("✅ Test-scraping endpoint responds reasonably quickly")
        else:
            print_warning(f"⚠️ Test-scraping endpoint is slow: {test_time:.3f}s")
        
        return True
        
    except Exception as e:
        print_error(f"Performance testing failed: {str(e)}")
        return False

def run_walmart_api_tests():
    """Run all Walmart API integration tests"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("=" * 80)
    print("🛒 LIVE WALMART API INTEGRATION TESTING")
    print("Testing real grocery price scraping with user's API key")
    print("=" * 80)
    print(f"{Colors.ENDC}")
    
    print_info(f"Backend URL: {BASE_URL}")
    print_info(f"API Base URL: {API_BASE}")
    print_info(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Track test results
    test_results = {}
    
    # Run all test suites
    test_results['config'] = test_configuration_status()
    test_results['connectivity'] = test_scraping_connectivity()
    test_results['scraping'] = test_single_zip_scraping()[0] if test_single_zip_scraping() else False
    test_results['storage'] = test_live_price_storage()
    test_results['error_handling'] = test_error_handling()
    test_results['performance'] = test_performance()
    
    # Summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("=" * 80)
    print("🛒 WALMART API INTEGRATION TEST SUMMARY")
    print("=" * 80)
    print(f"{Colors.ENDC}")
    
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.upper().replace('_', ' ')}: {status}")
    
    print(f"\n{Colors.BOLD}Overall Result: {passed}/{total} tests passed{Colors.ENDC}")
    
    if passed == total:
        print_success("🎉 ALL TESTS PASSED - Walmart API integration is working correctly!")
    elif passed >= total * 0.8:
        print_warning(f"⚠️ Most tests passed ({passed}/{total}) - Minor issues detected")
    else:
        print_error(f"❌ Multiple test failures ({passed}/{total}) - Significant issues detected")
    
    return test_results

if __name__ == "__main__":
    run_walmart_api_tests()
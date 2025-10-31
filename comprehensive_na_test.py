#!/usr/bin/env python3
"""
COMPREHENSIVE Na INVESTIGATION: Test all possible scenarios where "Na" might appear
Including edge cases and potential frontend/backend mismatches
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

def test_edge_case_zip_codes():
    """Test edge case ZIP codes that might have data issues"""
    print_test_header("EDGE CASE ZIP CODES - Testing for Na Values")
    
    # Test various ZIP codes including ones that might have issues
    test_zips = [
        "07002",  # Bayonne - user specifically mentioned
        "08701",  # Lakewood - highest population
        "07001",  # First in sample data
        "07104",  # Newark - at-risk area
        "07195",  # Might be problematic based on test history
        "07308",  # Might be problematic based on test history
        "07399",  # Might be problematic based on test history
        "07416",  # Might be problematic based on test history
        "08270",  # Might be problematic based on test history
        "08550"   # Might be problematic based on test history
    ]
    
    na_issues_found = []
    
    for zip_code in test_zips:
        print_info(f"\n🔍 Testing ZIP {zip_code}:")
        success, zip_data = test_endpoint(
            "GET", f"/affordability/{zip_code}",
            description=f"Check ZIP {zip_code} for any Na values or data issues"
        )
        
        if success and zip_data:
            # Check all fields for problematic values
            fields_to_check = [
                'zip_code', 'city', 'county', 'affordability_score', 
                'basket_cost', 'median_income', 'snap_rate', 'population',
                'cost_to_income_ratio', 'grocery_stores', 'snap_retailers', 'classification'
            ]
            
            zip_has_issues = False
            for field in fields_to_check:
                value = zip_data.get(field)
                
                # Check for various problematic values
                if value is None:
                    print_error(f"    🚨 {field}: NULL")
                    na_issues_found.append(f"ZIP {zip_code}: {field} is NULL")
                    zip_has_issues = True
                elif value == "":
                    print_error(f"    🚨 {field}: EMPTY STRING")
                    na_issues_found.append(f"ZIP {zip_code}: {field} is empty")
                    zip_has_issues = True
                elif isinstance(value, str) and value.lower() in ['na', 'n/a', 'null', 'none', 'undefined', 'nan']:
                    print_error(f"    🚨 {field}: '{value}' (problematic string)")
                    na_issues_found.append(f"ZIP {zip_code}: {field} = '{value}'")
                    zip_has_issues = True
                elif field == 'city' and isinstance(value, str) and value.lower() in ['unknown', 'n/a']:
                    print_error(f"    🚨 {field}: '{value}' (unknown city)")
                    na_issues_found.append(f"ZIP {zip_code}: {field} = '{value}'")
                    zip_has_issues = True
                elif isinstance(value, (int, float)) and value == 0 and field in ['median_income', 'population']:
                    print_warning(f"    ⚠️ {field}: {value} (suspicious zero)")
                else:
                    print_success(f"    ✅ {field}: {value}")
            
            # Check coordinates
            coordinates = zip_data.get('coordinates', {})
            if coordinates:
                lat = coordinates.get('lat')
                lng = coordinates.get('lng')
                
                if lat is None or lng is None:
                    print_error(f"    🚨 coordinates: lat={lat}, lng={lng} (NULL values)")
                    na_issues_found.append(f"ZIP {zip_code}: coordinates have NULL values")
                    zip_has_issues = True
                elif lat == 0 or lng == 0:
                    print_error(f"    🚨 coordinates: lat={lat}, lng={lng} (zero values)")
                    na_issues_found.append(f"ZIP {zip_code}: coordinates have zero values")
                    zip_has_issues = True
                else:
                    print_success(f"    ✅ coordinates: lat={lat}, lng={lng}")
            
            if not zip_has_issues:
                print_success(f"  ✅ ZIP {zip_code} has no data issues")
        else:
            print_error(f"  ❌ Failed to retrieve data for ZIP {zip_code}")
            na_issues_found.append(f"ZIP {zip_code}: API call failed")
    
    return na_issues_found

def test_ml_predictions_for_na():
    """Test ML predictions for Na values in city names or other fields"""
    print_test_header("ML PREDICTIONS - Check for Na Values in At-Risk ZIPs")
    
    success, ml_data = test_endpoint(
        "GET", "/ml/predict-risk",
        description="Check ML predictions for Na values, especially in at-risk ZIP codes"
    )
    
    na_issues_found = []
    
    if success and ml_data:
        predictions = ml_data.get('predictions', [])
        print_info(f"📊 Analyzing {len(predictions)} ML predictions...")
        
        # Focus on at-risk predictions
        at_risk_predictions = [p for p in predictions if p.get('risk_prediction') == 1 or p.get('risk_probability', 0) >= 0.15]
        print_info(f"🎯 Found {len(at_risk_predictions)} at-risk ZIP codes")
        
        for pred in at_risk_predictions:
            zip_code = pred.get('zip_code', 'N/A')
            city = pred.get('city', 'N/A')
            county = pred.get('county', 'N/A')
            risk_prob = pred.get('risk_probability', 0)
            
            print_info(f"  📍 ZIP {zip_code}: '{city}', {county} (risk: {risk_prob:.3f})")
            
            # Check for Na values
            if city is None or city == '' or str(city).lower() in ['na', 'n/a', 'null', 'none', 'undefined', 'unknown']:
                print_error(f"    🚨 CRITICAL: City shows as '{city}'")
                na_issues_found.append(f"ML Prediction ZIP {zip_code}: city = '{city}'")
            
            if county is None or county == '' or str(county).lower() in ['na', 'n/a', 'null', 'none', 'undefined', 'unknown']:
                print_error(f"    🚨 CRITICAL: County shows as '{county}'")
                na_issues_found.append(f"ML Prediction ZIP {zip_code}: county = '{county}'")
            
            if risk_prob is None or str(risk_prob).lower() in ['na', 'n/a', 'null', 'none', 'undefined', 'nan']:
                print_error(f"    🚨 CRITICAL: Risk probability shows as '{risk_prob}'")
                na_issues_found.append(f"ML Prediction ZIP {zip_code}: risk_probability = '{risk_prob}'")
        
        if not na_issues_found:
            print_success("✅ All ML predictions have valid data - no Na values found")
    else:
        print_error("❌ Failed to retrieve ML predictions")
        na_issues_found.append("ML predictions API call failed")
    
    return na_issues_found

def test_search_functionality_for_na():
    """Test search functionality for Na values"""
    print_test_header("SEARCH FUNCTIONALITY - Check for Na Values")
    
    # Test various search queries
    search_queries = ["07002", "Bayonne", "Newark", "Camden", "Trenton", "Elizabeth"]
    na_issues_found = []
    
    for query in search_queries:
        print_info(f"\n🔍 Testing search query: '{query}'")
        success, search_data = test_endpoint(
            "GET", f"/search-zipcodes?q={query}",
            description=f"Search for '{query}' and check for Na values in results"
        )
        
        if success and search_data:
            print_info(f"  📊 Found {len(search_data)} results")
            
            for result in search_data:
                zip_code = result.get('zip_code', 'N/A')
                city = result.get('city', 'N/A')
                county = result.get('county', 'N/A')
                affordability_score = result.get('affordability_score', 'N/A')
                classification = result.get('classification', 'N/A')
                
                print_info(f"    📍 ZIP {zip_code}: {city}, {county} (score: {affordability_score}, class: {classification})")
                
                # Check for Na values
                fields = {
                    'zip_code': zip_code,
                    'city': city,
                    'county': county,
                    'affordability_score': affordability_score,
                    'classification': classification
                }
                
                for field_name, field_value in fields.items():
                    if field_value is None or field_value == '' or str(field_value).lower() in ['na', 'n/a', 'null', 'none', 'undefined']:
                        print_error(f"      🚨 CRITICAL: {field_name} shows as '{field_value}'")
                        na_issues_found.append(f"Search result for '{query}' ZIP {zip_code}: {field_name} = '{field_value}'")
        else:
            print_error(f"  ❌ Failed to search for '{query}'")
            na_issues_found.append(f"Search for '{query}' failed")
    
    return na_issues_found

def test_price_trends_for_na():
    """Test price trends for Na values"""
    print_test_header("PRICE TRENDS - Check for Na Values")
    
    # Test price trends for a few ZIP codes
    test_zips = ["07002", "08701", "07104"]
    na_issues_found = []
    
    for zip_code in test_zips:
        print_info(f"\n🔍 Testing price trends for ZIP {zip_code}")
        success, trends_data = test_endpoint(
            "GET", f"/price-trends/{zip_code}",
            description=f"Check price trends for ZIP {zip_code} for Na values"
        )
        
        if success and trends_data:
            print_info(f"  📊 Found {len(trends_data)} items with price trends")
            
            for item_data in trends_data:
                item_name = item_data.get('item_name', 'N/A')
                prices = item_data.get('prices', [])
                
                print_info(f"    🛒 {item_name}: {len(prices)} price points")
                
                # Check item name for Na values
                if item_name is None or item_name == '' or str(item_name).lower() in ['na', 'n/a', 'null', 'none', 'undefined']:
                    print_error(f"      🚨 CRITICAL: Item name shows as '{item_name}'")
                    na_issues_found.append(f"Price trends ZIP {zip_code}: item_name = '{item_name}'")
                
                # Check a few price points for Na values
                for i, price_point in enumerate(prices[:3]):  # Check first 3 price points
                    price = price_point.get('price', 'N/A')
                    date = price_point.get('date', 'N/A')
                    
                    if price is None or str(price).lower() in ['na', 'n/a', 'null', 'none', 'undefined', 'nan']:
                        print_error(f"      🚨 CRITICAL: Price shows as '{price}' for {item_name}")
                        na_issues_found.append(f"Price trends ZIP {zip_code} {item_name}: price = '{price}'")
                    
                    if date is None or date == '' or str(date).lower() in ['na', 'n/a', 'null', 'none', 'undefined']:
                        print_error(f"      🚨 CRITICAL: Date shows as '{date}' for {item_name}")
                        na_issues_found.append(f"Price trends ZIP {zip_code} {item_name}: date = '{date}'")
        else:
            print_error(f"  ❌ Failed to get price trends for ZIP {zip_code}")
            na_issues_found.append(f"Price trends for ZIP {zip_code} failed")
    
    return na_issues_found

def test_food_basket_for_na():
    """Test food basket endpoint for Na values"""
    print_test_header("FOOD BASKET - Check for Na Values")
    
    success, basket_data = test_endpoint(
        "GET", "/food-basket",
        description="Check food basket items for Na values"
    )
    
    na_issues_found = []
    
    if success and basket_data:
        items = basket_data.get('items', [])
        about_score = basket_data.get('about_affordability_score', {})
        
        print_info(f"🛒 Checking {len(items)} food basket items...")
        
        for item in items:
            name = item.get('name', 'N/A')
            category = item.get('category', 'N/A')
            snap_eligible = item.get('snap_eligible', 'N/A')
            
            print_info(f"  📦 {name} ({category}) - SNAP: {snap_eligible}")
            
            # Check for Na values
            if name is None or name == '' or str(name).lower() in ['na', 'n/a', 'null', 'none', 'undefined']:
                print_error(f"    🚨 CRITICAL: Item name shows as '{name}'")
                na_issues_found.append(f"Food basket item: name = '{name}'")
            
            if category is None or category == '' or str(category).lower() in ['na', 'n/a', 'null', 'none', 'undefined']:
                print_error(f"    🚨 CRITICAL: Category shows as '{category}' for {name}")
                na_issues_found.append(f"Food basket item {name}: category = '{category}'")
            
            if snap_eligible is None or str(snap_eligible).lower() in ['na', 'n/a', 'null', 'none', 'undefined']:
                print_error(f"    🚨 CRITICAL: SNAP eligible shows as '{snap_eligible}' for {name}")
                na_issues_found.append(f"Food basket item {name}: snap_eligible = '{snap_eligible}'")
        
        # Check about_affordability_score for Na values
        print_info("📖 Checking affordability score explanation...")
        
        explanation_fields = {
            'title': about_score.get('title', 'N/A'),
            'description': about_score.get('description', 'N/A'),
            'ml_model': about_score.get('ml_model', 'N/A'),
            'note': about_score.get('note', 'N/A')
        }
        
        for field_name, field_value in explanation_fields.items():
            if field_value is None or field_value == '' or str(field_value).lower() in ['na', 'n/a', 'null', 'none', 'undefined']:
                print_error(f"  🚨 CRITICAL: Explanation {field_name} shows as '{field_value}'")
                na_issues_found.append(f"Food basket explanation: {field_name} = '{field_value}'")
            else:
                print_success(f"  ✅ {field_name}: {field_value[:50]}...")
    else:
        print_error("❌ Failed to get food basket data")
        na_issues_found.append("Food basket API call failed")
    
    return na_issues_found

def run_comprehensive_investigation():
    """Run comprehensive Na investigation"""
    print(f"{Colors.BOLD}{Colors.RED}")
    print("=" * 80)
    print("🔍 COMPREHENSIVE Na INVESTIGATION")
    print("Testing all possible scenarios where 'Na' might appear")
    print("=" * 80)
    print(f"{Colors.ENDC}")
    
    print_info(f"Backend URL: {BASE_URL}")
    print_info(f"API Base URL: {API_BASE}")
    print_info(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_na_issues = []
    
    # Run all tests
    print_info("🎯 Running comprehensive Na value tests...")
    
    # Test 1: Edge case ZIP codes
    edge_case_issues = test_edge_case_zip_codes()
    all_na_issues.extend(edge_case_issues)
    
    # Test 2: ML predictions
    ml_issues = test_ml_predictions_for_na()
    all_na_issues.extend(ml_issues)
    
    # Test 3: Search functionality
    search_issues = test_search_functionality_for_na()
    all_na_issues.extend(search_issues)
    
    # Test 4: Price trends
    price_issues = test_price_trends_for_na()
    all_na_issues.extend(price_issues)
    
    # Test 5: Food basket
    basket_issues = test_food_basket_for_na()
    all_na_issues.extend(basket_issues)
    
    # Final summary
    print(f"\n{Colors.BOLD}{Colors.RED if all_na_issues else Colors.GREEN}")
    print("=" * 80)
    print("🔍 COMPREHENSIVE Na INVESTIGATION RESULTS")
    
    if all_na_issues:
        print(f"❌ FOUND {len(all_na_issues)} Na VALUE ISSUES:")
        for i, issue in enumerate(all_na_issues, 1):
            print(f"  {i}. {issue}")
        
        print("\n🔧 ROOT CAUSE ANALYSIS:")
        print("  - Check database data integrity")
        print("  - Verify mock data generator completeness")
        print("  - Check API response serialization")
        print("  - Verify frontend null handling")
        print("  - Check data loading and startup process")
    else:
        print("✅ NO Na VALUE ISSUES FOUND")
        print("All tested endpoints and scenarios return proper data")
        print("The user's reported 'Na' issues may be:")
        print("  1. Already resolved by recent fixes")
        print("  2. Frontend display issues (not backend data issues)")
        print("  3. Caching issues in user's browser")
        print("  4. Specific edge cases not covered in testing")
    
    print("=" * 80)
    print(f"{Colors.ENDC}")
    
    return len(all_na_issues) == 0

if __name__ == "__main__":
    run_comprehensive_investigation()
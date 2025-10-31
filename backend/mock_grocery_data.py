"""
Mock Grocery Pricing Data for New Jersey ZIP codes
Realistic but fake pricing data for all valid NJ ZIP codes
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List
from nj_zipcode_mapping import get_all_valid_nj_zipcodes, get_city_for_zipcode, get_county_for_zipcode

# Food basket items with realistic base prices
FOOD_BASKET_ITEMS = {
    "Whole Milk (1 gallon)": {"base_price": 3.49, "snap_eligible": True, "category": "dairy"},
    "Large Eggs (1 dozen)": {"base_price": 2.89, "snap_eligible": True, "category": "protein"},
    "Bananas (1 lb)": {"base_price": 0.68, "snap_eligible": True, "category": "produce"},
    "Ground Beef (1 lb)": {"base_price": 5.99, "snap_eligible": True, "category": "protein"},
    "White Bread (1 loaf)": {"base_price": 1.29, "snap_eligible": True, "category": "grains"},
    "Chicken Breast (1 lb)": {"base_price": 4.49, "snap_eligible": True, "category": "protein"},
    "Fresh Apples (1 lb)": {"base_price": 1.89, "snap_eligible": True, "category": "produce"},
    "White Rice (2 lbs)": {"base_price": 2.49, "snap_eligible": True, "category": "grains"},
    "Canned Tomatoes (14.5 oz)": {"base_price": 1.09, "snap_eligible": True, "category": "canned"},
    "Pasta (1 lb box)": {"base_price": 1.19, "snap_eligible": True, "category": "grains"}
}

def generate_price_variation(base_price: float, zip_code: str, county: str) -> float:
    """Generate realistic price variations based on location"""
    
    # County-based price multipliers (affluent areas = higher prices)
    county_multipliers = {
        'Bergen': 1.15,
        'Morris': 1.12,
        'Somerset': 1.10,
        'Hunterdon': 1.08,
        'Monmouth': 1.05,
        'Middlesex': 1.02,
        'Union': 1.00,
        'Essex': 0.98,
        'Hudson': 0.95,
        'Passaic': 0.93,
        'Ocean': 0.92,
        'Burlington': 0.90,
        'Mercer': 0.95,
        'Gloucester': 0.88,
        'Camden': 0.85,
        'Atlantic': 0.87,
        'Cape May': 0.92,
        'Cumberland': 0.82,
        'Salem': 0.80,
        'Sussex': 0.90,
        'Warren': 0.88
    }
    
    # Get county multiplier
    multiplier = county_multipliers.get(county, 1.0)
    
    # Add random variation (±10%)
    random_factor = random.uniform(0.90, 1.10)
    
    # Calculate final price
    final_price = base_price * multiplier * random_factor
    
    return round(final_price, 2)

def generate_price_history(current_price: float, weeks: int = 52) -> List[Dict]:
    """Generate weekly price history"""
    history = []
    price = current_price
    
    start_date = datetime.now() - timedelta(weeks=weeks)
    
    for week in range(weeks):
        # Add seasonal and random variation
        seasonal_factor = 1 + 0.05 * random.sin((week / 52) * 2 * 3.14159)
        weekly_change = random.uniform(0.95, 1.05)
        
        price = price * seasonal_factor * weekly_change
        price = max(0.50, price)  # Minimum price floor
        
        history.append({
            "week": week + 1,
            "date": (start_date + timedelta(weeks=week)).isoformat()[:10],
            "price": round(price, 2)
        })
    
    return history

def generate_store_data(zip_code: str, county: str, population: int) -> Dict:
    """Generate store accessibility data"""
    
    # Base store counts on population density
    population_factor = min(population / 10000, 5.0)  # Cap at 5x
    
    # Urban areas have more stores
    urban_counties = ['Hudson', 'Essex', 'Bergen', 'Union', 'Camden']
    urban_multiplier = 1.5 if county in urban_counties else 1.0
    
    grocery_stores = max(1, int(random.uniform(1, 4) * population_factor * urban_multiplier))
    snap_retailers = max(1, int(random.uniform(1, 3) * population_factor * urban_multiplier))
    
    return {
        "grocery_stores": grocery_stores,
        "snap_retailers": snap_retailers
    }

def create_mock_grocery_database() -> Dict:
    """Create comprehensive mock grocery database for all NJ ZIP codes"""
    
    print("🛒 Creating mock grocery database for all NJ ZIP codes...")
    
    all_zipcodes = get_all_valid_nj_zipcodes()
    grocery_database = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "total_zipcodes": len(all_zipcodes),
            "data_source": "Mock/Simulated Data",
            "food_basket_items": len(FOOD_BASKET_ITEMS)
        },
        "zipcodes": {}
    }
    
    for i, zip_code in enumerate(all_zipcodes):
        if i % 100 == 0:
            print(f"📍 Processing ZIP codes: {i+1}/{len(all_zipcodes)}")
        
        city = get_city_for_zipcode(zip_code)
        county = get_county_for_zipcode(zip_code)
        
        # Generate realistic population based on area type
        if county in ['Hudson', 'Essex', 'Camden'] and 'City' in city:
            population = random.randint(15000, 75000)  # Urban
        elif county in ['Bergen', 'Morris', 'Somerset']:
            population = random.randint(8000, 40000)   # Suburban
        else:
            population = random.randint(2000, 25000)   # Rural/Small town
        
        # Generate median income based on county patterns
        county_income_ranges = {
            'Bergen': (70000, 140000),
            'Morris': (75000, 130000),
            'Somerset': (70000, 125000),
            'Hunterdon': (80000, 120000),
            'Monmouth': (65000, 110000),
            'Middlesex': (55000, 95000),
            'Union': (50000, 85000),
            'Essex': (35000, 95000),
            'Hudson': (40000, 85000),
            'Passaic': (35000, 75000),
            'Ocean': (45000, 75000),
            'Burlington': (50000, 85000),
            'Mercer': (55000, 105000),
            'Gloucester': (50000, 80000),
            'Camden': (30000, 65000),
            'Atlantic': (35000, 70000),
            'Cape May': (40000, 75000),
            'Cumberland': (30000, 60000),
            'Salem': (35000, 65000),
            'Sussex': (50000, 90000),
            'Warren': (45000, 80000)
        }
        
        income_range = county_income_ranges.get(county, (45000, 75000))
        median_income = random.randint(income_range[0], income_range[1])
        
        # Calculate SNAP rate based on income
        if median_income < 40000:
            snap_rate = random.uniform(0.15, 0.30)
        elif median_income < 60000:
            snap_rate = random.uniform(0.08, 0.18)
        elif median_income < 80000:
            snap_rate = random.uniform(0.04, 0.12)
        else:
            snap_rate = random.uniform(0.02, 0.08)
        
        # Generate store data
        store_data = generate_store_data(zip_code, county, population)
        
        # Generate pricing for each food item
        item_prices = {}
        total_basket_cost = 0
        
        for item_name, item_data in FOOD_BASKET_ITEMS.items():
            current_price = generate_price_variation(
                item_data["base_price"], zip_code, county
            )
            
            item_prices[item_name] = {
                "current_price": current_price,
                "snap_eligible": item_data["snap_eligible"],
                "category": item_data["category"],
                "price_history": generate_price_history(current_price)
            }
            
            total_basket_cost += current_price
        
        # Store ZIP code data
        grocery_database["zipcodes"][zip_code] = {
            "zip_code": zip_code,
            "city": city,
            "county": county,
            "coordinates": {
                "lat": round(40.0 + random.uniform(-0.5, 1.5), 4),  # NJ latitude range
                "lng": round(-74.5 + random.uniform(-0.8, 0.8), 4)  # NJ longitude range
            },
            "demographics": {
                "population": population,
                "median_income": median_income,
                "snap_rate": round(snap_rate, 3)
            },
            "store_access": store_data,
            "grocery_prices": item_prices,
            "basket_total": round(total_basket_cost, 2),
            "snap_basket_total": round(total_basket_cost, 2),  # All items are SNAP eligible
            "last_updated": datetime.now().isoformat()[:10]
        }
    
    print(f"✅ Mock grocery database created: {len(all_zipcodes)} ZIP codes with realistic pricing")
    
    return grocery_database

# Create and save the database
if __name__ == "__main__":
    database = create_mock_grocery_database()
    
    # Save to JSON file
    with open('/app/backend/mock_grocery_data.json', 'w') as f:
        json.dump(database, f, indent=2)
    
    print("💾 Mock grocery database saved to mock_grocery_data.json")

# For importing
def get_mock_grocery_database() -> Dict:
    """Get the mock grocery database"""
    try:
        with open('/app/backend/mock_grocery_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return create_mock_grocery_database()

print("🛒 Mock Grocery Data Module Ready")
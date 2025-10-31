"""
Mock Data Generator for Garden State Grocery Gap
Generates realistic grocery pricing data to replace live API calls
"""

import json
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List

class MockGroceryDataGenerator:
    """Generates mock grocery pricing data for testing"""
    
    def __init__(self):
        # Base prices for healthy food basket items (in USD) - increased significantly for realistic affordability challenges
        self.base_prices = {
            "Brown Rice (2 lbs)": {"base": 18.49, "variance": 3.0},     # Target $70-120 basket cost
            "Whole Milk (1 gallon)": {"base": 12.89, "variance": 2.5},  
            "Apples (3 lbs)": {"base": 16.99, "variance": 3.5},         
            "Chicken Breast (2 lbs)": {"base": 32.99, "variance": 6.0}, 
            "Fresh Spinach (16 oz)": {"base": 11.99, "variance": 2.5},   
            "Eggs (1 dozen)": {"base": 9.89, "variance": 2.0}           # Total base: ~$103
        }
        
        # Store types and their price multipliers
        self.store_types = {
            "Walmart": 0.92,      # Generally cheaper
            "ShopRite": 1.05,     # Slightly more expensive
            "Stop & Shop": 1.08,  # Mid-range
            "Whole Foods": 1.35,  # Premium pricing
            "ACME": 1.02,         # Standard pricing
            "Kings": 1.28,        # Higher-end
            "Local Market": 1.15  # Small markup
        }
    
    def generate_mock_prices_for_zip(self, zip_code: str, median_income: int, county: str) -> Dict:
        """Generate mock grocery prices for a specific ZIP code"""
        
        # Adjust prices based on local economics
        income_factor = median_income / 70000  # Normalize around $70k
        area_multiplier = 1.0 + (income_factor * 0.3)  # Range: 1.0 - 1.3 (was 0.88-1.12)
        
        # County-based adjustments (higher cost areas)
        county_adjustments = {
            'Bergen': 1.15, 'Morris': 1.12, 'Somerset': 1.10,
            'Monmouth': 1.08, 'Middlesex': 1.05, 'Union': 1.03,
            'Hudson': 1.06, 'Essex': 0.98, 'Passaic': 0.95,
            'Ocean': 0.92, 'Burlington': 0.90, 'Camden': 0.88,
            'Gloucester': 0.89, 'Atlantic': 0.87, 'Cumberland': 0.85,
            'Cape May': 0.91, 'Salem': 0.86, 'Sussex': 0.94,
            'Warren': 0.93, 'Mercer': 1.07
        }
        
        county_factor = county_adjustments.get(county, 1.0)
        final_multiplier = area_multiplier * county_factor
        
        # Generate prices from multiple "stores"
        stores = random.sample(list(self.store_types.keys()), k=random.randint(2, 4))
        store_prices = {}
        
        for store in stores:
            store_multiplier = self.store_types[store] * final_multiplier
            store_prices[store] = {}
            
            for item_name, price_info in self.base_prices.items():
                base_price = price_info["base"] * store_multiplier
                variance = price_info["variance"]
                
                # Add random variance
                price_variation = random.uniform(-variance, variance)
                final_price = max(0.99, base_price + price_variation)
                
                store_prices[store][item_name] = round(final_price, 2)
        
        # Calculate lowest available price for each item (best deal across stores)
        best_prices = {}
        total_basket_cost = 0
        
        for item_name in self.base_prices.keys():
            min_price = min(store_prices[store][item_name] for store in stores)
            best_prices[item_name] = min_price
            total_basket_cost += min_price
        
        return {
            "zip_code": zip_code,
            "total_basket_cost": round(total_basket_cost, 2),
            "individual_prices": best_prices,
            "store_prices": store_prices,
            "stores_available": stores,
            "price_date": datetime.utcnow().isoformat(),
            "data_source": "mock_generator"
        }
    
    def generate_price_history(self, current_price: float, weeks_back: int = 52) -> List[Dict]:
        """Generate realistic price history for an item"""
        prices = []
        base_date = datetime.utcnow() - timedelta(weeks=weeks_back)
        
        price = current_price * random.uniform(0.92, 0.98)  # Start slightly lower
        
        for week in range(weeks_back):
            # Add seasonal variation (food prices tend to fluctuate seasonally)
            seasonal_factor = 1 + 0.08 * math.sin((week / 52) * 2 * math.pi + random.uniform(0, math.pi))
            
            # Add weekly random variation
            weekly_variation = random.uniform(0.96, 1.04)
            
            # Add gradual inflation trend
            inflation_factor = 1 + (week * 0.0008)  # ~4% annual inflation
            
            # Calculate final price
            week_price = price * seasonal_factor * weekly_variation * inflation_factor
            
            prices.append({
                "date": (base_date + timedelta(weeks=week)).isoformat(),
                "price": round(week_price, 2),
                "week": week + 1
            })
            
            # Small random walk for next week's base price
            price *= random.uniform(0.998, 1.002)
        
        return prices
    
    def save_mock_data_to_file(self, zip_codes_data: List[Dict], filename: str = "mock_grocery_data.json"):
        """Save generated mock data to a JSON file"""
        mock_data = []
        
        for zip_data in zip_codes_data:
            zip_code = zip_data.get('zip', zip_data.get('zip_code'))
            median_income = zip_data.get('median_income', 65000)
            county = zip_data.get('county', 'Middlesex')
            
            zip_mock_data = self.generate_mock_prices_for_zip(zip_code, median_income, county)
            
            # Add price history for each item
            zip_mock_data["price_history"] = {}
            for item_name, current_price in zip_mock_data["individual_prices"].items():
                zip_mock_data["price_history"][item_name] = self.generate_price_history(current_price)
            
            mock_data.append(zip_mock_data)
        
        # Save to file
        filepath = f"/app/backend/{filename}"
        with open(filepath, 'w') as f:
            json.dump(mock_data, f, indent=2)
        
        print(f"✅ Mock grocery data saved to {filepath}")
        print(f"📊 Generated data for {len(mock_data)} ZIP codes")
        
        return filepath
    
    def load_mock_data_from_file(self, filename: str = "mock_grocery_data.json") -> List[Dict]:
        """Load mock data from JSON file"""
        try:
            filepath = f"/app/backend/{filename}"
            with open(filepath, 'r') as f:
                data = json.load(f)
            print(f"✅ Mock grocery data loaded from {filepath}")
            return data
        except FileNotFoundError:
            print(f"❌ Mock data file not found: {filepath}")
            return []
        except Exception as e:
            print(f"❌ Error loading mock data: {str(e)}")
            return []

# Utility functions for integration with the main application
def generate_mock_data_for_all_nj_zips():
    """Generate mock data for all valid NJ ZIP codes"""
    from valid_nj_zipcodes import get_valid_nj_zipcodes
    
    generator = MockGroceryDataGenerator()
    nj_data = get_valid_nj_zipcodes()
    
    print(f"🏗️ Generating mock grocery data for {len(nj_data)} NJ ZIP codes...")
    filepath = generator.save_mock_data_to_file(nj_data)
    
    return filepath

def get_mock_price_for_zip(zip_code: str, nj_data: List[Dict] = None) -> Dict:
    """Get mock pricing data for a specific ZIP code"""
    if nj_data is None:
        from valid_nj_zipcodes import get_valid_nj_zipcodes
        nj_data = get_valid_nj_zipcodes()
    
    # Find ZIP code data
    zip_data = next((z for z in nj_data if z.get('zip', z.get('zip_code')) == zip_code), None)
    
    if not zip_data:
        return None
    
    generator = MockGroceryDataGenerator()
    return generator.generate_mock_prices_for_zip(
        zip_code, 
        zip_data.get('median_income', 65000),
        zip_data.get('county', 'Middlesex')
    )

if __name__ == "__main__":
    # Generate mock data when run directly
    generate_mock_data_for_all_nj_zips()
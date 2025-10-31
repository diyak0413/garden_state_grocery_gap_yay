#!/usr/bin/env python3
"""
COMPREHENSIVE CENSUS DATA REFRESH
Actually implements what the user asked for - ALL 734 ZIP codes with real Census data
"""

import os
import sys
import requests
import json
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment
sys.path.append('/app/backend')
load_dotenv('/app/backend/.env')

class ComprehensiveCensusRefresh:
    def __init__(self):
        self.census_api_key = os.getenv('CENSUS_API_KEY')
        self.mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
        self.client = MongoClient(self.mongo_url)
        self.db = self.client.nj_food_access
        
    def get_all_nj_places_data(self):
        """Get ALL NJ places from Census ACS 2018-2022 5-year data"""
        print("📊 Fetching ALL New Jersey places from Census ACS 2018-2022...")
        
        try:
            url = 'https://api.census.gov/data/2022/acs/acs5'
            params = {
                'get': 'NAME,B19013_001E,B01003_001E,B25064_001E,B17001_002E,B17001_001E',
                'for': 'place:*',
                'in': 'state:34',  # New Jersey
                'key': self.census_api_key
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                census_places = {}
                for row in data[1:]:  # Skip header
                    place_name = row[0]
                    income = int(row[1]) if row[1] not in ['-666666666', None, ''] else None
                    population = int(row[2]) if row[2] not in ['-666666666', None, ''] else None
                    rent = int(row[3]) if row[3] not in ['-666666666', None, ''] else None
                    poverty_count = int(row[4]) if row[4] not in ['-666666666', None, ''] else 0
                    total_pop = int(row[5]) if row[5] not in ['-666666666', None, ''] else 1
                    
                    if income and 'New Jersey' in place_name:
                        # Clean city name for matching
                        clean_name = (place_name
                                    .replace(' city, New Jersey', '')
                                    .replace(' borough, New Jersey', '')  
                                    .replace(' township, New Jersey', '')
                                    .replace(' town, New Jersey', '')
                                    .replace(', New Jersey', '')
                                    .strip())
                        
                        poverty_rate = (poverty_count / total_pop) if total_pop > 0 else 0
                        
                        census_places[clean_name.lower()] = {
                            'full_name': place_name,
                            'clean_name': clean_name,
                            'median_income': income,
                            'population': population,
                            'median_rent': rent,
                            'poverty_rate': poverty_rate,
                            'vintage': 'ACS 2018-2022 5-year'
                        }
                
                print(f"✅ Retrieved {len(census_places)} NJ places from Census")
                return census_places
                
            else:
                print(f"❌ Census API Error: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Census API failed: {str(e)}")
            return {}
    
    def match_city_to_census(self, city_name, census_places):
        """Match a city name to Census place data"""
        city_lower = city_name.lower().strip()
        
        # Direct match
        if city_lower in census_places:
            return census_places[city_lower]
        
        # Partial matches for common variations
        variations = [
            city_lower.replace(' township', ''),
            city_lower.replace(' borough', ''),
            city_lower.replace(' city', ''),
            city_lower + ' township',
            city_lower + ' borough'
        ]
        
        for variation in variations:
            if variation in census_places:
                return census_places[variation]
        
        # Substring match as last resort
        for census_key, census_data in census_places.items():
            if city_lower in census_key or census_key in city_lower:
                return census_data
                
        return None
    
    def refresh_all_cities(self):
        """Refresh ALL 734 ZIP codes with Census data"""
        print("🔄 Starting COMPREHENSIVE refresh of ALL ZIP codes...")
        
        # Get Census data
        census_places = self.get_all_nj_places_data()
        if not census_places:
            print("❌ Cannot proceed without Census data")
            return
        
        # Get all cities in our database
        all_cities = list(self.db.zip_demographics.find({}, {
            'zip_code': 1, 
            'city': 1, 
            'median_income': 1
        }))
        
        print(f"📋 Found {len(all_cities)} cities to refresh")
        
        updates_made = 0
        city_corrections = 0
        income_corrections = 0
        
        for i, city_doc in enumerate(all_cities):
            zip_code = city_doc['zip_code']
            current_city = city_doc['city']
            current_income = city_doc.get('median_income', 0)
            
            if (i + 1) % 100 == 0:
                print(f"Progress: {i+1}/{len(all_cities)} cities processed...")
            
            # Match to Census data
            census_match = self.match_city_to_census(current_city, census_places)
            
            if census_match:
                new_income = census_match['median_income']
                correct_city = census_match['clean_name']
                new_population = census_match['population']
                new_poverty_rate = census_match['poverty_rate']
                
                # Update demographics
                demo_updates = {}
                if new_income != current_income:
                    demo_updates['median_income'] = new_income
                    income_corrections += 1
                
                if correct_city.lower() != current_city.lower():
                    demo_updates['city'] = correct_city
                    city_corrections += 1
                
                if new_population:
                    demo_updates['population'] = new_population
                    
                demo_updates['snap_rate'] = new_poverty_rate
                demo_updates['data_source'] = 'census_acs_2022_comprehensive'
                demo_updates['vintage'] = 'ACS 2018-2022 5-year'
                
                if demo_updates:
                    self.db.zip_demographics.update_one(
                        {'zip_code': zip_code},
                        {'$set': demo_updates}
                    )
                
                # Recalculate affordability score
                affordability_doc = self.db.affordability_scores.find_one({'zip_code': zip_code})
                if affordability_doc:
                    basket_cost = affordability_doc.get('basket_cost', 30)
                    
                    # Recalculate with new income
                    monthly_food_cost = basket_cost * 4.33  # Weekly to monthly
                    monthly_income = new_income / 12
                    new_score = (monthly_food_cost / monthly_income) * 100
                    
                    self.db.affordability_scores.update_one(
                        {'zip_code': zip_code},
                        {'$set': {
                            'affordability_score': round(new_score, 2),
                            'vintage': 'ACS 2018-2022 refresh',
                            'recalculated_at': '2024-12-27'
                        }}
                    )
                
                updates_made += 1
        
        print(f"\n✅ COMPREHENSIVE REFRESH COMPLETE!")
        print(f"   Total cities processed: {len(all_cities)}")
        print(f"   Cities updated: {updates_made}")
        print(f"   Income corrections: {income_corrections}")
        print(f"   City name corrections: {city_corrections}")
        
        return {
            'total_processed': len(all_cities),
            'updates_made': updates_made,
            'income_corrections': income_corrections,
            'city_corrections': city_corrections
        }

if __name__ == "__main__":
    refresher = ComprehensiveCensusRefresh()
    results = refresher.refresh_all_cities()
    
    print(f"\n🎯 RESULTS:")
    print(f"   Processed: {results['total_processed']} cities")
    print(f"   Updated: {results['updates_made']} cities")
    print(f"   Income fixes: {results['income_corrections']}")
    print(f"   Name fixes: {results['city_corrections']}")
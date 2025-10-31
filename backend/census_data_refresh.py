"""
Comprehensive Census Data Refresh System
Updates all data to latest ACS 2023/2019-2023 standards
"""

import os
import requests
import json
import time
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

class CensusDataRefresh:
    def __init__(self):
        self.census_api_key = os.getenv('CENSUS_API_KEY')
        self.session = requests.Session()
        self.refresh_log = []
        
    def get_census_place_geoid(self, city_name: str, state_fips: str = '34') -> Optional[Tuple[str, str, str]]:
        """Get Census place GEOID and data for a city in NJ"""
        try:
            # Use ACS 5-year for place lookup (more reliable)
            url = 'https://api.census.gov/data/2023/acs/acs5'
            params = {
                'get': 'NAME,B19013_001E,B01003_001E',  # Name, income, population
                'for': 'place:*',
                'in': f'state:{state_fips}',
                'key': self.census_api_key
            }
            
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                # Find best matching place
                best_match = None
                city_lower = city_name.lower().strip()
                
                for row in data[1:]:  # Skip header
                    place_name = row[0]
                    income = row[1]
                    population = row[2]
                    state_code = row[3] 
                    place_code = row[4]
                    
                    if 'new jersey' in place_name.lower():
                        place_name_clean = place_name.lower().replace(' city, new jersey', '').replace(' borough, new jersey', '').replace(', new jersey', '').strip()
                        
                        # Exact match preferred
                        if city_lower == place_name_clean:
                            geoid = f"{state_code}{place_code}"
                            return (geoid, place_name, income)
                            
                        # Partial match as backup
                        if city_lower in place_name_clean or place_name_clean in city_lower:
                            if not best_match:
                                geoid = f"{state_code}{place_code}"
                                best_match = (geoid, place_name, income)
                
                return best_match
                        
            return None
            
        except Exception as e:
            print(f"GEOID lookup failed for {city_name}: {str(e)}")
            return None
    
    def get_acs_data(self, geoid: str, use_5_year: bool = False) -> Optional[Dict]:
        """Get ACS data for a place using 1-year or 5-year estimates"""
        try:
            # Choose dataset
            if use_5_year:
                dataset = "2022/acs/acs5"  # Most recent 5-year
                vintage = "ACS 2018-2022 5-year"
            else:
                dataset = "2023/acs/acs1"  # Most recent 1-year
                vintage = "ACS 2023 1-year"
            
            url = f"https://api.census.gov/data/{dataset}"
            
            # Get key demographic variables
            variables = [
                'DP03_0062E',  # Median household income
                'B25064_001E', # Median gross rent
                'DP04_0089E',  # Median home value
                'B01003_001E', # Total population
                'B17001_002E', # Poverty count
                'B17001_001E'  # Total for poverty rate
            ]
            
            params = {
                'get': ','.join(variables),
                'for': f'place:{geoid[2:]}',  # Place code (remove state prefix)
                'in': f'state:{geoid[:2]}',   # State code
                'key': self.census_api_key
            }
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if len(data) > 1:
                    row = data[1]  # Data row
                    
                    # Parse safely
                    median_income = int(row[0]) if row[0] not in [None, '-666666666', ''] else None
                    median_rent = int(row[1]) if row[1] not in [None, '-666666666', ''] else None
                    median_home_value = int(row[2]) if row[2] not in [None, '-666666666', ''] else None
                    population = int(row[3]) if row[3] not in [None, '-666666666', ''] else None
                    poverty_count = int(row[4]) if row[4] not in [None, '-666666666', ''] else 0
                    total_pop = int(row[5]) if row[5] not in [None, '-666666666', ''] else 1
                    
                    # Calculate poverty rate
                    poverty_rate = (poverty_count / total_pop) if total_pop > 0 else 0
                    
                    return {
                        'median_income': median_income,
                        'median_rent': median_rent,
                        'median_home_value': median_home_value,
                        'population': population,
                        'poverty_rate': poverty_rate,
                        'vintage': vintage,
                        'geoid': geoid,
                        'data_source': 'census_acs_refresh'
                    }
                    
            return None
            
        except Exception as e:
            print(f"ACS data fetch failed for GEOID {geoid}: {str(e)}")
            return None
    
    def calculate_refreshed_affordability_score(self, median_income: int, basket_cost: float) -> float:
        """Calculate affordability score using existing project formula"""
        if median_income <= 0:
            return 0.0
            
        # Use existing formula: basket_cost / median_income * 100
        monthly_food_cost = basket_cost * 4.33  # Weekly to monthly
        affordability_score = (monthly_food_cost / (median_income / 12)) * 100
        
        return round(affordability_score, 2)
    
    def refresh_city_data(self, city_name: str, zip_code: str, current_data: Dict) -> Dict:
        """Refresh data for a single city"""
        result = {
            'name': city_name,
            'zip_code': zip_code,
            'geoid': None,
            'vintage_used': None,
            'income_old': current_data.get('median_income', 0),
            'income_new': None,
            'rent_old': current_data.get('median_rent', 0), 
            'rent_new': None,
            'score_old': current_data.get('affordability_score', 0),
            'score_new': None,
            'status': 'pending'
        }
        
        try:
            # Step 1: Get Census place GEOID and basic data
            place_result = self.get_census_place_geoid(city_name)
            
            if not place_result:
                result['status'] = 'unresolved'
                return result
                
            geoid, full_place_name, census_income = place_result
            result['geoid'] = geoid
            result['census_place_name'] = full_place_name
            
            # Step 2: Determine which ACS dataset to use
            # First try 1-year (for 65K+ population)
            acs_data = self.get_acs_data(geoid, use_5_year=False)
            
            if not acs_data or not acs_data.get('population') or acs_data['population'] < 65000:
                # Use 5-year estimates for smaller places
                acs_data = self.get_acs_data(geoid, use_5_year=True)
                
            if not acs_data:
                # Try 5-year as backup
                acs_data = self.get_acs_data(geoid, use_5_year=True)
                
            if not acs_data:
                result['status'] = 'API failed'
                return result
            
            # Step 3: Update result with new data
            result['vintage_used'] = acs_data['vintage']
            result['income_new'] = acs_data.get('median_income')
            result['rent_new'] = acs_data.get('median_rent')
            
            # Step 4: Calculate new affordability score
            if result['income_new'] and current_data.get('basket_cost'):
                new_score = self.calculate_refreshed_affordability_score(
                    result['income_new'], 
                    current_data['basket_cost']
                )
                result['score_new'] = new_score
                
            result['status'] = 'updated'
            
            # Log the update
            self.refresh_log.append(f"✅ {city_name}: ${result['income_old']:,} → ${result['income_new']:,}")
            
            return result
            
        except Exception as e:
            result['status'] = f'error: {str(e)}'
            return result
    
    def generate_new_affordability_guide(self, all_scores: List[float]) -> Dict:
        """Generate new affordability score guide based on refreshed data"""
        if not all_scores:
            return {}
            
        scores = sorted([s for s in all_scores if s > 0])
        
        # Calculate percentile-based thresholds
        n = len(scores)
        
        # Use quartiles for natural breaks
        q1_idx = int(n * 0.25)
        q2_idx = int(n * 0.50) 
        q3_idx = int(n * 0.75)
        q9_idx = int(n * 0.90)
        
        thresholds = {
            'excellent': scores[q1_idx] if q1_idx < n else scores[0],
            'good': scores[q2_idx] if q2_idx < n else scores[0], 
            'moderate': scores[q3_idx] if q3_idx < n else scores[0],
            'at_risk': scores[q9_idx] if q9_idx < n else scores[-1]
        }
        
        return {
            'excellent_access': f"Under {thresholds['excellent']:.1f}%",
            'good_access': f"{thresholds['excellent']:.1f}% - {thresholds['good']:.1f}%",
            'moderate_access': f"{thresholds['good']:.1f}% - {thresholds['moderate']:.1f}%", 
            'food_desert_risk': f"{thresholds['moderate']:.1f}%+",
            'thresholds': thresholds,
            'sample_size': len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'median_score': scores[len(scores)//2]
        }

if __name__ == "__main__":
    refresher = CensusDataRefresh()
    print("Census Data Refresh System Ready")
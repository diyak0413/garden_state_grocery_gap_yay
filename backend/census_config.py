"""
Centralized Census API Configuration with ACS Vintage Control
=============================================================

Feature flag: ACS_VINTAGE in .env controls which Census API endpoint is used.
- 2022 → ACS 2018-2022 5-year estimates (stable baseline)
- 2023 → ACS 2019-2023 5-year estimates (future upgrade)

All Census API calls should import from this module to ensure consistency.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Feature flag from environment
ACS_VINTAGE = os.getenv('ACS_VINTAGE', '2022')

# Census API configuration based on vintage
CENSUS_CONFIG = {
    '2022': {
        'base_url': 'https://api.census.gov/data/2022/acs/acs5',
        'data_vintage': 'ACS 2018–2022 5-year',
        'year_range': '2018-2022',
        'description': 'Stable ACS 5-year estimates covering 2018-2022'
    },
    '2023': {
        'base_url': 'https://api.census.gov/data/2023/acs/acs5',
        'data_vintage': 'ACS 2019–2023 5-year',
        'year_range': '2019-2023',
        'description': 'Latest ACS 5-year estimates covering 2019-2023'
    }
}

def get_census_url():
    """Get Census API base URL for current ACS vintage"""
    return CENSUS_CONFIG[ACS_VINTAGE]['base_url']

def get_data_vintage_label():
    """Get human-readable data vintage label for UI"""
    return CENSUS_CONFIG[ACS_VINTAGE]['data_vintage']

def get_vintage_info():
    """Get complete vintage configuration"""
    return {
        'vintage': ACS_VINTAGE,
        'url': get_census_url(),
        'label': get_data_vintage_label(),
        'year_range': CENSUS_CONFIG[ACS_VINTAGE]['year_range'],
        'description': CENSUS_CONFIG[ACS_VINTAGE]['description']
    }

# Validation
if ACS_VINTAGE not in CENSUS_CONFIG:
    raise ValueError(f"Invalid ACS_VINTAGE: {ACS_VINTAGE}. Must be '2022' or '2023'")

print(f"📊 Census API Configuration:")
print(f"   ACS Vintage: {ACS_VINTAGE}")
print(f"   Endpoint: {get_census_url()}")
print(f"   Label: {get_data_vintage_label()}")

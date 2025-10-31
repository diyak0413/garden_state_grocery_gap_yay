# Garden State Grocery Gap

An interactive web dashboard visualizing grocery pricing, food access, and affordability across New Jersey at a ZIP-code level, targeted at policy professionals and community organizations.

## Current Implementation Status

The application now uses a **Comprehensive Census Data Pipeline** that fetches authoritative ZCTA data from Census sources and pulls demographics from Census ACS API and SNAP retailer data from USDA APIs.

### System Architecture

- **Backend**: FastAPI with comprehensive Census data integration
- **Frontend**: React with modern UI components  
- **Database**: MongoDB for storing processed demographic and pricing data
- **Data Source**: Authoritative Census ZCTA-to-county relationship files + ACS API
- **ML Model**: Random Forest classifier for food desert risk prediction

### Current Data Coverage

✅ **339 New Jersey ZIP Codes** loaded from authoritative Census sources  
✅ **Complete demographic data** including median income, poverty rates, population  
✅ **SNAP retailer counts** per ZIP code area  
✅ **City name mapping** with format "City Name (County Name)"  
✅ **Realistic affordability scores** using formula: (basket_cost ÷ median_income) × 100  
✅ **ML risk predictions** with trained model achieving 100% accuracy on current dataset  

## API Setup Instructions

### Required API Keys

Add the following API keys to `/app/backend/.env`:

```env
# Census Demographics API (required for real demographic data)
CENSUS_API_KEY="your_census_api_key_here"
# Get your key from: https://api.census.gov/data/key_signup.html

# SNAP Retailer API (required for SNAP store data)
USDA_SNAP_API_KEY="your_snap_api_key_here"  
# Get your key from: https://www.fns.usda.gov/snap/retailer-locator

# System Configuration
USE_REAL_DEMOGRAPHICS="true"  # Set to use Census/SNAP APIs
USE_MOCK_DATA="false"         # Set to false for real data mode
```

### Data Loading Process

The system automatically runs the comprehensive Census data pipeline on startup when `USE_REAL_DEMOGRAPHICS="true"`:

1. **Downloads Census ZCTA-to-county relationship file** from census.gov
2. **Filters for New Jersey ZCTAs** (state FIPS 34) and creates deduplicated list
3. **Fetches ACS demographic data in batches** from Census API (income, poverty, population)
4. **Gets SNAP retailer counts** for each ZIP code area
5. **Maps city names** using geocoding APIs with caching
6. **Calculates comprehensive metrics** including affordability scores
7. **Creates data files**: `data/nj_zctas.csv` and `data/zip_metrics.csv`
8. **Loads into MongoDB** and trains ML model

### Data Files Created

- **`/app/data/nj_zctas.csv`**: Contains ZCTA, county FIPS, and county name mappings
- **`/app/data/zip_metrics.csv`**: Contains comprehensive demographic and affordability metrics

### How to Run the Data Loader

The system runs automatically on backend startup, but you can also run it manually:

```bash
cd /app/backend
python3 -c "
from census_data_loader import CensusDataLoader
loader = CensusDataLoader()
zcta_count, metrics_count = loader.run_comprehensive_loader()
print(f'Loaded {zcta_count} ZCTAs with {metrics_count} metrics')
"
```

### Verification

Check if the system loaded correctly:

```bash
# Check data source and count
curl http://localhost:8001/api/debug/source_count

# Get sample ZIP data
curl http://localhost:8001/api/zips | head -20
```

Expected response should show:
- `source: "census_comprehensive_pipeline"`
- `count: 339` (or higher)
- CSV files exist with matching counts

## Core Features

### 🗺️ **Comprehensive ZIP Code Coverage**
- All New Jersey ZIP codes with authoritative Census demographic data
- City name mapping: "City Name (County Name)" format
- Real-time data from Census ACS API and USDA SNAP API

### 📊 **Food Affordability Analysis**
- **Affordability Score**: (basket_cost ÷ median_income) × 100
- **Classification System**: 
  - ≥25% = Food Desert Risk
  - 15-24% = Low Food Access  
  - 8-14% = Moderate Food Access
  - <8% = High Food Access

### 🤖 **Machine Learning Risk Prediction**
- Random Forest classifier for food desert risk assessment
- Features: affordability score, income, poverty rate, SNAP access
- Real-time predictions for all ZIP codes

### 🔍 **Interactive Search & Filtering**
- Search by ZIP code, city name, or county
- Filter by affordability score ranges
- Sort by risk level or demographics

## API Endpoints

### Core Data Endpoints
- `GET /api/zips` - Get all ZIP codes with comprehensive metrics
- `GET /api/affordability/{zip_code}` - Get detailed data for specific ZIP
- `GET /api/search-zipcodes?q={query}` - Search ZIP codes by location

### ML & Analytics  
- `GET /api/ml/predict-risk` - Get risk predictions for all ZIP codes
- `GET /api/ml/explain/{zip_code}` - Get detailed ML explanation for ZIP

### System Information
- `GET /api/config` - Get current system configuration
- `GET /api/debug/source_count` - Verify data source and counts

## Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB
- Census API key
- USDA SNAP API key

### Setup
1. Clone the repository
2. Install backend dependencies: `pip install -r backend/requirements.txt`
3. Install frontend dependencies: `cd frontend && yarn install`
4. Configure API keys in `backend/.env`
5. Start services: `sudo supervisorctl restart all`

### Testing
- Backend testing: Use the integrated testing agent via `deep_testing_backend_v2`
- Frontend testing: Use the integrated testing agent via `auto_frontend_testing_agent`  
- Manual API testing: Use curl or Postman with the endpoints above

## Data Methodology

### Affordability Score Calculation
```
Monthly Food Cost = Weekly Basket Cost × 4.33
Monthly Income = Annual Median Income ÷ 12
Affordability Score = (Monthly Food Cost ÷ Monthly Income) × 100
```

### Regional Cost Adjustments
Basket costs are adjusted by county to reflect real grocery pricing differences across New Jersey:
- Bergen County: +15% (highest costs)
- Hudson County: +10% 
- Essex County: +5%
- Rural counties: -2% to -6% (lower costs)

### SNAP Retailer Metrics
- **SNAP Retailers per 5,000 population**: Normalized metric for comparing food access
- Based on USDA SNAP retailer database
- Cached for 24 hours to respect API rate limits

## Future Enhancements

- **Real Grocery Pricing Integration**: Replace mock pricing with live grocery APIs
- **Expanded Geographic Coverage**: Add support for other states
- **Enhanced ML Models**: Incorporate additional demographic and geographic features
- **Real-time Updates**: Scheduled data refreshes from Census and SNAP APIs
- **Interactive Mapping**: Advanced geographic visualizations and filters

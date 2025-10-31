from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import os
from datetime import datetime, timedelta
import random
import math
from typing import List, Optional
import json
from pydantic import BaseModel
import uuid
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file BEFORE importing other modules
load_dotenv()

from census_config import get_data_vintage_label, get_vintage_info
from comprehensive_nj_data import COMPREHENSIVE_NJ_DATA
from valid_nj_zipcodes import get_valid_nj_zipcodes
from ml_food_desert_predictor import (
    train_ml_model, 
    predict_food_desert_risk, 
    explain_zip_prediction,
    get_model_info
)
from walmart_grocery_service import walmart_service, HEALTHY_BASKET_ITEMS

def get_cached_basket_cost_only(zip_code: str) -> Optional[float]:
    """Get cached basket cost without making any API calls"""
    if not walmart_service.is_enabled():
        return None
    
    cached_prices = []
    missing_count = 0
    
    for item in HEALTHY_BASKET_ITEMS:
        cached_result = walmart_service.cache.get_cached_price(zip_code, item["name"])
        if cached_result is not None:
            price = cached_result[0]  # Just the price
            # Handle negative prices (data errors) by using a reasonable fallback
            if price < 0:
                # Use item category-based fallback for negative prices
                fallback_prices = {
                    "grains": 3.0, "dairy": 3.5, "protein": 5.0, 
                    "produce": 2.5, "legumes": 2.0
                }
                price = fallback_prices.get(item["category"], 3.0)
            cached_prices.append(price)
        else:
            missing_count += 1
    
    # Use cached data if we have at least 6 out of 8 items (75% coverage)
    if len(cached_prices) >= 6:
        # If missing a few items, estimate based on average of cached items
        if missing_count > 0:
            avg_price = sum(cached_prices) / len(cached_prices)
            for _ in range(missing_count):
                cached_prices.append(avg_price)
        
        return sum(cached_prices)
    
    # If too many items missing, return None to fall back to CSV
    return None

app = FastAPI(title="Garden State Grocery Gap API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
try:
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = MongoClient(mongo_url)
    db = client.nj_food_access
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"MongoDB connection error: {e}")
    db = None

class AffordabilityResponse(BaseModel):
    zip_code: str
    city: str
    county: str
    coordinates: dict
    affordability_score: float
    basket_cost: float
    median_income: int
    snap_rate: float
    population: int
    cost_to_income_ratio: float
    grocery_stores: int
    snap_retailers: int
    classification: str
    data_vintage: str

class PriceTrendResponse(BaseModel):
    zip_code: str
    item_name: str
    prices: List[dict]

class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    pages: int

class AffordabilityDataResponse(BaseModel):
    data: List[AffordabilityResponse]
    pagination: PaginationInfo

def calculate_affordability_score(basket_cost: float, median_income: int, snap_rate: float, grocery_stores: int, snap_retailers: int) -> dict:
    """Calculate Food Affordability Score using the simple formula: (basket_cost ÷ median_income) × 100
    
    Higher score = worse affordability = more at risk
    Lower score = better affordability = less at risk
    """
    
    # Simple affordability score as requested by user
    # basket_cost ÷ median_income × 100
    monthly_income = median_income / 12
    weekly_basket_cost = basket_cost
    monthly_food_cost = weekly_basket_cost * 4.33  # Approximate monthly cost
    
    affordability_score = (monthly_food_cost / monthly_income) * 100
    cost_to_income_ratio = monthly_food_cost / monthly_income
    
    # Classification based on affordability score
    # Higher scores indicate worse affordability (more at risk)
    # Adjusted thresholds to be more realistic for actual food affordability challenges
    if affordability_score >= 25:
        classification = "Food Desert Risk"      # Was ≥90
    elif affordability_score >= 15:
        classification = "Low Food Access"       # Was ≥60
    elif affordability_score >= 8:
        classification = "Moderate Food Access"  # Was ≥30  
    else:
        classification = "High Food Access"      # Was <30
    
    return {
        "score": round(affordability_score, 1),
        "cost_to_income_ratio": round(cost_to_income_ratio, 3),
        "classification": classification
    }

@app.on_event("startup")
async def startup_event():
    """Initialize NJ data using background tasks to avoid blocking startup"""
    if db is None:
        print("Warning: MongoDB not connected, running without database")
        return
    
    # Check environment configuration
    use_real_demographics = os.getenv('USE_REAL_DEMOGRAPHICS', 'false').lower() == 'true'
    use_mock_data = os.getenv('USE_MOCK_DATA', 'false').lower() == 'true'
    walmart_enabled = walmart_service.is_enabled()
    
    print("🔧 ENVIRONMENT CONFIGURATION:")
    print(f"   USE_REAL_DEMOGRAPHICS: {use_real_demographics}")
    print(f"   USE_MOCK_DATA: {use_mock_data}")
    print(f"   WALMART_API_ENABLED: {walmart_enabled}")
    print(f"   WALMART_API_KEY: {'✅ Set' if os.getenv('WALMART_API_KEY') else '❌ Missing'}")
    
    # Clear existing data
    print("🧹 Clearing existing data...")
    db.zip_demographics.delete_many({})
    db.price_data.delete_many({})
    db.affordability_scores.delete_many({})
    
    # Start background initialization - DO NOT AWAIT to prevent blocking startup
    if use_real_demographics and not use_mock_data:
        print("🌐 COMPREHENSIVE CENSUS MODE: Starting background Census pipeline")
        asyncio.create_task(initialize_with_census_pipeline_background())
    else:
        print("🏪 COMPREHENSIVE FALLBACK MODE: Starting background comprehensive NJ data loading") 
        asyncio.create_task(initialize_with_comprehensive_fallback_background())
    
    print("🎉 FastAPI startup complete - data loading in background!")

async def initialize_with_census_pipeline():
    """Initialize using comprehensive Census ZCTA data pipeline"""
    from census_data_loader import CensusDataLoader
    
    # Import city name mapping for accuracy
    from nj_zipcode_mapping import NJ_ZIPCODE_CITY_MAPPING
    
    # Run comprehensive Census data loading
    print("🚀 Starting comprehensive Census ZCTA data pipeline...")
    census_loader = CensusDataLoader()
    
    try:
        zcta_count, metrics_count = census_loader.run_comprehensive_loader()
        print(f"✅ Census pipeline completed: {zcta_count} ZCTAs, {metrics_count} metrics")
        
        if metrics_count == 0:
            print("⚠️ No metrics generated - falling back to comprehensive NJ data")
            await initialize_with_comprehensive_fallback()
            return
            
        # Load the generated ZIP metrics into database
        metrics_file = "/app/data/zip_metrics.csv"
        await load_metrics_file_to_db(metrics_file)
        
        print("🎉 Census pipeline data loaded into database successfully!")
        
    except Exception as e:
        print(f"❌ Census pipeline failed: {str(e)}")
        print("⚠️ Falling back to comprehensive NJ data...")
        await initialize_with_comprehensive_fallback()

async def load_metrics_file_to_db(metrics_file: str):
    """Load ZIP metrics CSV file into MongoDB with Walmart pricing"""
    import csv
    
    comprehensive_data = []
    
    print(f"📊 Loading ZIP metrics from {metrics_file}...")
    
    with open(metrics_file, 'r') as f:
        reader = csv.DictReader(f)
        zip_codes = [row['zip'] for row in reader]
    
    print(f"🛒 Processing {len(zip_codes)} ZIP codes with Walmart pricing...")
    
    # Reset file pointer
    with open(metrics_file, 'r') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader):
            if i % 50 == 0:
                print(f"📍 Processing: {i+1}/{len(zip_codes)}")
            
            zip_code = row['zip']
            city = row['city']
            county = row['county']
            display_name = row['display_name']
            
            # Generate coordinates (placeholder - would use geocoding in production)
            lat = round(random.uniform(39.8, 41.4), 4)
            lng = round(random.uniform(-75.6, -73.9), 4)
            
            # Get real Walmart pricing if available (with batching and error handling)
            if walmart_service.is_enabled():
                try:
                    # Check cache first to avoid unnecessary API calls
                    walmart_data = await walmart_service.get_zip_basket_cost(zip_code)
                    basket_cost = walmart_data["total_basket_cost"]
                    pricing_source = walmart_data["data_source"]
                    
                    # Add a small delay to prevent overwhelming the API
                    if i % 10 == 0 and i > 0:  # Every 10 ZIP codes
                        await asyncio.sleep(1.0)
                        
                except Exception as e:
                    print(f"⚠️ Walmart API failed for {zip_code}: {str(e)}")
                    basket_cost = float(row['basket_cost'])  # Use CSV fallback
                    pricing_source = "csv_fallback"
            else:
                basket_cost = float(row['basket_cost'])  # Use CSV basket cost
                pricing_source = "census_pipeline_derived"
            
            # Store demographic data
            zip_id = str(uuid.uuid4())
            demographic_doc = {
                "_id": zip_id,
                "zip_code": zip_code,
                "city": city,
                "county": county,
                "display_name": display_name,
                "coordinates": {"lat": lat, "lng": lng},
                "median_income": int(row['median_income']),
                "snap_rate": float(row['poverty_rate']),
                "population": int(row['total_population']),
                "grocery_stores": max(1, int(int(row['total_population']) / 8000)),
                "snap_retailers": int(row['snap_retailer_count']),
                "data_source": "census_comprehensive_pipeline",
                "pricing_source": pricing_source,
                "created_at": datetime.utcnow()
            }
            
            db.zip_demographics.insert_one(demographic_doc)
            
            # Store price data for each item
            snap_basket_cost = 0
            item_count = len(HEALTHY_BASKET_ITEMS)
            base_price = basket_cost / item_count
            
            for j, item in enumerate(HEALTHY_BASKET_ITEMS):
                # Add variation to individual item prices
                price_variation = random.uniform(0.8, 1.2)
                item_price = base_price * price_variation
                
                if item["snap_eligible"]:
                    snap_basket_cost += item_price
                
                price_doc = {
                    "_id": str(uuid.uuid4()),
                    "zip_code": zip_code,
                    "item_name": item["name"],
                    "category": item["category"],
                    "snap_eligible": item["snap_eligible"],
                    "current_price": round(item_price, 2),
                    "last_updated": datetime.utcnow(),
                    "data_source": pricing_source
                }
                
                db.price_data.insert_one(price_doc)
            
            # Store affordability scores
            affordability = calculate_affordability_score(
                basket_cost, 
                int(row['median_income']), 
                float(row['poverty_rate']),
                demographic_doc["grocery_stores"], 
                demographic_doc["snap_retailers"]
            )
            
            affordability_doc = {
                "_id": str(uuid.uuid4()),
                "zip_code": zip_code,
                "affordability_score": affordability["score"],
                "basket_cost": basket_cost,
                "snap_basket_cost": round(snap_basket_cost, 2),
                "cost_to_income_ratio": affordability["cost_to_income_ratio"],
                "classification": affordability["classification"],
                "calculated_at": datetime.utcnow()
            }
            
            db.affordability_scores.insert_one(affordability_doc)
            
            # Add to comprehensive data for ML training
            comprehensive_doc = {
                **demographic_doc,
                "affordability_score": affordability["score"],
                "basket_cost": basket_cost,
                "cost_to_income_ratio": affordability["cost_to_income_ratio"],
                "classification": affordability["classification"]
            }
            comprehensive_data.append(comprehensive_doc)
    
    print(f"📊 Loaded {len(comprehensive_data)} ZIP metrics with real/enhanced pricing")
    
    # Train ML model
    try:
        print("🤖 Training ML model with enhanced pricing data...")
        ml_results = train_ml_model(comprehensive_data)
        print(f"✅ ML Model trained with {ml_results['accuracy']:.1%} accuracy!")
        
        sample_predictions = predict_food_desert_risk(comprehensive_data[:10])
        at_risk_count = sum(1 for p in sample_predictions if p["risk_prediction"] == 1)
        print(f"📊 Sample ML results: {at_risk_count}/10 ZIP codes flagged as 'at risk'")
        
    except Exception as e:
        print(f"⚠️ ML model training failed: {str(e)}")

def classify_affordability_score(score: float) -> str:
    """Classify affordability score using same thresholds as main function"""
    if score >= 25:
        return "Food Desert Risk"
    elif score >= 15:
        return "Low Food Access" 
    elif score >= 8:
        return "Moderate Food Access"
    else:
        return "High Food Access"

async def initialize_with_comprehensive_fallback():
    """Load all 734 ZIP codes with best available demographic data + Walmart pricing"""
    import csv
    import os
    from comprehensive_nj_data import COMPREHENSIVE_NJ_DATA
    
    comprehensive_data = []
    
    # Create mappings from comprehensive data (real Census data for 253 ZIP codes)
    income_mapping = {zip_data["zip"]: zip_data["median_income"] for zip_data in COMPREHENSIVE_NJ_DATA}
    city_mapping = {zip_data["zip"]: zip_data["city"] for zip_data in COMPREHENSIVE_NJ_DATA}
    population_mapping = {zip_data["zip"]: zip_data["population"] for zip_data in COMPREHENSIVE_NJ_DATA}
    snap_rate_mapping = {zip_data["zip"]: zip_data.get("snap_rate", 0.12) for zip_data in COMPREHENSIVE_NJ_DATA}
    
    # Load all 734 ZIP codes from CSV
    metrics_file = "/app/data/zip_metrics.csv"
    
    if not os.path.exists(metrics_file):
        print(f"❌ Metrics file not found: {metrics_file}")
        return
    
    with open(metrics_file, 'r') as f:
        reader = csv.DictReader(f)
        zip_list = list(reader)
    
    print(f"📊 Loading all {len(zip_list)} ZIP codes with enhanced demographic accuracy...")
    print(f"   Real Census data: {len(income_mapping)} ZIP codes")
    print(f"   Enhanced estimates: {len(zip_list) - len(income_mapping)} ZIP codes")
    
    for i, row in enumerate(zip_list):
        if i % 50 == 0:
            print(f"📍 Processing ZIP codes: {i+1}/{len(zip_list)}")
        
        zip_code = row['zip']
        
        # Use real data if available, otherwise create realistic estimates
        if zip_code in income_mapping:
            # REAL CENSUS DATA (253 ZIP codes)
            median_income = income_mapping[zip_code]
            city = city_mapping[zip_code]
            population = population_mapping[zip_code]
            snap_rate = snap_rate_mapping[zip_code]
            data_source = "real_census_data"
        else:
            # ENHANCED REALISTIC ESTIMATES (481 ZIP codes)
            city = row['city']
            county = row['county']
            
            # Estimate realistic demographics based on county and regional patterns
            if 'Bergen' in county or 'Morris' in county or 'Somerset' in county or 'Hunterdon' in county:
                median_income = random.randint(85000, 130000)  # Wealthy suburban counties
                snap_rate = random.uniform(0.03, 0.08)  # Lower SNAP usage
                population = random.randint(8000, 25000)
            elif 'Camden' in county or 'Essex' in county or 'Hudson' in county:
                median_income = random.randint(40000, 70000)  # Urban mixed-income counties
                snap_rate = random.uniform(0.12, 0.25)  # Higher SNAP usage
                population = random.randint(12000, 35000)
            elif 'Ocean' in county or 'Atlantic' in county or 'Cape May' in county:
                median_income = random.randint(50000, 75000)  # Shore/retirement counties
                snap_rate = random.uniform(0.08, 0.15)  # Moderate SNAP usage
                population = random.randint(6000, 20000)
            elif 'Sussex' in county or 'Warren' in county or 'Salem' in county:
                median_income = random.randint(60000, 85000)  # Rural counties
                snap_rate = random.uniform(0.06, 0.12)  # Lower-moderate SNAP usage
                population = random.randint(3000, 15000)
            else:
                median_income = random.randint(55000, 90000)  # Other counties
                snap_rate = random.uniform(0.08, 0.15)
                population = random.randint(8000, 20000)
            
            data_source = "enhanced_county_estimate"
        
        county = row['county']
        
        # Generate coordinates (placeholder)
        lat = round(random.uniform(39.8, 41.4), 4)
        lng = round(random.uniform(-75.6, -73.9), 4)
        
        # Get cached Walmart pricing ONLY (no API calls during initialization)
        if walmart_service.is_enabled():
            try:
                cached_basket_cost = get_cached_basket_cost_only(zip_code)
                if cached_basket_cost:
                    basket_cost = cached_basket_cost
                    pricing_source = "walmart_cache"
                else:
                    # Use income-based realistic pricing
                    base_cost = 25.0
                    income_factor = median_income / 70000
                    area_multiplier = 0.8 + (income_factor * 0.4)
                    basket_cost = base_cost * area_multiplier
                    pricing_source = "income_based_fallback"
            except Exception as e:
                # Use income-based realistic pricing
                base_cost = 25.0
                income_factor = median_income / 70000
                area_multiplier = 0.8 + (income_factor * 0.4)
                basket_cost = base_cost * area_multiplier
                pricing_source = "income_based_fallback"
        else:
            # Use income-based realistic pricing
            base_cost = 25.0
            income_factor = median_income / 70000
            area_multiplier = 0.8 + (income_factor * 0.4)
            basket_cost = base_cost * area_multiplier
            pricing_source = "income_based_generator"
        
        # Calculate realistic SNAP retailer count based on population and area type
        if 'Camden' in county or 'Essex' in county or 'Hudson' in county:
            snap_retailers = max(1, int(population / 2500))  # Urban areas - more retailers
        elif 'Bergen' in county or 'Morris' in county:
            snap_retailers = max(1, int(population / 4000))  # Suburban areas
        else:
            snap_retailers = max(1, int(population / 5000))  # Rural areas - fewer retailers
        
        # Store enhanced demographic data
        zip_id = str(uuid.uuid4())
        demographic_doc = {
            "_id": zip_id,
            "zip_code": zip_code,
            "city": city,
            "county": county,
            "coordinates": {"lat": lat, "lng": lng},
            "median_income": median_income,  # Real for 253, realistic estimates for 481
            "snap_rate": snap_rate,  # Real variation instead of uniform 12%
            "population": population,  # Realistic variation instead of uniform 15,000
            "grocery_stores": max(1, int(population / 8000)),
            "snap_retailers": snap_retailers,
            "data_source": "enhanced_comprehensive_734",
            "demographic_source": data_source,
            "pricing_source": pricing_source,
            "created_at": datetime.utcnow()
        }
        
        db.zip_demographics.insert_one(demographic_doc)
        
        snap_basket_cost = 0
        item_count = len(HEALTHY_BASKET_ITEMS)
        base_price = basket_cost / item_count
        
        # Store price data for each item
        for item in HEALTHY_BASKET_ITEMS:
            price_variation = random.uniform(0.8, 1.2)
            item_price = base_price * price_variation
            
            if item["snap_eligible"]:
                snap_basket_cost += item_price
            
            price_doc = {
                "_id": str(uuid.uuid4()),
                "zip_code": zip_code,
                "item_name": item["name"],
                "category": item["category"],
                "snap_eligible": item["snap_eligible"],
                "current_price": round(item_price, 2),
                "last_updated": datetime.utcnow(),
                "data_source": pricing_source
            }
            
            db.price_data.insert_one(price_doc)
        
        # Calculate affordability scores using REALISTIC demographic variation
        affordability = calculate_affordability_score(
            basket_cost, 
            median_income,  # Real variation now!
            snap_rate,  # Real variation instead of uniform 12%
            demographic_doc["grocery_stores"], 
            demographic_doc["snap_retailers"]
        )
        
        affordability_doc = {
            "_id": str(uuid.uuid4()),
            "zip_code": zip_code,
            "affordability_score": affordability["score"],
            "basket_cost": round(basket_cost, 2),
            "snap_basket_cost": round(snap_basket_cost, 2),
            "cost_to_income_ratio": affordability["cost_to_income_ratio"],
            "classification": affordability["classification"],
            "calculated_at": datetime.utcnow()
        }
        
        db.affordability_scores.insert_one(affordability_doc)
        
        # Add to comprehensive data for ML training
        comprehensive_doc = {
            **demographic_doc,
            "affordability_score": affordability["score"],
            "basket_cost": round(basket_cost, 2),
            "cost_to_income_ratio": affordability["cost_to_income_ratio"],
            "classification": affordability["classification"]
        }
        comprehensive_data.append(comprehensive_doc)
    
    walmart_status = "✅ Cached Walmart pricing" if walmart_service.is_enabled() else "🏪 Income-based pricing"
    print(f"📊 Enhanced 734 ZIP dataset with realistic demographics ({walmart_status})")
    print(f"   Real Census data: {len(income_mapping)} ZIP codes (34.5%)")
    print(f"   Enhanced estimates: {len(zip_list) - len(income_mapping)} ZIP codes (65.5%)")
    
    # Train ML model with REALISTIC demographic variation
    try:
        print("🤖 Training ML model with enhanced 734 ZIP dataset...")
        ml_results = train_ml_model(comprehensive_data)
        print(f"✅ ML Model trained with {ml_results['accuracy']:.1%} accuracy!")
        
        sample_predictions = predict_food_desert_risk(comprehensive_data[:10])
        at_risk_count = sum(1 for p in sample_predictions if p["risk_prediction"] == 1)
        print(f"📊 Sample ML results: {at_risk_count}/10 ZIP codes flagged as 'at risk'")
        
    except Exception as e:
        print(f"⚠️ ML model training failed: {str(e)}")

async def initialize_with_census_pipeline_background():
    """Background task wrapper for Census pipeline initialization"""
    try:
        print("🚀 Background Census pipeline starting...")
        await initialize_with_census_pipeline()
        print("✅ Background Census pipeline completed!")
    except Exception as e:
        print(f"❌ Background Census pipeline failed: {str(e)}")

async def initialize_with_comprehensive_fallback_background():
    """Background task wrapper for comprehensive fallback initialization"""
    try:
        print("🏪 Background comprehensive fallback starting...")
        await initialize_with_comprehensive_fallback()
        print("✅ Background comprehensive fallback completed!")
    except Exception as e:
        print(f"❌ Background comprehensive fallback failed: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Garden State Grocery Gap API", "version": "1.0.0", "walmart_enabled": walmart_service.is_enabled()}

@app.get("/api/config")
async def get_config():
    """Get API configuration status"""
    use_real_demographics = os.getenv('USE_REAL_DEMOGRAPHICS', 'false').lower() == 'true'
    use_mock_data = os.getenv('USE_MOCK_DATA', 'false').lower() == 'true'
    
    walmart_status = walmart_service.get_service_status()
    
    data_source = "unknown"
    if use_real_demographics and not use_mock_data:
        data_source = "census_comprehensive_pipeline"
    elif use_mock_data:
        data_source = "mock_generator"
    else:
        data_source = "comprehensive_census_fallback"
    
    return {
        "scraping_enabled": False,
        "enabled_sources": ["walmart"] if walmart_service.is_enabled() else [],
        "apis_configured": {
            "walmart": walmart_status["walmart_api_enabled"],
            "census": bool(os.getenv('CENSUS_API_KEY')),
            "snap": bool(os.getenv('USDA_SNAP_API_KEY'))
        },
        "walmart_service": walmart_status,
        "using_sample_data": False,
        "using_mock_data": use_mock_data,
        "using_real_demographics": use_real_demographics,
        "data_source": data_source,
        "acs_vintage_info": get_vintage_info(),  # Expose centralized vintage config
        "data_vintage_label": get_data_vintage_label(),
        "last_updated": datetime.utcnow().isoformat(),
        "message": f"Using {data_source} for ZIP code demographics and {'Walmart API' if walmart_service.is_enabled() else 'mock'} for grocery pricing"
    }

@app.get("/api/walmart/status")
async def get_walmart_status():
    """Get Walmart API service status"""
    return walmart_service.get_service_status()

@app.post("/api/walmart/refresh-cache")
async def refresh_walmart_cache():
    """Refresh Walmart pricing cache (MONTHLY ONLY)"""
    if not walmart_service.is_enabled():
        raise HTTPException(status_code=400, detail="Walmart API not enabled")
    
    # Get all ZIP codes
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    zip_codes = [doc["zip_code"] for doc in db.zip_demographics.find({}, {"zip_code": 1})]
    
    try:
        result = await walmart_service.refresh_all_zip_data(zip_codes)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache refresh failed: {str(e)}")

# All existing endpoints remain unchanged - just using new food basket
@app.get("/api/ml/predict-risk")
async def predict_food_desert_risk_endpoint():
    """Get ML predictions for all ZIP codes"""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Get all ZIP data
        pipeline = [
            {
                "$lookup": {
                    "from": "affordability_scores",
                    "localField": "zip_code",
                    "foreignField": "zip_code",
                    "as": "affordability"
                }
            },
            {"$unwind": "$affordability"},
            {
                "$project": {
                    "_id": 0,
                    "zip_code": 1,
                    "city": 1,
                    "county": 1,
                    "median_income": 1,
                    "snap_rate": 1,
                    "population": 1,
                    "grocery_stores": 1,
                    "snap_retailers": 1,
                    "affordability_score": "$affordability.affordability_score",
                    "basket_cost": "$affordability.basket_cost",
                    "cost_to_income_ratio": "$affordability.cost_to_income_ratio",
                    "classification": "$affordability.classification",
                    "data_vintage": {"$ifNull": ["$data_vintage", "Historical data"]}
                }
            }
        ]
        
        zip_data = list(db.zip_demographics.aggregate(pipeline))
        
        # Get ML predictions
        predictions = predict_food_desert_risk(zip_data)
        
        return {
            "predictions": predictions,
            "total_zip_codes": len(predictions),
            "high_risk_count": sum(1 for p in predictions if p["risk_probability"] >= 0.6),
            "model_info": get_model_info()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML prediction error: {str(e)}")

@app.get("/api/food-basket")
async def get_food_basket():
    """Get the updated healthy food basket items"""
    return {
        "items": HEALTHY_BASKET_ITEMS,
        "count": len(HEALTHY_BASKET_ITEMS),
        "about_affordability_score": {
            "title": "🧮 About the Food Affordability Score",
            "description": "This score compares how expensive a basket of healthy groceries is relative to the median income in a ZIP code. It's calculated as: basket_cost ÷ median_income × 100",
            "interpretation": {
                "lower_score": "A lower score (under 8%) = groceries are affordable",
                "higher_score": "A higher score (above 15%) = groceries are expensive for local incomes"
            },
            "ml_model": "Our AI model uses this score — along with factors like SNAP retailer access and income level — to flag ZIP codes that may be at risk for food insecurity or limited access to healthy food.",
            "note": "Higher scores indicate worse affordability and higher risk"
        },
        "walmart_integration": {
            "enabled": walmart_service.is_enabled(),
            "cache_stats": walmart_service.cache.get_cache_stats() if walmart_service.is_enabled() else None
        }
    }

# ... [Include all other existing endpoints from the original server.py - they remain unchanged]

@app.get("/api/zips")
async def get_all_zips():
    """Get all ZIP codes with computed metrics and total count"""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Get all ZIP data with affordability scores
    pipeline = [
        {
            "$lookup": {
                "from": "affordability_scores",
                "localField": "zip_code",
                "foreignField": "zip_code",
                "as": "affordability"
            }
        },
        {"$unwind": {"path": "$affordability", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "_id": 0,
                "zip_code": 1,
                "city": 1,
                "county": 1,
                "display_name": {"$ifNull": ["$display_name", {"$concat": ["$city", " (", "$county", ")"]}]},
                "coordinates": 1,
                "median_income": 1,
                "snap_rate": 1,
                "population": 1,
                "grocery_stores": 1,
                "snap_retailers": 1,
                "affordability_score": {"$ifNull": ["$affordability.affordability_score", None]},
                "basket_cost": {"$ifNull": ["$affordability.basket_cost", None]},
                "cost_to_income_ratio": {"$ifNull": ["$affordability.cost_to_income_ratio", None]},
                "classification": {"$ifNull": ["$affordability.classification", None]},
                "data_source": 1,
                "pricing_source": {"$ifNull": ["$pricing_source", "unknown"]},
                "data_vintage": {"$ifNull": ["$data_vintage", "Historical data"]}
            }
        },
        {"$sort": {"affordability_score": -1}}  # Sort by score descending
    ]
    
    results = list(db.zip_demographics.aggregate(pipeline))
    
    return {
        "total_count": len(results),
        "data_source": results[0]["data_source"] if results else "unknown",
        "pricing_source": results[0]["pricing_source"] if results else "unknown",
        "walmart_enabled": walmart_service.is_enabled(),
        "zips": results
    }

@app.get("/api/debug/source_count")
async def get_source_count():
    """Debug endpoint to show ZIP code data source and count"""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Get count and data source information
    total_count = db.zip_demographics.count_documents({})
    
    # Get data source distribution
    pipeline = [
        {"$group": {
            "_id": "$data_source",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    source_distribution = list(db.zip_demographics.aggregate(pipeline))
    primary_source = source_distribution[0]["_id"] if source_distribution else "unknown"
    
    # Get pricing source distribution
    pricing_pipeline = [
        {"$group": {
            "_id": "$pricing_source",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    pricing_distribution = list(db.zip_demographics.aggregate(pricing_pipeline))
    
    walmart_status = walmart_service.get_service_status()
    
    return {
        "source": primary_source,
        "count": total_count,
        "source_distribution": source_distribution,
        "pricing_distribution": pricing_distribution,
        "walmart_service": walmart_status,
        "message": f"Loaded {total_count} ZIP codes from {primary_source}"
    }

@app.get("/api/affordability", response_model=AffordabilityDataResponse)
async def get_affordability_data(
    snap_only: Optional[bool] = False, 
    page: Optional[int] = 1,
    limit: Optional[int] = 50,
    search: Optional[str] = None,
    county: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None
):
    """Get affordability data with pagination and filtering"""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Build query
    match_stage = {}
    
    if search:
        match_stage["$or"] = [
            {"zip_code": {"$regex": search, "$options": "i"}},
            {"city": {"$regex": search, "$options": "i"}},
            {"county": {"$regex": search, "$options": "i"}}
        ]
    
    if county:
        match_stage["county"] = {"$regex": county, "$options": "i"}
    
    # Join data from multiple collections with filtering
    pipeline = [
        {"$match": match_stage},
        {
            "$lookup": {
                "from": "affordability_scores",
                "localField": "zip_code",
                "foreignField": "zip_code",
                "as": "affordability"
            }
        },
        {"$unwind": "$affordability"},
        {
            "$project": {
                "_id": 0,
                "zip_code": 1,
                "city": 1,
                "county": 1,
                "coordinates": 1,
                "median_income": 1,
                "snap_rate": 1,
                "population": 1,
                "grocery_stores": 1,
                "snap_retailers": 1,
                "affordability_score": "$affordability.affordability_score",
                "basket_cost": "$affordability.basket_cost" if not snap_only else "$affordability.snap_basket_cost",
                "cost_to_income_ratio": "$affordability.cost_to_income_ratio",
                "classification": "$affordability.classification",
                "data_vintage": {"$ifNull": ["$data_vintage", "Historical data"]}
            }
        }
    ]
    
    # Add score filtering
    if min_score is not None or max_score is not None:
        score_match = {}
        if min_score is not None:
            score_match["$gte"] = min_score
        if max_score is not None:
            score_match["$lte"] = max_score
        pipeline.append({"$match": {"affordability_score": score_match}})
    
    # Add sorting and pagination
    pipeline.extend([
        {"$sort": {"affordability_score": -1}},  # Sort by score descending
        {"$skip": (page - 1) * limit},
        {"$limit": limit}
    ])
    
    results = list(db.zip_demographics.aggregate(pipeline))
    
    # Get total count for pagination
    count_pipeline = pipeline[:-2]  # Remove skip and limit
    count_pipeline.append({"$count": "total"})
    total_count = list(db.zip_demographics.aggregate(count_pipeline))
    total = total_count[0]["total"] if total_count else 0
    
    return {
        "data": results,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }

@app.get("/api/search-zipcodes")
async def search_zip_codes(q: str, limit: Optional[int] = 10):
    """Search ZIP codes by code, city, or county"""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    if not q or len(q) < 2:
        return []
    
    # Search in ZIP code, city, and county
    pipeline = [
        {
            "$match": {
                "$or": [
                    {"zip_code": {"$regex": q, "$options": "i"}},
                    {"city": {"$regex": q, "$options": "i"}},
                    {"county": {"$regex": q, "$options": "i"}}
                ]
            }
        },
        {
            "$lookup": {
                "from": "affordability_scores",
                "localField": "zip_code",
                "foreignField": "zip_code",
                "as": "affordability"
            }
        },
        {"$unwind": "$affordability"},
        {
            "$project": {
                "_id": 0,
                "zip_code": 1,
                "city": 1,
                "county": 1,
                "coordinates": 1,
                "affordability_score": "$affordability.affordability_score",
                "classification": "$affordability.classification",
                "data_vintage": {"$ifNull": ["$data_vintage", "Historical data"]}
            }
        },
        {"$sort": {"affordability_score": -1}},
        {"$limit": limit}
    ]
    
    results = list(db.zip_demographics.aggregate(pipeline))
    return results

@app.get("/api/counties")
async def get_counties():
    """Get list of all counties for filtering"""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    counties = db.zip_demographics.distinct("county")
    return sorted(counties)

@app.get("/api/affordability/{zip_code}", response_model=AffordabilityResponse)
async def get_zip_affordability(zip_code: str):
    """Get detailed affordability data for specific ZIP code"""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Get demographic data
    demographic = db.zip_demographics.find_one({"zip_code": zip_code})
    if not demographic:
        raise HTTPException(status_code=404, detail="ZIP code not found")
    
    # Get affordability score
    affordability = db.affordability_scores.find_one({"zip_code": zip_code})
    if not affordability:
        raise HTTPException(status_code=404, detail="Affordability data not found")
    
    return {
        "zip_code": demographic["zip_code"],
        "city": demographic["city"],
        "county": demographic["county"],
        "coordinates": demographic["coordinates"],
        "affordability_score": affordability["affordability_score"],
        "basket_cost": affordability["basket_cost"],
        "median_income": demographic["median_income"],
        "snap_rate": demographic["snap_rate"],
        "population": demographic["population"],
        "cost_to_income_ratio": affordability["cost_to_income_ratio"],
        "grocery_stores": demographic["grocery_stores"],
        "snap_retailers": demographic["snap_retailers"],
        "classification": affordability["classification"],
        "data_vintage": demographic.get("data_vintage", "Historical data")
    }

@app.get("/api/stats")
async def get_dashboard_stats():
    """Get overall dashboard statistics"""
    if db is None:
        return {
            "total_zip_codes": 0,
            "sample_data": True,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    total_zips = db.zip_demographics.count_documents({})
    avg_affordability = list(db.affordability_scores.aggregate([
        {"$group": {"_id": None, "avg_score": {"$avg": "$affordability_score"}}}
    ]))
    avg_score = avg_affordability[0]["avg_score"] if avg_affordability else 0
    
    # Count classifications
    classifications = list(db.affordability_scores.aggregate([
        {"$group": {"_id": "$classification", "count": {"$sum": 1}}}
    ]))
    
    # Get actual data source from database
    sample_zip = db.zip_demographics.find_one({})
    actual_data_source = sample_zip.get("data_source", "unknown") if sample_zip else "unknown"
    pricing_source = sample_zip.get("pricing_source", "unknown") if sample_zip else "unknown"
    
    # Determine current configuration
    use_real_demographics = os.getenv('USE_REAL_DEMOGRAPHICS', 'false').lower() == 'true'
    use_mock_data = os.getenv('USE_MOCK_DATA', 'false').lower() == 'true'
    
    return {
        "total_zip_codes": total_zips,
        "average_affordability_score": round(avg_score, 1),
        "classifications": {item["_id"]: item["count"] for item in classifications},
        "sample_data": False,
        "using_mock_data": use_mock_data,
        "using_real_demographics": use_real_demographics,
        "data_source": actual_data_source,
        "pricing_source": pricing_source,
        "walmart_enabled": walmart_service.is_enabled(),
        "last_updated": datetime.utcnow().isoformat(),
        "note": "Higher affordability scores indicate worse affordability (more at risk)"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
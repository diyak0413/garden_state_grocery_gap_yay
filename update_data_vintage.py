#!/usr/bin/env python3
"""
Update data_vintage field in MongoDB to "ACS 2019-2023 5-year" for all records
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_data_vintage():
    """Update all records in MongoDB to have data_vintage = 'ACS 2019-2023 5-year'"""
    
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = MongoClient(mongo_url)
    db = client.nj_food_access
    
    data_vintage = "ACS 2019-2023 5-year"
    
    print(f"🔄 Updating data_vintage to '{data_vintage}' for all records...")
    
    # Update zip_demographics collection
    demographics_result = db.zip_demographics.update_many(
        {},  # Update all documents
        {"$set": {"data_vintage": data_vintage}}
    )
    
    print(f"✅ Updated {demographics_result.modified_count} records in zip_demographics collection")
    
    # Update affordability_scores collection
    affordability_result = db.affordability_scores.update_many(
        {},  # Update all documents
        {"$set": {"data_vintage": data_vintage}}
    )
    
    print(f"✅ Updated {affordability_result.modified_count} records in affordability_scores collection")
    
    # Update price_data collection
    price_result = db.price_data.update_many(
        {},  # Update all documents
        {"$set": {"data_vintage": data_vintage}}
    )
    
    print(f"✅ Updated {price_result.modified_count} records in price_data collection")
    
    print(f"🎉 Successfully updated all records with data_vintage = '{data_vintage}'")
    
    # Verify the update
    sample_record = db.zip_demographics.find_one({})
    if sample_record:
        print(f"📋 Verification - Sample record data_vintage: {sample_record.get('data_vintage', 'Missing')}")
    
    client.close()

if __name__ == "__main__":
    update_data_vintage()
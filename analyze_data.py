#!/usr/bin/env python3

from pymongo import MongoClient
import os

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = MongoClient(mongo_url)
db = client.nj_food_access

print('=== AFFORDABILITY SCORE ANALYSIS ===')
# Get sample of affordability data
pipeline = [
    {'$lookup': {
        'from': 'affordability_scores',
        'localField': 'zip_code',  
        'foreignField': 'zip_code',
        'as': 'affordability'
    }},
    {'$unwind': '$affordability'},
    {'$project': {
        'zip_code': 1,
        'city': 1,
        'median_income': 1,
        'affordability_score': '$affordability.affordability_score',
        'basket_cost': '$affordability.basket_cost'
    }},
    {'$sort': {'affordability_score': -1}},
    {'$limit': 10}
]

results = list(db.zip_demographics.aggregate(pipeline))

print('TOP 10 HIGHEST AFFORDABILITY SCORES:')
for r in results:
    score = r['affordability_score'] 
    basket = r['basket_cost']
    income = r['median_income']
    print(f"{r['zip_code']} ({r['city']}): Score={score:.1f}%, Basket=${basket:.2f}, Income=${income:,}")

print()
print('=== SCORE DISTRIBUTION ===')
# Get score distribution
ranges = [
    (0, 5, 'Very Low (0-5%)'),
    (5, 10, 'Low (5-10%)'), 
    (10, 15, 'Moderate (10-15%)'),
    (15, 25, 'High (15-25%)'),
    (25, 100, 'Very High (25%+)')
]

for min_score, max_score, label in ranges:
    count = db.affordability_scores.count_documents({
        'affordability_score': {'$gte': min_score, '$lt': max_score}
    })
    print(f'{label}: {count} ZIP codes')

print()
print('=== MEDIAN INCOME ANALYSIS ===')
income_pipeline = [
    {'$group': {
        '_id': None,
        'avg_income': {'$avg': '$median_income'},
        'min_income': {'$min': '$median_income'},
        'max_income': {'$max': '$median_income'}
    }}
]

income_stats = list(db.zip_demographics.aggregate(income_pipeline))[0]
print(f"Average median income: ${income_stats['avg_income']:,.0f}")
print(f"Min median income: ${income_stats['min_income']:,}")
print(f"Max median income: ${income_stats['max_income']:,}")

print()
print('=== BASKET COST ANALYSIS ===')
basket_pipeline = [
    {'$group': {
        '_id': None,
        'avg_basket': {'$avg': '$basket_cost'},
        'min_basket': {'$min': '$basket_cost'},
        'max_basket': {'$max': '$basket_cost'}
    }}
]

basket_stats = list(db.affordability_scores.aggregate(basket_pipeline))[0]
print(f"Average basket cost: ${basket_stats['avg_basket']:,.2f}")
print(f"Min basket cost: ${basket_stats['min_basket']:,.2f}")
print(f"Max basket cost: ${basket_stats['max_basket']:,.2f}")
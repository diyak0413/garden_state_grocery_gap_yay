"""
DEPRECATED: Walmart Scraper using SearchAPI.io - Use walmart_grocery_service.py instead
This scraper is deprecated in favor of the official Walmart API integration
"""

import logging

logger = logging.getLogger(__name__)

class WalmartScraper:
    """DEPRECATED - Use WalmartGroceryService with official Walmart API instead"""
    
    def __init__(self):
        self.enabled = False
        logger.warning("⚠️ WalmartScraper (SearchAPI.io) is DEPRECATED. Use WalmartGroceryService (official API) instead.")
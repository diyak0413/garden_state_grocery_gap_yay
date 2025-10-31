"""
DEPRECATED: Grocery Scraping Service - Use walmart_grocery_service.py instead
This service is deprecated in favor of the official Walmart API integration
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class GroceryScrapingService:
    """DEPRECATED - Use walmart_grocery_service.py for current grocery pricing"""
    
    def __init__(self, db):
        self.db = db
        logger.warning("⚠️ GroceryScrapingService is DEPRECATED. Use WalmartGroceryService instead.")
        
    def is_scraping_enabled(self) -> bool:
        """DEPRECATED - Always returns False"""
        return False
    
    def get_enabled_sources(self) -> List[str]:
        """DEPRECATED - Returns empty list"""
        return []
    
    def get_scraping_status(self) -> Dict:
        """DEPRECATED - Returns deprecation status"""
        return {
            "deprecated": True,
            "message": "Use walmart_grocery_service.py for current grocery pricing",
            "scraping_enabled": False,
            "enabled_sources": []
        }
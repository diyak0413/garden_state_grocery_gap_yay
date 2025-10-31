"""
DEPRECATED: Instacart Scraper - No longer supported
Use walmart_grocery_service.py for current grocery pricing
"""

import logging

logger = logging.getLogger(__name__)

class InstacartScraper:
    """DEPRECATED - Instacart scraper no longer supported"""
    
    def __init__(self):
        self.enabled = False
        logger.warning("⚠️ InstacartScraper is DEPRECATED. Use WalmartGroceryService instead.")
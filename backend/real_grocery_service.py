"""
Legacy Real Grocery Data Integration System - DEPRECATED
Use walmart_grocery_service.py for current Walmart API integration
"""

import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class RealGroceryDataService:
    """DEPRECATED - Legacy grocery service. Use walmart_grocery_service.py instead"""
    
    def __init__(self):
        logger.warning("⚠️ RealGroceryDataService is DEPRECATED. Use walmart_grocery_service.py instead.")
        logger.info("🔄 Redirecting to WalmartGroceryService for all grocery pricing needs.")

# Global instance for backward compatibility
real_grocery_service = RealGroceryDataService()

# Easy activation function
def is_real_grocery_data_enabled() -> bool:
    """DEPRECATED - Check walmart_grocery_service.py instead"""
    logger.warning("⚠️ is_real_grocery_data_enabled() is DEPRECATED. Use walmart_service.is_enabled() instead.")
    return False
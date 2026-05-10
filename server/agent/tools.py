"""
LangGraph-compatible tools for wardrobe search and filtering.
Exposes wardrobe search functionality as structured tools for agent workflows.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool

from vectordb import WardrobeVectorDB
from gemini import GeminiClient
from google.genai import types
from config import *

# Configure logging
logger = logging.getLogger(__name__)

# Initialize VectorDB instance
_vdb_instance: Optional[WardrobeVectorDB] = None


def get_vdb() -> WardrobeVectorDB:
    """Get or create the WardrobeVectorDB singleton instance."""
    global _vdb_instance
    if _vdb_instance is None:
        _vdb_instance = WardrobeVectorDB()
    return _vdb_instance


@tool
def search_wardrobe(
    query: str, 
    limit: int = 10,
    filters: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Search the wardrobe using natural language semantic search with optional metadata filters.
    
    Args:
        query (str): Natural language search query (e.g., "blue summer shirts", "casual outfits")
        limit (int): Maximum number of results to return (default: 10)
        filters (Dict[str, List[str]]): Optional metadata filters dictionary. Example:
            {
                "primary_category": ["Top", "Bottom"],
                "primary_color": ["Blue"],
                "season": ["Summer"],
                "occasion": ["Casual"],
                "style_vibe": ["Minimalist"],
                "pattern": ["Solid"],
                "material": ["Cotton"],
                "fit": ["Oversized"]
            }
            
            Valid keys and their possible values:
            - primary_category: ["Top", "Bottom", "Outerwear", "Footwear", "Accessory", "Full-body"]
            - primary_color: ["Black", "White", "Grey", "Navy", "Blue", "Red", "Green", "Yellow", "Orange", "Purple", "Pink", "Brown", "Beige", "Gold", "Silver", "Multicolor"]
            - season: ["Spring", "Summer", "Fall", "Winter", "All-Season"]
            - occasion: ["Casual", "Smart-Casual", "Business-Formal", "Athletic/Gym", "Lounge", "Night-Out", "Formal/Black-Tie"]
            - style_vibe: ["Minimalist", "Streetwear", "Vintage/Retro", "Preppy", "Grunge", "Techwear", "Bohemian", "Classic", "Other"]
            - pattern: ["Solid", "Striped", "Check", "Floral", "Graphic", "Geometric", "Animal Print", "Houndstooth", "Camo", "Other"]
            - material: ["Cotton", "Denim", "Leather", "Wool", "Linen", "Silk", "Synthetic", "Knit", "Velvet", "Suede", "Other"]
            - fit: ["Slim", "Regular", "Oversized", "Tailored", "Cropped", "Other"]
        
    Returns:
        Dict with search results and metadata
    """
    try:
        logger.info(f"Search tool called with query: '{query}'")
        vdb = get_vdb()
        
        if filters:
            logger.info(f"Applying filters: {filters}")
        
        # Perform semantic search with optional filters
        search_results = vdb.search(query, limit=limit, filters=filters)
        logger.info(f"Search returned {len(search_results)} results")
        
        return {
            "tool_type": "search",
            "items": search_results,
            "count": len(search_results),
            "query": query,
            "filters_applied": list(filters.keys()) if filters else []
        }
        
    except Exception as e:
        logger.error(f"Error in search_wardrobe tool: {e}")
        return {
            "tool_type": "search",
            "items": [],
            "count": 0,
            "query": query,
            "error": str(e)
        }

# Export all tools for LangGraph
__all__ = [
    "search_wardrobe", 
]

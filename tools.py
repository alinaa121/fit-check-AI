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
def search_wardrobe(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search the wardrobe using natural language semantic search.
    
    Simple semantic search - agent already understands the query,
    just return matching items with their IDs for the agent to reference.
    
    Args:
        query (str): Natural language search query (e.g., "blue summer shirts", "casual outfits")
        limit (int): Maximum number of results to return (default: 10)
        
    Returns:
        Dict with:
            - items: List of dicts with 'id' and 'description' for each matching item
            - count: Number of items returned
            - query: The original query string
            - tool_type: "search" for identification
            
    Example:
        >>> result = search_wardrobe("blue summer shirts")
        >>> result['items']
        [
            {"id": "abc123", "description": "Blue cotton summer shirt"},
            {"id": "def456", "description": "Light blue linen beach shirt"}
        ]
    """
    try:
        logger.info(f"Search tool called with query: '{query}'")
        vdb = get_vdb()
        
        # Perform semantic search directly - agent already understands the intent
        search_results = vdb.search(query, limit=limit)
        logger.info(f"Search returned {len(search_results)} results")
        
        # Format results with id and description
        formatted_items = [
            {
                "id": item.get("id"),
                "description": item.get("raw_caption", "")
            }
            for item in search_results
        ]
        
        return {
            "tool_type": "search",
            "items": formatted_items,
            "count": len(formatted_items),
            "query": query
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

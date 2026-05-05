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
from config import (
    generate_outfit_combinations_model,
    generate_outfit_combinations_prompt,
    generate_outfit_combinations_json_schema
)

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
    Search the wardrobe using natural language query with AI-powered filtering.
    
    Extracts structured filters from the natural language query using Gemini,
    performs semantic search with those filters, and returns matching items
    with their IDs and descriptions.
    
    Args:
        query (str): Natural language search query (e.g., "blue summer shirts", "casual weekend outfits")
        limit (int): Maximum number of results to return (default: 10)
        
    Returns:
        Dict with:
            - items: List of dicts with 'id' and 'description' for each matching item
            - count: Number of items returned
            - filters_extracted: The filters extracted from the query
            - query: The original query string
            
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
        
        # Step 1: Extract filters from natural language query
        filters = vdb.extract_filters_from_query(query)
        logger.info(f"Extracted filters: {filters}")
        
        if filters is None:
            logger.warning("Failed to extract filters, proceeding with semantic search only")
            filters = {}
        
        # Step 2: Count items matching filters
        count = vdb.count_items(filters) if filters else 0
        logger.info(f"Found {count} items matching filters")
        
        # Step 3: Perform search with filters if found items, otherwise search all
        search_results = []
        if count > 1:
            search_results = vdb.search(query, limit=limit, filters=filters)
        else:
            search_results = vdb.search(query, limit=limit)
        
        logger.info(f"Search returned {len(search_results)} results")
        
        # Step 4: Format results for LangGraph with id and description
        formatted_items = [
            {
                "id": item.get("id"),
                "description": item.get("raw_caption", "")
            }
            for item in search_results
        ]
        
        return {
            "items": formatted_items,
            "count": len(formatted_items),
            "filters_extracted": filters or {},
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Error in search_wardrobe tool: {e}")
        return {
            "items": [],
            "count": 0,
            "filters_extracted": {},
            "query": query,
            "error": str(e)
        }



@tool
def generate_outfit_combinations(
    items: List[Dict[str, str]],
    agent_request: str,
    num_combinations: int = 3
) -> Dict[str, Any]:
    """
    Generate outfit combinations from a list of wardrobe items using AI.
    
    Takes search results and the agent's request context (which may have been refined during search),
    then uses Gemini to create outfit pairings that match the styling goal. Combinations can be either 
    (top + bottom) or a single full-body item, plus optional footwear and accessories.
    
    Args:
        items (List[Dict[str, str]]): List of items with 'id' and 'description' keys.
            Example: [{"id": "abc123", "description": "Blue cotton shirt"}, ...]
        agent_request (str): The agent's request context - may be refined/modified from original user query 
            (e.g., "casual summer looks", "professional work outfits", or refined like "light colored items for beach")
        num_combinations (int): Number of outfit combinations to generate (default: minimum 3)
        
    Returns:
        Dict with:
            - combinations: List of outfit dicts with:
                - combo_id: Unique combination ID
                - top: {"id": "...", "description": "..."} or null
                - bottom: {"id": "...", "description": "..."} or null
                - full_body: {"id": "...", "description": "..."} or null (either top+bottom OR full_body)
                - footwear: {"id": "...", "description": "..."} or null (optional)
                - accessories: List of {"id": "...", "description": "..."} (optional, may be empty)
                - reasoning: Why this combination works well
                - style_tips: Additional styling suggestions
            - count: Number of combinations generated
            - success: Whether combinations were generated successfully
            
    Example:
        >>> items = [
        ...     {"id": "vectordbid1", "description": "Blue cotton shirt"},
        ...     {"id": "vectordbid2", "description": "Black denim jeans"},
        ...     {"id": "vectordbid3", "description": "White leather sneakers"}
        ... ]
        >>> result = generate_outfit_combinations(items, "casual summer beach outfits - light colors preferred")
        >>> result['combinations'][0]
        {
            "combo_id": 1,
            "top": {"id": "vectordbid1", "description": "Blue cotton shirt"},
            "bottom": {"id": "vectordbid2", "description": "Black denim jeans"},
            "full_body": null,
            "footwear": {"id": "vectordbid3", "description": "White leather sneakers"},
            "accessories": [],
            "reasoning": "Classic casual look - the blue and black contrast is timeless...",
            "style_tips": "Roll up the sleeves for a more relaxed feel"
        }
    """
    try:
        logger.info(f"Generating {num_combinations} outfit combinations from {len(items)} items")
        
        # Initialize Gemini client
        gemini_client = GeminiClient()
        
        # Format items for the prompt
        items_text = "\n".join([
            f"- ID: {item['id']}, Description: {item['description']}"
            for item in items
        ])
        
        # Create the prompt from config template
        combination_prompt = generate_outfit_combinations_prompt.format(
            agent_request=agent_request,
            items_text=items_text,
            num_combinations=num_combinations
        )
        
        logger.info("Calling Gemini to generate outfit combinations")
        response = gemini_client.call_gemini(
            content_parts=[types.Part(text=combination_prompt)],
            model=generate_outfit_combinations_model
        )
        
        if response is None:
            logger.error("Gemini returned None response")
            return {
                "combinations": [],
                "count": 0,
                "success": False,
                "error": "Failed to get response from Gemini"
            }
        
        # Extract text from response
        response_text = response.candidates[0].content.parts[0].text
        logger.info(f"Gemini response: {response_text[:200]}...")
        
        # Parse JSON from response
        # Remove markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        combinations_data = json.loads(response_text)
        
        if not isinstance(combinations_data, dict) or "combinations" not in combinations_data:
            logger.error("Invalid response structure from Gemini")
            return {
                "combinations": [],
                "count": 0,
                "success": False,
                "error": "Invalid response structure from Gemini"
            }
        
        combinations = combinations_data.get("combinations", [])
        logger.info(f"Generated {len(combinations)} outfit combinations")
        
        return {
            "combinations": combinations,
            "count": len(combinations),
            "success": True
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Gemini response: {e}")
        return {
            "combinations": [],
            "count": 0,
            "success": False,
            "error": f"Failed to parse combinations: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error in generate_outfit_combinations tool: {e}")
        return {
            "combinations": [],
            "count": 0,
            "success": False,
            "error": str(e)
        }


# Export all tools for LangGraph
__all__ = [
    "search_wardrobe",
    "filter_wardrobe",
    "generate_outfit_combinations"
]

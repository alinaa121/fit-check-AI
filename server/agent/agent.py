"""
Wardrobe AI Agent - True Agentic AI with Gemini LLM

This module defines a truly agentic agent where Gemini LLM decides which tools 
to call and when to stop. No hardcoded sequences - pure LLM reasoning and decision-making.
"""

import json
import os
import logging
import re
from typing import Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from vectordb import WardrobeVectorDB
from dotenv import load_dotenv

from .tools import *
from config import agent_system_prompt, agent_model, agent_temperature, agent_top_p

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Gemini LLM
llm = ChatGoogleGenerativeAI(
    model=agent_model,
    temperature=agent_temperature,
    top_p=agent_top_p,
    api_key=os.getenv("gemini")
)

# Tools list for the agent
tools = [search_wardrobe, research_trends]
_agent_vdb = WardrobeVectorDB()


def process_agent_response(response: str) -> str:
    """
    Post-process agent response to convert item IDs to markdown image links.
    
    Converts patterns like:
    - "sandals (6811062d-f4ab-452e-8700-c19c861a2b0e)"
    - "blue shirt (id:abc123)"
    - "shoes (id234567duws)"
    
    To markdown links pointing to image URLs:
    - "[sandals](http://localhost:8000/wardrobe/image/images/...jpg)"
    
    Args:
        response: Agent's text response
        
    Returns:
        Response with item references converted to image URL markdown links
    """
    
    vdb = _agent_vdb
    
    def get_image_link(item_name: str, item_id: str) -> str:
        """
        Try to fetch image URL for an item ID, return markdown link or fallback.
        """
        try:
            item = vdb.get_by_id(item_id)
            if item and item.get("payload"):
                img_path = item["payload"].get("img_path")
                if img_path:
                    image_url = f"http://localhost:8000/wardrobe/image/{img_path}"
                    return f"[{item_name}]({image_url})"
        except Exception as e:
            logger.warning(f"Could not fetch image path for item {item_id}: {e}")
        
        # Fallback: return original format
        return f"{item_name} ({item_id})"
    
    # Pattern 1: "word (uuid-style-id)"
    # Matches: "sandals (6811062d-f4ab-452e-8700-c19c861a2b0e)"
    pattern1 = r'(\w+(?:\s+\w+)*)\s+\(([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\)'
    response = re.sub(pattern1, lambda m: get_image_link(m.group(1), m.group(2)), response)
    
    # Pattern 2: "word (id: simple-id)"
    # Matches: "shirt (id: abc123)" or "shoes (id:abc123)"
    pattern2 = r'(\w+(?:\s+\w+)*)\s+\(id:\s*(\w+)\)'
    response = re.sub(pattern2, lambda m: get_image_link(m.group(1), m.group(2)), response)
    
    # Pattern 3: "word (idXXXXXX)" - short alphanumeric IDs
    # Matches: "sandals (id234567duws)"
    pattern3 = r'(\w+(?:\s+\w+)*)\s+\(id([a-z0-9]+)\)'
    response = re.sub(pattern3, lambda m: get_image_link(m.group(1), m.group(2)), response)
    
    return response


def run_agent(user_query: str, max_iterations: int = 10) -> Dict[str, Any]:
    """
    Run the truly agentic agent using ReAct pattern.
    Agent runs freely without restrictions.
    Returns agent's final response for post-processing.
    
    Args:
        user_query: Natural language query from user
        max_iterations: Max number of tool calls (default: 10)
        
    Returns:
        Dict with agent's final response and any tool data
    """
    try:
        # Create the agent with system prompt from config
        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=agent_system_prompt
        )
        
        # Invoke the agent with the user query
        config = {"recursion_limit": max_iterations}
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_query}]},
            config=config
        )
        
        # Extract agent's final response
        agent_final_message = ""
        
        if "messages" in result:
            messages = result["messages"]
            
            # Get the last AI message (agent's final response)
            for message in reversed(messages):
                try:
                    if hasattr(message, "type") and message.type == "ai":
                        content = message.content
                        
                        # Handle case where content is a list
                        if isinstance(content, list):
                            # Extract text parts from content blocks
                            text_parts = []
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text_parts.append(item.get("text", ""))
                                elif isinstance(item, str):
                                    text_parts.append(item)
                            agent_final_message = " ".join(text_parts)
                        else:
                            agent_final_message = content
                        
                        break
                except (AttributeError, KeyError):
                    continue
        
        # Return raw agent response for post-processing
        processed_response = process_agent_response(agent_final_message)
        
        return {
            "input": user_query,
            "agent_response": processed_response,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error in agent: {e}")
        return {
            "input": user_query,
            "status": "error",
            "error": str(e)
        }

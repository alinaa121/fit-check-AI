"""
Wardrobe AI Agent - True Agentic AI with Gemini LLM

This module defines a truly agentic agent where Gemini LLM decides which tools 
to call and when to stop. No hardcoded sequences - pure LLM reasoning and decision-making.
"""

import json
import os
from typing import Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from tools import search_wardrobe, generate_outfit_combinations
from config import agent_system_prompt, agent_model, agent_temperature, agent_top_p

load_dotenv()

# Initialize Gemini LLM
llm = ChatGoogleGenerativeAI(
    model=agent_model,
    temperature=agent_temperature,
    top_p=agent_top_p,
    api_key=os.getenv("gemini")
)

# Tools list for the agent
tools = [search_wardrobe, generate_outfit_combinations]


def run_agent(user_query: str, max_iterations: int = 6) -> Dict[str, Any]:
    """
    Run the agentic agent using ReAct pattern.
    LLM decides which tools to call and when to stop.
    
    Args:
        user_query: Natural language query from user
        max_iterations: Max number of tool calls (default: 6)
        
    Returns:
        Dict with:
            - combinations: List of outfit combinations with clothing IDs
            - count: Number of combinations generated
            - input: Original user query
            - status: Status of the agent execution
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
        
        # Extract structured output: get the most recent combinations result with IDs
        combinations_data = None
        agent_reasoning = ""
        
        if "messages" in result:
            messages = result["messages"]
            
            # Parse messages to find combinations and agent reasoning
            for message in reversed(messages):
                try:
                    if hasattr(message, "content") and isinstance(message.content, str):
                        # Try to parse as JSON (tool results)
                        try:
                            content = json.loads(message.content)
                            if isinstance(content, dict) and "combinations" in content:
                                combinations_data = content
                                continue
                        except (json.JSONDecodeError, ValueError):
                            pass
                        
                        # Plain text message from AI (agent's reasoning/conclusion)
                        if not agent_reasoning and message.type == "ai":
                            agent_reasoning = message.content
                except (AttributeError, KeyError):
                    continue
        
        # Build structured output
        structured_output = {
            "combinations": combinations_data.get("combinations", []) if combinations_data else [],
            "count": combinations_data.get("count", 0) if combinations_data else 0,
            "input": user_query,
            "status": "success"
        }
        
        return structured_output
        
    except Exception as e:
        return {
            "combinations": [],
            "count": 0,
            "input": user_query,
            "status": "error",
            "error": str(e)
        }

#clothing ingestion pipeline
import os
from dotenv import load_dotenv

load_dotenv()

# API Base URL - used to construct image URLs in API responses
# Development: http://localhost:8000 (default)
# Production: Set via environment variable API_BASE_URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

identify_clothing_model="gemini-3-flash-preview"
identify_clothing_function = {
    "name": "identify_clothing",
    "description": "Extracts detailed fashion metadata from a clothing item image. Returns structured JSON with comprehensive attributes.",
    "parameters": {
        "type": "object",
        "properties": {
            "raw_caption": {
                "type": "string",
                "description": "Rich, highly descriptive 1-2 sentence caption detailing texture, shade, design elements, hardware, and aesthetic."
            },
            "primary_category": {
                "type": "string",
                "enum": ["Top", "Bottom", "Outerwear", "Footwear", "Accessory", "Full-body", "Not-Clothing"],
                "description": "Main category of the clothing item."
            },
            "primary_color": {
                "type": "string",
                "enum": ["Black", "White", "Grey", "Navy", "Blue", "Red", "Green", "Yellow", "Orange", "Purple", "Pink", "Brown", "Beige", "Gold", "Silver", "Multicolor"],
                "description": "Dominant color of the item."
            },
            "secondary_colors": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Black", "White", "Grey", "Navy", "Blue", "Red", "Green", "Yellow", "Orange", "Purple", "Pink", "Brown", "Beige", "Gold", "Silver", "Multicolor"]
                },
                "description": "Up to 3 additional colors present in the item."
            },
            "pattern": {
                "type": "string",
                "enum": ["Solid", "Striped", "Check", "Floral", "Graphic", "Geometric", "Animal Print", "Houndstooth", "Camo", "Other"],
                "description": "Pattern type on the clothing."
            },
            "material": {
                "type": "string",
                "enum": ["Cotton", "Denim", "Leather", "Wool", "Linen", "Silk", "Synthetic", "Knit", "Velvet", "Suede", "Other"],
                "description": "Primary material or fabric."
            },
            "season": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Spring", "Summer", "Fall", "Winter", "All-Season"]
                },
                "description": "Up to 3 seasons suitable for wearing this item."
            },
            "occasion": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Casual", "Smart-Casual", "Business-Formal", "Athletic/Gym", "Lounge", "Night-Out", "Formal/Black-Tie"]
                },
                "description": "Up to 3 occasions this item is appropriate for."
            },
            "fit": {
                "type": "string",
                "enum": ["Slim", "Regular", "Oversized", "Tailored", "Cropped", "Other"],
                "description": "Fit style of the garment."
            },
            "style_vibe": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Minimalist", "Streetwear", "Vintage/Retro", "Preppy", "Grunge", "Techwear", "Bohemian", "Classic", "Other"]
                },
                "description": "Up to 3 style vibes or aesthetics."
            }
        },
        "required": ["raw_caption", "primary_category", "primary_color", "pattern", "material", "fit", "occasion", "style_vibe"]
    }
}

identify_clothing_prompt = """
You are an expert fashion stylist and cataloging AI. Your task is to analyze the provided image of a clothing item and extract detailed metadata.

You must return a single JSON object strictly adhering to the schema and Enums defined in the function. Do not include any markdown formatting, explanations, or text outside of the JSON object.

### INSTRUCTIONS:
1. raw_caption: Write a rich, highly descriptive 1-2 sentence caption detailing the item's texture, exact shade, unique design elements, hardware, and overall aesthetic.

2. For all other fields, you MUST choose the most accurate value from the provided ENUM lists defined in the function schema.

3. For array fields (secondary_colors, season, occasion, style_vibe), provide up to 3 most relevant values from their respective ENUMs.

4. Be precise with your selections:
   - primary_category: Choose from [Top, Bottom, Outerwear, Footwear, Accessory, Full-body, Not-Clothing]
   - primary_color and secondary_colors: Use exact color ENUMs
   - pattern: Select the most accurate pattern type
   - material: Identify the primary fabric
   - season: Consider the garment's weight and coverage
   - occasion: Think about where this would typically be worn
   - fit: Assess the silhouette and cut
   - style_vibe: Capture the aesthetic essence

5. If the image does not contain clothing or cannot be identified, set primary_category to 'Not-Clothing' and explain why in raw_caption.

Analyze the image carefully and return your structured metadata.
"""

extract_vdb_filters_model = "gemini-3-flash-preview" 
extract_vdb_filters_function = {
    "name": "extract_vdb_filters",
    "description": "Extracts structured filters from user's natural language query for searching wardrobe items. Returns only the filters mentioned in the query.",
    "parameters": {
        "type": "object",
        "properties": {
            "primary_category": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Top", "Bottom", "Outerwear", "Footwear", "Accessory", "Full-body"]
                },
                "description": "Main categories mentioned (e.g., 'shirts' -> ['Top'], 'pants and shoes' -> ['Bottom', 'Footwear'])"
            },
            "primary_color": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Black", "White", "Grey", "Navy", "Blue", "Red", "Green", "Yellow", "Orange", "Purple", "Pink", "Brown", "Beige", "Gold", "Silver", "Multicolor"]
                },
                "description": "Colors mentioned in the query (e.g., 'blue and black' -> ['Blue', 'Black'])"
            },
            "secondary_colors": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Black", "White", "Grey", "Navy", "Blue", "Red", "Green", "Yellow", "Orange", "Purple", "Pink", "Brown", "Beige", "Gold", "Silver", "Multicolor"]
                },
                "description": "Secondary or accent colors mentioned"
            },
            "pattern": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Solid", "Striped", "Check", "Floral", "Graphic", "Geometric", "Animal Print", "Houndstooth", "Camo", "Other"]
                },
                "description": "Patterns mentioned (e.g., 'striped or checked' -> ['Striped', 'Check'])"
            },
            "material": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Cotton", "Denim", "Leather", "Wool", "Linen", "Silk", "Synthetic", "Knit", "Velvet", "Suede", "Other"]
                },
                "description": "Materials or fabrics mentioned (e.g., 'cotton or denim' -> ['Cotton', 'Denim'])"
            },
            "season": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Spring", "Summer", "Fall", "Winter", "All-Season"]
                },
                "description": "Seasons mentioned or implied (e.g., 'summer clothes' -> ['Summer'])"
            },
            "weather": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Hot", "Warm", "Cool", "Cold", "Rainy", "Snowy", "Windy"]
                },
                "description": "Weather conditions mentioned (e.g., 'rainy day outfit' -> ['Rainy'])"
            },
            "occasion": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Casual", "Smart-Casual", "Business-Formal", "Athletic/Gym", "Lounge", "Night-Out", "Formal/Black-Tie"]
                },
                "description": "Occasions mentioned (e.g., 'work outfit' -> ['Business-Formal'], 'party dress' -> ['Night-Out'])"
            },
            "fit": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Slim", "Regular", "Oversized", "Tailored", "Cropped", "Other"]
                },
                "description": "Fit styles mentioned (e.g., 'slim fit or oversized' -> ['Slim', 'Oversized'])"
            },
            "style_vibe": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Minimalist", "Streetwear", "Vintage/Retro", "Preppy", "Grunge", "Techwear", "Bohemian", "Classic", "Other"]
                },
                "description": "Style aesthetics mentioned or implied (e.g., 'streetwear look' -> ['Streetwear'])"
            }
        },
        "required": []
    }
}

extract_vdb_filters_prompt = """
You are a fashion search query analyzer. Your task is to extract structured filters from the user's natural language query to search their wardrobe.

### INSTRUCTIONS:
1. Analyze the user's query carefully for ANY mentions of clothing attributes
2. Return ONLY the filters that are explicitly or very strongly implied in the query
3. Note that the user is FRUGAL. Hence, be VERY CONSERVATIVE in inferring filters. If the query is ambiguous, return fewer filters rather than risk including incorrect ones.
4. ALL filter values must be ARRAYS (lists), even for single values
5. If a filter is not mentioned, DO NOT include it in the response
6. Use the exact ENUM values provided in the function schema


Analyze the query and return the structured filters.
"""

# Rank and return clothes
rank_and_return_clothes_model = "gemini-3-flash-preview"
rank_and_return_clothes_function = {
    "name": "rank_and_return_clothes",
    "description": "Ranks clothing items by relevance to user query based on their descriptions. Returns ordered list of most relevant item IDs and a friendly caption.",
    "parameters": {
        "type": "object",
        "properties": {
            "ranked_item_ids": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "Ordered list of item IDs from most to least relevant to the query. Exclude items that are not relevant. Can be empty if no items match."
            },
            "caption": {
                "type": "string",
                "description": "A friendly, natural caption describing the results. Make it personalized, girly and warm."
            }
        },
        "required": ["ranked_item_ids", "caption"]
    }
}

rank_and_return_clothes_prompt = """
You are a personal wardrobe stylist AI. Rank clothing items by relevance to the user's query.

You'll receive a user query and a list of items (each with id and description). Analyze each item's description and rank by relevance, considering:
- Explicit attributes (color, type, style, material)
- Implicit intent (e.g., "beach day" → casual, light, summer)
- Occasion and outfit compatibility

Rules:
- Return ranked_item_ids ordered from most to least relevant
- EXCLUDE irrelevant items (fewer results is better than noise)
- If no good matches exist, return close alternatives but note this in caption
- If nothing relevant, return empty array with apologetic caption

Caption must be warm, friendly, personalized (e.g., "Here are your blue jeans!", "Found these cozy sweaters for winter!", "Sorry, couldn't find anything matching that").
"""

#vectordb
COLLECTION_NAME = "wardrobe_all_mini_lm"
EMBEDDING_MODEL="all-MiniLM-L6-v2"

# Agent system prompt for wardrobe AI
agent_system_prompt = """You are a friendly, encouraging personal fashion stylist and your best friend's style advisor rolled into one AI. Your vibe is warm, supportive, and genuinely excited about helping users create amazing outfits and feel confident about their wardrobe.

PERSONALITY & TONE:
- You're like a girl best friend giving style advice over coffee - warm, genuine, enthusiastic
- Always encouraging and body-positive
- Celebrate what they have, suggest thoughtful improvements
- Use natural, conversational language (not robotic)
- Be creative and fun with styling suggestions
- Understand that fashion is personal and subjective
- Keep responses SHORT and punchy - no long essays!

RESPONSE FORMAT:
⚠️ ALWAYS use this format for ANY wardrobe item: **item_name (uuid)** - wrap in markdown bold and include the full UUID
Examples: **blue jeans (a1b2c3d4-e5f6-4789-0abc-def123456789)**, **oversized blazer (xyz789...)**
- Write like you're texting a friend, not writing an article
- Use markdown naturally: **bold** for emphasis and ALL wardrobe items, *italic* for flavor
- Sprinkle in markdown where it feels right - no forced structure
- Line breaks for readability, not because you "need" a section header
- Use lists/headers ONLY when genuinely helpful (like 3+ items)
- Example: "I'd pair your **denim jacket (id3)** with those **white sneakers (id7)** for a chill vibe. Super clean and effortless!"

AVAILABLE TOOLS:
1. search_wardrobe: Find items matching user requirements (colors, styles, categories, etc.)
2. research_trends: Get current fashion trends for specific categories or styles

CRITICAL: ALWAYS REFERENCE ITEMS BY THEIR IDs
- When you mention any clothing item from the wardrobe, reference it by ID like this: "the blue shirt (id1)" or "your black jeans (id2)"
- This helps the frontend render and display the actual items
- Example: "I love pairing your oversized blazer (id5) with those slim black trousers (id8) for a polished look"
- If items are suggestions for shopping (not in wardrobe), mention them without IDs

YOUR DECISION LOGIC - BE TRULY AGENTIC:
Analyze the user's request and intelligently decide which tool(s) to call. 
If wardrobe does not have appropriate items, suggest shopping for new pieces.

GUIDELINES:
- You decide which tools to call based on the request - NOT a fixed workflow
- You can call 1 tool or multiple tools as needed
- STOP when you have a complete answer
- Be helpful: provide reasoning for your suggestions ("Why this works: ...")
- Ask clarifying questions if the request is vague ("Are you looking for casual or professional?")
- Always include styling tips and practical advice
- Make them feel excited about their wardrobe, not limited by it
- KEEP IT BRIEF - quality over quantity!
"""

# Agent LLM model
agent_model = "gemini-3-flash-preview"
agent_temperature = 0.7
agent_top_p = 0.9

# Outfit Feedback from LLM
outfit_feedback_model = "gemini-3-flash-preview"
outfit_feedback_function = {
    "name": "generate_outfit_feedback",
    "description": "Generates personalized, constructive feedback on a user's outfit composition.",
    "parameters": {
        "type": "object",
        "properties": {
            "feedback": {
                "type": "string",
                "description": "Detailed, friendly, and constructive outfit feedback with styling suggestions."
            }
        },
        "required": ["feedback"]
    }
}

outfit_feedback_prompt = """You are a warm, encouraging personal fashion stylist providing real-time feedback on an outfit composition. Your tone is like a best friend giving genuine style advice.

OUTFIT ANALYSIS TASK:
You will receive:
1. A list of clothing items the user has composed in their outfit (with descriptions, colors, categories)
2. The user's optional context about the occasion or purpose of the outfit

FEEDBACK GUIDELINES:
- Be encouraging and positive while offering constructive suggestions
- Analyze how the pieces work together (color harmony, proportion balance, style cohesion)
- Consider the occasion/context provided by the user
- Suggest improvements if there are clashing colors, mismatched styles, or proportion issues
- Point out what works well about the combination
- Offer specific styling tips or alternatives if needed
- Keep the tone conversational and friendly, like texting a friend
- Be brief but insightful (3-5 sentences typically)
- If the outfit seems incomplete (e.g., missing shoes or outerwear for the occasion), mention it naturally

TONE:
- Warm and supportive, never judgmental
- Genuine and personalized
- Use natural language, not robotic
- Celebrate their choices while being honest about styling

Return only the feedback text - no formatting required, just warm, genuine advice."""

#s3
key="images"
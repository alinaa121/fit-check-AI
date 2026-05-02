#clothing ingestion pipeline
identify_clothing_model="gemini-3-flash-preview"

#clothing ingestion pipeline
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

#vectordb
COLLECTION_NAME = "wardrobe_all_mini_lm"
EMBEDDING_MODEL="all-MiniLM-L6-v2"

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

#s3
key="images"
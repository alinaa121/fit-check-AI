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

#s3
key="images"
#clothing ingestion pipeline
identify_clothing_model="gemini-3-flash-preview"

#clothing ingestion pipeline
identify_clothing_function = {
    "name": "identify_clothing",
    "description": "Identifies clothing type and provides a description. Returns 'not clothing' if not clothing or cannot identify.",
    "parameters": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["top", "skirt", "dress", "pants", "shorts", "jacket", "not_clothing"],
                "description": "Type of clothing identified or 'not_clothing'."
            },
            "description": {
                "type": "string",
                "description": "Description of the clothing item or reason for rejection."
            }
        },
        "required": ["type", "description"]
    }
}

identify_clothing_prompt = """
You are an expert fashion descriptor. 
Your output is critical for searching and comparing fashion items. 
Identify the clothing item in this image and return structured output.
You must try to atleast cover the following attributes in your description:
- Type of clothing (e.g., top, skirt, dress, pants, shorts, jacket)
- Color, pattern, and material if identifiable
- Style details (e.g., long-sleeve, sleeveless, A-line, etc.) if identifiable
- Any unique features (e.g., ruffles, buttons, etc.) if identifiable
- Occasion or usage context if identifiable
- Overall style or vibe (e.g., casual, formal, bohemian, etc.) if identifiable
If not clothing or cannot identify, return type: 'not_clothing' and a description why.
"""

#vectordb
COLLECTION_NAME = "wardrobe_all_mini_lm"
EMBEDDING_MODEL="all-MiniLM-L6-v2"
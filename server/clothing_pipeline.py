from gemini import GeminiClient
from google.genai import types
from config import *
import logging
import mimetypes
import uuid
from typing import Optional, Dict
from s3_utils import upload_image_from_bytes

logging.basicConfig(
        format='%(asctime)s %(filename)s %(levelname)s: %(message)s',
        level=logging.INFO) 

class ClothingPipeline:
    def __init__(self) -> None:
        """
        Initializes the ClothingPipeline with a GeminiClient instance.
        """
        self.gemini_client = GeminiClient()
    
    def identify_clothing(self, image_bytes: bytes, mime_type: str) -> Optional[Dict]:
        """
        Identifies the clothing metadata from an image using Gemini.

        Args:
            image_bytes (bytes): The image data in bytes.
            mime_type (str): The MIME type of the image (e.g., 'image/jpeg').

        Returns:
            Optional[Dict]: Dictionary with all clothing metadata fields if successful, else None.
        """
        tools = types.Tool(function_declarations=[identify_clothing_function])
        response = self.gemini_client.call_gemini(
            content_parts = [
                types.Part(text=identify_clothing_prompt),
                types.Part(inline_data=types.Blob(data=image_bytes, mime_type=mime_type))
            ],
            model=identify_clothing_model,
            config = types.GenerateContentConfig(
                tools=[tools],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode='ANY'
                    )
                )
            )
        )
    
        if response and response.candidates[0].content.parts[0].function_call:
            function_call = response.candidates[0].content.parts[0].function_call
            logging.info(f"Structured output: {function_call.args}")
            # Return all fields from the new schema
            return dict(function_call.args)
        else:
            logging.error("No function call in response or unexpected response format.")
            return None

    def load_image(self, image_path: str) -> bytes:
        """
        Loads an image from the given file path as bytes.

        Args:
            image_path (str): Path to the image file.

        Returns:
            bytes: The image data in bytes.
        """
        with open(image_path, 'rb') as img_file:
            return img_file.read()
    
    
    def detect_mime_from_bytes(self, data: bytes) -> Optional[str]:
        """
        Detects MIME type from image bytes using magic bytes (file signatures).
        Only allows JPEG and PNG.

        Args:
            data (bytes): The image data in bytes.

        Returns:
            Optional[str]: The detected MIME type if allowed, else None.
        """
        if len(data) < 12:
            logging.error("Image data too short to detect MIME type")
            return None
        
        # Check JPEG signature
        if data.startswith(b'\xff\xd8\xff'):
            logging.info("Detected MIME type: image/jpeg")
            return 'image/jpeg'
        
        # Check PNG signature
        elif data.startswith(b'\x89PNG\r\n\x1a\n'):
            logging.info("Detected MIME type: image/png")
            return 'image/png'
        
        else:
            logging.error(f"Unsupported or unrecognized image format. Only JPEG and PNG are allowed.")
            return None
    
    def identify_and_upload(self, image_bytes: bytes, mime_type: Optional[str] = None, s3_key: Optional[str] = None, vector_db = None) -> Optional[Dict]:
        """
        Identifies clothing from bytes, uploads to S3, and adds to VectorDB if it's valid clothing (not 'Not-Clothing').

        Args:
            image_bytes (bytes): The image data in bytes.
            mime_type (Optional[str]): The MIME type of the image. If None, auto-detects from bytes.
            s3_key (Optional[str]): The S3 key (path) where the image should be stored. 
                                    If None, auto-generates using config.key prefix and UUID.
            vector_db (Optional[WardrobeVectorDB]): VectorDB instance to store metadata. If None, skips VectorDB upload.

        Returns:
            Optional[Dict]: Dictionary with all metadata fields plus 's3_key', 'uploaded', and 'point_id' if successful, else None.
        """
        # Auto-detect MIME type if not provided
        if mime_type is None:
            logging.info("MIME type not provided, auto-detecting from bytes")
            mime_type = self.detect_mime_from_bytes(image_bytes)
            if mime_type is None:
                logging.error("Failed to detect valid MIME type from bytes")
                return None
        
        # Auto-generate S3 key if not provided
        if s3_key is None:
            extension = 'jpg' if 'jpeg' in mime_type else mime_type.split('/')[-1]
            s3_key = f"{key}/{uuid.uuid4()}.{extension}"
            logging.info(f"Auto-generated S3 key: {s3_key}")
        
        logging.info(f"Identifying clothing from bytes with mime_type: {mime_type}")
        
        # Identify the clothing
        result = self.identify_clothing(image_bytes, mime_type)
        
        if result is None:
            logging.error("Failed to identify clothing")
            return None
        
        primary_category = result.get('primary_category', '').lower()
        
        # Check if it's valid clothing (not 'not-clothing')
        if primary_category in ['Not-Clothing', '']:
            logging.warning(f"Image is not clothing (category: {primary_category}). Skipping upload.")
            result_copy = result.copy()
            result_copy.update({
                "uploaded": False,
                "reason": "not_clothing"
            })
            return result_copy
        
        # Upload to S3
        try:
            logging.info(f"Uploading valid clothing (category: {primary_category}) to S3 at key: {s3_key}")
            upload_image_from_bytes(image_bytes, bucket=None, key=s3_key, content_type=mime_type)
            logging.info(f"Successfully uploaded to S3: {s3_key}")
            
            result_copy = result.copy()
            result_copy.update({
                "s3_key": s3_key,
                "uploaded": True
            })
            
            # Add to VectorDB if instance provided
            if vector_db is not None:
                try:
                    # Extract metadata (exclude upload-specific fields)
                    metadata = {k: v for k, v in result.items() if k not in ["uploaded", "s3_key"]}
                    point_id = vector_db.add(img_path=s3_key, metadata=metadata)
                    logging.info(f"Added to VectorDB with point ID: {point_id}")
                    result_copy["point_id"] = point_id
                    result_copy["vectordb_added"] = True
                except Exception as e:
                    logging.error(f"Failed to add to VectorDB: {e}")
                    result_copy["vectordb_added"] = False
                    result_copy["vectordb_error"] = str(e)
            
            return result_copy
        except Exception as e:
            logging.error(f"Failed to upload to S3: {e}")
            result_copy = result.copy()
            result_copy.update({
                "uploaded": False,
                "reason": f"upload_error: {str(e)}"
            })
            return result_copy
    
    def extract_filters_from_query(self, query: str) -> Optional[Dict]:
        """
        Extracts structured filters from a natural language query using Gemini.
        Returns a dictionary with filter keys and list values ready for vdb.search().

        Args:
            query (str): Natural language query (e.g., "show me blue summer shirts")

        Returns:
            Optional[Dict]: Dictionary with filter arrays if successful, else None.
            Example: {
                "primary_category": ["Top"],
                "primary_color": ["Blue"],
                "season": ["Summer"]
            }
        """
        logging.info(f"Extracting filters from query: '{query}'")
        
        try:
            tools = types.Tool(function_declarations=[extract_vdb_filters_function])
            response = self.gemini_client.call_gemini(
                content_parts = [
                    types.Part(text=extract_vdb_filters_prompt),
                    types.Part(text=f"\n\nUser Query: {query}")
                ],
                model=extract_vdb_filters_model, 
                config = types.GenerateContentConfig(
                    tools=[tools],
                    tool_config=types.ToolConfig(
                        function_calling_config=types.FunctionCallingConfig(
                            mode='ANY'
                        )
                    )
                )
            )
        
            if response and response.candidates[0].content.parts[0].function_call:
                function_call = response.candidates[0].content.parts[0].function_call
                filters = dict(function_call.args)
                logging.info(f"Extracted filters: {filters}")
                return filters if filters else {}
            else:
                logging.warning("No function call in response, returning empty filters")
                return {}
                
        except Exception as e:
            logging.error(f"Error extracting filters from query: {e}")
            return None
        
    def rank_and_filter_results(self, query: str, items: list) -> Optional[Dict]:
        """
        Ranks and filters clothing items by relevance to user query using AI.

        Args:
            query (str): User's search query or intent (e.g., "blue summer shirts", "outfit for beach day")
            items (list): List of dictionaries, each with 'id' and 'description' fields

        Returns:
            Optional[Dict]: {
                "ranked_item_ids": [...],  # Ordered list of most relevant IDs (can be empty)
                "caption": "..."           # Friendly message about results
            }
            Returns None if error occurs.
        """
        if not items:
            logging.warning("No items provided for ranking")
            return {
                "ranked_item_ids": [],
                "caption": "No items to rank."
            }
        
        logging.info(f"Ranking {len(items)} items for query: '{query}'")
        
        # Build the items text for the prompt
        items_text = "\n".join([
            f"- ID: {item.get('id', 'unknown')}, Description: {item.get('description', 'No description')}"
            for item in items
        ])
        
        # Construct the full prompt
        full_prompt = f"{rank_and_return_clothes_prompt}\n\nUser Query: {query}\n\nItems:\n{items_text}"
        
        try:
            tools = types.Tool(function_declarations=[rank_and_return_clothes_function])
            response = self.gemini_client.call_gemini(
                content_parts=[types.Part(text=full_prompt)],
                model=rank_and_return_clothes_model,
                config=types.GenerateContentConfig(
                    tools=[tools],
                    tool_config=types.ToolConfig(
                        function_calling_config=types.FunctionCallingConfig(mode='ANY')
                    )
                )
            )
            
            if response and response.candidates[0].content.parts[0].function_call:
                function_call = response.candidates[0].content.parts[0].function_call
                result = {
                    "ranked_item_ids": list(function_call.args.get('ranked_item_ids', [])),
                    "caption": function_call.args.get('caption', 'Here are your results.')
                }
                logging.info(f"Ranked {len(result['ranked_item_ids'])} items. Caption: {result['caption']}")
                return result
            else:
                logging.error("No function call in response")
                return None
                
        except Exception as e:
            logging.error(f"Error ranking items: {e}")
            return None

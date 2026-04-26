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
    
    def get_mime_type(self, image_path: str) -> Optional[str]:
        """
        Determines the MIME type of the image. Only allows JPEG and PNG.

        Args:
            image_path (str): Path to the image file.

        Returns:
            Optional[str]: The MIME type if allowed, else None.
        """
        mime_type, _ = mimetypes.guess_type(image_path)
        allowed_types = ["image/jpeg", "image/jpg", "image/png"]
        if mime_type is None:
            # Default to jpeg if unknown
            mime_type = "image/jpeg"
        if mime_type.lower() not in allowed_types:
            logging.error(f"Unsupported image type: {mime_type}. Only JPEG and PNG are allowed.")
            return None
        logging.info(f"Determined MIME type: {mime_type} for image: {image_path}")
        return mime_type
    
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
        
    def process_image(self, image_path: str) -> Optional[Dict]:
        """
        Processes an image: loads it, checks MIME type, and identifies clothing.

        Args:
            image_path (str): Path to the image file.

        Returns:
            Optional[Dict]: Dictionary with all clothing metadata if successful, else None.
        """
        image_bytes = self.load_image(image_path)
        mime_type = self.get_mime_type(image_path)
        if mime_type is None:
            return None
        result = self.identify_clothing(image_bytes, mime_type)
        return result
    
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
    
    
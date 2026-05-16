from fastapi import FastAPI, HTTPException, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import logging
import uuid
import io
from PIL import Image
from google.genai import types
from datetime import datetime
import json

from vectordb import WardrobeVectorDB
from s3_utils import *
from clothing_pipeline import ClothingPipeline
from agent import *
from gemini import GeminiClient
from config import (
    API_BASE_URL,
    outfit_feedback_model,
    outfit_feedback_function,
    outfit_feedback_prompt
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Wardrobe AI API",
    description="API for managing and searching wardrobe clothing items",
    version="1.0.0"
)

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize VectorDB
vdb = WardrobeVectorDB()

# Initialize Clothing Pipeline
pipeline = ClothingPipeline()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Wardrobe AI API is running"}


@app.get("/wardrobe/image/{image_key:path}")
async def get_image(image_key: str):
    """
    Proxy endpoint to serve images from S3.
    This bypasses Block Public Access restrictions by fetching images server-side.
    
    Args:
        image_key: The S3 key path (e.g., 'images/abc-123.jpg')
        
    Returns:
        StreamingResponse with the image content
    """
    try:
        import io
        from s3_utils import download_file_to_memory
        
        logger.info(f"Fetching image from S3: {image_key}")
        
        # Download image from S3 into memory
        image_bytes = download_file_to_memory(
            bucket=None,  # Uses BUCKET_NAME from env
            key=image_key
        )
        
        # Determine content type from file extension
        content_type = "image/jpeg"
        if image_key.lower().endswith('.png'):
            content_type = "image/png"
        elif image_key.lower().endswith('.webp'):
            content_type = "image/webp"
        
        # Return image as streaming response
        return StreamingResponse(
            io.BytesIO(image_bytes),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching image {image_key}: {e}")
        raise HTTPException(status_code=404, detail=f"Image not found: {str(e)}")


@app.get("/wardrobe/items", response_model=List[Dict[str, Any]])
async def get_all_items(
    limit: int = 100,
    url_expiration: int = 3600
):
    """
    Get all wardrobe items with their metadata and presigned image URLs.
    
    Args:
        limit: Maximum number of items to return (default: 100)
        url_expiration: Presigned URL expiration in seconds (default: 3600 = 1 hour)
        
    Returns:
        List of items with metadata and image URLs for frontend rendering
    """
    try:
        logger.info(f"Fetching wardrobe items with limit={limit}")
        
        # Get all items from vectordb
        results, next_offset = vdb.list_all(limit=limit)
        
        items = []
        for point in results:
            payload = point.payload
            img_path = payload.get("img_path")
            
            # Generate proxy URLs using API_BASE_URL from config
            image_url = None
            if img_path:
                image_url = f"{API_BASE_URL}/wardrobe/image/{img_path}"
            
            # Construct item response
            item = {
                "id": point.id,
                "image_url": image_url,
                "img_path": img_path,
                "raw_caption": payload.get("raw_caption"),
                "primary_category": payload.get("primary_category"),
                "sub_category": payload.get("sub_category"),
                "primary_color": payload.get("primary_color"),
                "secondary_colors": payload.get("secondary_colors", []),
                "pattern": payload.get("pattern"),
                "material": payload.get("material"),
                "season": payload.get("season", []),
                "weather": payload.get("weather", []),
                "occasion": payload.get("occasion", []),
                "fit": payload.get("fit"),
                "style_vibe": payload.get("style_vibe", []),
                "created_at": payload.get("created_at"),
                "modified_at": payload.get("modified_at"),
            }
            items.append(item)
        
        logger.info(f"Returning {len(items)} wardrobe items")
        return items
        
    except Exception as e:
        logger.error(f"Error fetching wardrobe items: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch wardrobe items: {str(e)}")


@app.get("/wardrobe/search", response_model=Dict[str, Any])
async def search_wardrobe(query: str):
    """
    Search wardrobe with AI-powered query understanding and ranking.
    
    This endpoint:
    1. Extracts structured filters from natural language query
    2. Searches the wardrobe with semantic and metadata filters
    3. Ranks results by relevance using AI
    4. Returns ranked items with metadata and image URLs
    
    Args:
        query (str): Natural language search query (e.g., "blue summer shirts", "casual weekend outfits")
        
    Returns:
        Dict with:
            - caption: Friendly message describing the results
            - items: List of ranked items with full metadata and image URLs
            - count: Number of items returned
    """
    try:
        logger.info(f"Searching wardrobe for query: '{query}'")
        
        # Step 1: Extract structured filters from natural language query
        filters = pipeline.extract_filters_from_query(query)
        logger.info(f"Extracted filters: {filters}")
        
        # Step 2: Count items matching filters
        count = vdb.count_items(filters)
        logger.info(f"Found {count} items matching filters")
        
        # Step 3: Search with filters if found items, otherwise search all
        search_items = []
        if count > 1:
            search_items = vdb.search(query, limit=10, filters=filters)
        else:
            search_items = vdb.search(query, limit=10)
        
        # Convert to format expected by ranking function
        items_for_ranking = [
            {"id": item['id'], "description": item['raw_caption']} 
            for item in search_items
        ]
        logger.info(f"Prepared {len(items_for_ranking)} items for ranking")
        
        # Step 4: Rank items by relevance using AI
        ranked = pipeline.rank_and_filter_results(query, items_for_ranking)
        
        if ranked is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to rank search results"
            )
        
        # Step 5: Fetch full metadata for ranked items
        ranked_ids = ranked.get('ranked_item_ids', [])
        caption = ranked.get('caption', 'Here are your results.')
        
        items_with_metadata = vdb.search_by_points(ranked_ids)
        logger.info(f"Retrieved full metadata for {len(items_with_metadata)} ranked items")
        
        # Step 6: Construct response with image URLs using API_BASE_URL
        result_urls = []
        for item in items_with_metadata:
            img_path = item.get('img_path')
            image_url = f"{API_BASE_URL}/wardrobe/image/{img_path}" if img_path else None
            
            result_urls.append(image_url)
        
        logger.info(f"Search completed: {len(result_urls)} items ranked")
        
        return {
            "query": query,
            "caption": caption,
            "items": result_urls
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during wardrobe search: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/wardrobe/upload", response_model=Dict[str, Any])
async def upload_item(
    file: UploadFile = File(...)
):
    """
    Upload a clothing item image, generate AI caption, upload to S3, and add to vector database.
    
    Args:
        file: The image file to upload (JPEG or PNG)
        
    Returns:
        Dict with metadata, S3 key, and upload status
    """
    try:
        logger.info(f"Receiving file upload: {file.filename}")
        
        # Read file as bytes
        image_bytes = await file.read()
        logger.info(f"Read {len(image_bytes)} bytes from uploaded file")
        
        # Detect MIME type from bytes
        mime_type = pipeline.detect_mime_from_bytes(image_bytes)
        if mime_type is None:
            raise HTTPException(
                status_code=400, 
                detail="Invalid image format. Only JPEG and PNG are supported."
            )
        
        # Generate S3 key with UUID in images/ folder
        extension = 'jpg' if 'jpeg' in mime_type else 'png'
        s3_key = f"images/{uuid.uuid4()}.{extension}"
        logger.info(f"Generated S3 key: {s3_key}")
        
        # Process image: identify clothing, upload to S3, and add to VectorDB
        result = pipeline.identify_and_upload(
            image_bytes=image_bytes,
            mime_type=mime_type,
            s3_key=s3_key,
            vector_db=vdb
        )
        
        if result is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to process image with AI"
            )
        
        # Check if it was uploaded (not "Not-Clothing")
        if not result.get("uploaded", False):
            reason = result.get("reason", "unknown")
            logger.warning(f"Image not uploaded. Reason: {reason}")
            return {
                "status": "rejected",
                "reason": reason,
                "message": "Image is not clothing and was not uploaded",
                "metadata": result
            }
        
        # Check if VectorDB upload succeeded
        if not result.get("vectordb_added", False):
            error_msg = result.get("vectordb_error", "unknown error")
            logger.error(f"VectorDB upload failed: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Image uploaded to S3 but failed to add to database: {error_msg}"
            )
        
        point_id = result.get("point_id")
        
        # Generate presigned URL for immediate display
        try:
            image_url = generate_presigned_url(
                bucket=None,
                key=s3_key,
                expiration=3600
            )
        except Exception as e:
            logger.warning(f"Failed to generate presigned URL: {e}")
            image_url = None
        
        # Extract clean metadata (remove internal fields)
        metadata = {k: v for k, v in result.items() if k not in ["uploaded", "s3_key", "point_id", "vectordb_added", "vectordb_error"]}
        
        # Return success response
        return {
            "status": "success",
            "message": "Image processed, uploaded, and cataloged successfully",
            "id": point_id,
            "s3_key": s3_key,
            "image_url": image_url,
            "metadata": metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.delete("/wardrobe/item/{item_id}", response_model=Dict[str, Any])
async def delete_item(item_id: str):
    """
    Delete a wardrobe item by its point ID.
    
    This will:
    1. Retrieve the item from VectorDB to get the S3 image path
    2. Delete the image from S3
    3. Delete the point from VectorDB
    
    Args:
        item_id: The point ID (UUID) of the item to delete
        
    Returns:
        Dict with deletion status and details
    """
    try:
        logger.info(f"Deleting item with ID: {item_id}")
        
        # Step 1: Get the item from VectorDB to retrieve img_path
        item = vdb.get_by_id(item_id)
        
        if item is None:
            logger.warning(f"Item {item_id} not found in database")
            raise HTTPException(
                status_code=404,
                detail=f"Item with ID '{item_id}' not found"
            )
        
        img_path = item.get("payload", {}).get("img_path")
        
        if not img_path:
            logger.warning(f"Item {item_id} has no img_path in payload")
            # Still proceed with deletion from VectorDB
        
        # Step 2: Delete from S3 if img_path exists
        s3_deleted = False
        if img_path:
            try:
                delete_object(bucket=None, key=img_path)
                logger.info(f"Deleted S3 object: {img_path}")
                s3_deleted = True
            except Exception as e:
                logger.error(f"Failed to delete S3 object {img_path}: {e}")
                # Continue with VectorDB deletion even if S3 fails
        
        # Step 3: Delete from VectorDB
        try:
            vdb.delete_by_point(item_id)
            logger.info(f"Deleted point {item_id} from VectorDB")
        except Exception as e:
            logger.error(f"Failed to delete point {item_id} from VectorDB: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete item from database: {str(e)}"
            )
        
        return {
            "status": "success",
            "message": f"Item '{item_id}' deleted successfully",
            "id": item_id,
            "img_path": img_path,
            "s3_deleted": s3_deleted,
            "vectordb_deleted": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during deletion: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Delete operation failed: {str(e)}"
        )


@app.patch("/wardrobe/item/{item_id}", response_model=Dict[str, Any])
async def update_item(
    item_id: str,
    field_name: str = Body(...),
    new_value: Any = Body(...)
):
    """
    Update a specific field of a wardrobe item.
    
    If updating 'raw_caption', the item will be re-embedded for better search results.
    For other fields, only the metadata is updated.
    
    Args:
        item_id: The point ID (UUID) of the item to update
        request: UpdateItemRequest with field_name and new_value
        
    Returns:
        Dict with update status and updated item details
    """
    try:
        logger.info(f"Updating item {item_id}: {field_name} = {new_value}")
        
        # Validate field name
        valid_fields = [
            "raw_caption", "primary_category", "sub_category", "primary_color",
            "secondary_colors", "pattern", "material", "season", "weather",
            "occasion", "fit", "style_vibe"
        ]
        
        if field_name not in valid_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid field name. Valid fields: {', '.join(valid_fields)}"
            )
        
        # Perform the update
        success = vdb.update_by_point(item_id, field_name, new_value)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Item with ID '{item_id}' not found"
            )
        
        # Retrieve updated item
        updated_item = vdb.get_by_id(item_id)
        
        return {
            "status": "success",
            "message": f"Field '{field_name}' updated successfully",
            "id": item_id,
            "field_updated": field_name,
            "new_value": new_value,
            "re_embedded": field_name == "raw_caption",
            "updated_payload": updated_item.get("payload", {}) if updated_item else {}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during update: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Update operation failed: {str(e)}"
        )


@app.post("/wardrobe/outfit-feedback", response_model=Dict[str, Any])
async def get_outfit_feedback(
    item_ids: List[str] = Body(...),
    context: Optional[str] = Body(None)
):
    """
    Generate LLM-based feedback on a user's outfit composition.
    
    This endpoint:
    1. Retrieves full metadata for outfit items from VectorDB
    2. Constructs a system prompt with item descriptions and user context
    3. Calls Gemini LLM to generate personalized outfit feedback
    4. Returns the feedback text
    
    Args:
        request (OutfitFeedbackRequest):
            - item_ids: List of clothing item IDs in the outfit
            - context: Optional user-provided context (e.g., occasion, event)
    
    Returns:
        Dict with:
            - feedback: The LLM-generated feedback text
            - items_analyzed: Number of items analyzed
            - context_provided: Whether user provided context
    """
    try:
        logger.info(f"Generating outfit feedback for {len(item_ids)} items")
        
        if not item_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one item must be provided for feedback"
            )
        
        # Step 1: Retrieve full metadata for all items using VectorDB search_by_points
        logger.info(f"Fetching metadata for items: {item_ids}")
        outfit_items = vdb.search_by_points(item_ids)
        
        if not outfit_items:
            raise HTTPException(
                status_code=404,
                detail="Could not find metadata for the provided item IDs"
            )
        
        logger.info(f"Retrieved metadata for {len(outfit_items)} items")
        
        # Step 2: Construct item descriptions for the prompt
        item_descriptions = []
        for item in outfit_items:
            description = f"- {item.get('primary_category', 'Item')}: {item.get('raw_caption', 'No description')} (Color: {item.get('primary_color', 'Unknown')}, Pattern: {item.get('pattern', 'Unknown')})"
            item_descriptions.append(description)
        
        items_text = "\n".join(item_descriptions)
        
        # Step 3: Build the user message with outfit details and context
        user_message = f"""Here is the outfit composition:
{items_text}

"""
        if context:
            user_message += f"User context: {context}\n"
        
        user_message += "\nPlease provide feedback on this outfit."
        
        logger.info(f"Prepared outfit message with {len(outfit_items)} items and context: {bool(context)}")
        
        # Step 4: Call Gemini LLM with outfit feedback function
        gemini = GeminiClient()
        
        # Use function directly from config (matching pattern from clothing_pipeline.py)
        tools = types.Tool(function_declarations=[outfit_feedback_function])
        
        config = types.GenerateContentConfig(
            tools=[tools],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode='ANY'
                )
            ),
            system_instruction=outfit_feedback_prompt
        )
        
        # Prepare content parts for Gemini
        content_parts = [types.Part(text=user_message)]
        
        # Call Gemini
        logger.info("Calling Gemini LLM for outfit feedback")
        response = gemini.call_gemini(
            content_parts=content_parts,
            model=outfit_feedback_model,
            config=config
        )
        
        if response is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate feedback from LLM"
            )
        
        # Step 5: Extract feedback from response (matching pattern from clothing_pipeline.py)
        feedback_text = None
        
        try:
            # Access function call from response structure
            if response and response.candidates[0].content.parts[0].function_call:
                function_call = response.candidates[0].content.parts[0].function_call
                logger.info(f"Function call response: {function_call.args}")
                feedback_text = function_call.args.get('feedback') or str(function_call.args)
            else:
                logger.warning("No function call in response or unexpected response format")
        except (AttributeError, IndexError, KeyError) as e:
            logger.warning(f"Could not extract from structured format, trying text fallback: {e}")
            # Try text fallback
            if hasattr(response, 'text'):
                feedback_text = response.text
        
        if not feedback_text:
            logger.warning("Could not extract feedback from LLM response")
            feedback_text = "Unable to generate feedback at this time. Please try again."
        
        logger.info(f"Successfully generated outfit feedback ({len(str(feedback_text))} characters)")
        
        return {
            "feedback": feedback_text,
            "items_analyzed": len(outfit_items),
            "context_provided": bool(context)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating outfit feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate outfit feedback: {str(e)}"
        )


@app.post("/wardrobe/outfit-save", response_model=Dict[str, Any])
async def save_outfit(
    item_ids: List[str] = Body(...),
    name: Optional[str] = Body(None)
):
    """
    Save an outfit composition to S3.
    
    This endpoint:
    1. Validates that at least one item is provided
    2. Creates a JSON file with outfit data (item IDs, date, optional name)
    3. Uploads to S3 in the outfits/ folder with a unique ID
    4. Returns the outfit ID and details
    
    Args:
        request (SaveOutfitRequest):
            - item_ids: List of clothing item IDs in the outfit
            - name: Optional outfit name
    
    Returns:
        Dict with:
            - outfit_id: Unique identifier for the saved outfit
            - s3_key: S3 path where outfit was saved
            - items_count: Number of items in outfit
            - saved_at: ISO timestamp of when outfit was saved
    """
    try:
        logger.info(f"Saving outfit with {len(item_ids)} items")
        
        if not item_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one item must be provided to save an outfit"
            )
        
        # Step 1: Generate outfit ID and timestamp
        outfit_id = str(uuid.uuid4())
        saved_at = datetime.utcnow().isoformat() + "Z"
        
        # Step 2: Create outfit data structure
        outfit_data = {
            "outfit_id": outfit_id,
            "name": name or f"Outfit {saved_at.split('T')[0]}",
            "item_ids": item_ids,
            "saved_at": saved_at,
            "items_count": len(item_ids)
        }
        
        # Step 3: Convert to JSON
        outfit_json = json.dumps(outfit_data, indent=2)
        outfit_bytes = outfit_json.encode('utf-8')
        
        # Step 4: Generate S3 key with outfit ID
        s3_key = f"outfits/{outfit_id}.json"
        
        logger.info(f"Uploading outfit to S3: {s3_key}")
        
        # Step 5: Upload to S3 using upload_fileobj
        outfit_file = io.BytesIO(outfit_bytes)
        upload_fileobj(
            outfit_file,
            bucket=None,  # Uses BUCKET_NAME from env
            key=s3_key,
            content_type="application/json"
        )
        
        logger.info(f"Successfully saved outfit {outfit_id} to S3")
        
        return {
            "status": "success",
            "message": "Outfit saved successfully",
            "outfit_id": outfit_id,
            "s3_key": s3_key,
            "items_count": len(item_ids),
            "saved_at": saved_at,
            "name": outfit_data["name"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving outfit: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save outfit: {str(e)}"
        )


@app.get("/wardrobe/outfits", response_model=Dict[str, Any])
async def get_outfits():
    """
    Retrieve all saved outfits from S3.
    
    This endpoint:
    1. Lists all JSON files in the outfits/ folder
    2. For each outfit, reads the JSON and extracts item_ids and name
    3. Retrieves full item metadata from VectorDB using the item_ids
    4. Generates image URLs for each item
    5. Returns all outfits with their names and items
    
    Returns:
        Dict with:
            - outfits: List of saved outfits, each containing:
                - outfit_id: Unique identifier
                - name: Outfit name
                - items: List of items with id, image_url, and metadata
                - saved_at: When the outfit was saved
                - items_count: Number of items in outfit
            - count: Total number of outfits
            - status: "success"
    """
    try:
        logger.info("Fetching all saved outfits from S3")
        
        # Step 1: List all outfit JSON files in outfits/ folder
        outfit_files = list_objects(bucket=None, prefix="outfits/")
        logger.info(f"Found {len(outfit_files)} outfit files")
        
        if not outfit_files:
            logger.info("No saved outfits found")
            return {
                "outfits": [],
                "count": 0,
                "status": "success"
            }
        
        outfits = []
        
        # Step 2: Process each outfit file
        for outfit_file in outfit_files:
            try:
                # Read the JSON file from S3
                outfit_bytes = download_file_to_memory(bucket=None, key=outfit_file)
                outfit_json = json.loads(outfit_bytes.decode('utf-8'))
                
                logger.info(f"Processing outfit: {outfit_json.get('outfit_id')}")
                
                # Step 3: Extract item_ids and name
                item_ids = outfit_json.get("item_ids", [])
                outfit_name = outfit_json.get("name", "Unnamed Outfit")
                outfit_id = outfit_json.get("outfit_id")
                saved_at = outfit_json.get("saved_at")
                
                if not item_ids:
                    logger.warning(f"Outfit {outfit_id} has no items, skipping")
                    continue
                
                # Step 4: Retrieve full metadata for all items
                outfit_items = vdb.search_by_points(item_ids)
                
                if not outfit_items:
                    logger.warning(f"Could not retrieve metadata for outfit {outfit_id}")
                    continue
                
                # Step 5: Construct items with image URLs
                items_with_urls = []
                for item in outfit_items:
                    img_path = item.get("img_path")
                    image_url = f"{API_BASE_URL}/wardrobe/image/{img_path}" if img_path else None
                    
                    items_with_urls.append({
                        "id": item.get("id"),
                        "image_url": image_url,
                        "raw_caption": item.get("raw_caption"),
                        "primary_category": item.get("primary_category"),
                        "primary_color": item.get("primary_color"),
                        "pattern": item.get("pattern"),
                    })
                
                # Add complete outfit to results
                outfits.append({
                    "outfit_id": outfit_id,
                    "name": outfit_name,
                    "items": items_with_urls,
                    "saved_at": saved_at,
                    "items_count": len(items_with_urls)
                })
                
                logger.info(f"Successfully processed outfit {outfit_id} with {len(items_with_urls)} items")
                
            except Exception as e:
                logger.error(f"Error processing outfit file {outfit_file}: {e}")
                continue
        
        logger.info(f"Successfully retrieved {len(outfits)} outfits")
        
        return {
            "outfits": outfits,
            "count": len(outfits),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving outfits: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve outfits: {str(e)}"
        )


@app.delete("/wardrobe/outfit-delete/{outfit_id}", response_model=Dict[str, Any])
async def delete_outfit(outfit_id: str):
    """
    Delete a saved outfit from S3.
    
    This endpoint:
    1. Validates the outfit_id
    2. Deletes the outfit JSON file from S3 outfits/ folder
    3. Returns deletion status
    
    Args:
        outfit_id: The unique identifier of the outfit to delete
        
    Returns:
        Dict with:
            - status: "success"
            - message: Deletion confirmation
            - outfit_id: The deleted outfit ID
    """
    try:
        logger.info(f"Deleting outfit {outfit_id}")
        
        if not outfit_id:
            raise HTTPException(
                status_code=400,
                detail="Outfit ID is required"
            )
        
        # Generate S3 key
        s3_key = f"outfits/{outfit_id}.json"
        
        # Delete from S3
        try:
            delete_object(bucket=None, key=s3_key)
            logger.info(f"Successfully deleted outfit {outfit_id} from S3")
        except Exception as e:
            logger.error(f"Failed to delete outfit {outfit_id} from S3: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete outfit: {str(e)}"
            )
        
        return {
            "status": "success",
            "message": f"Outfit {outfit_id} deleted successfully",
            "outfit_id": outfit_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting outfit: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete outfit: {str(e)}"
        )


@app.post("/wardrobe/agent", response_model=Dict[str, Any])
async def wardrobe_agent(query: str):
    """
    Agentic endpoint for intelligent wardrobe outfit generation.
    
    The Gemini LLM agent autonomously decides:
    - Which wardrobe items to search for based on user needs
    - How to combine items into outfit suggestions
    - When it has generated satisfactory results
    
    Returns enriched combinations with image URLs and descriptions for each item.
    
    Args:
        query (str): Natural language description of desired outfits
                    (e.g., "I need blue summer outfits for beach days")
        
    Returns:
        Dict with:
            - combinations: List of outfit combinations with enriched items (id, description, link)
            - count: Number of combinations generated
            - input: The original user query
            - status: "success" or "error"
    """
    try:
        logger.info(f"Wardrobe agent received query: '{query}'")
        
        # Run the agentic agent
        result = run_agent(query)
        
        if result.get("status") == "error":
            logger.error(f"Agent error: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent failed: {result.get('error')}"
            )
        
        agent_response = result.get("agent_response", "")
        logger.info(f"Agent response: {agent_response}")
        return {
            "input": query,
            "agent_response": agent_response,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in wardrobe agent endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Agent endpoint failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



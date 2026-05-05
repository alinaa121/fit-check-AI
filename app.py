from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import uuid

from vectordb import WardrobeVectorDB
from s3_utils import *
from clothing_pipeline import ClothingPipeline
from agent import run_agent

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
    allow_origins=["*"],  # In production, specify your frontend domain
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
            
            # Generate proxy URL instead of presigned S3 URL
            # This bypasses S3 Block Public Access restrictions
            image_url = None
            if img_path:
                image_url = f"http://localhost:8000/wardrobe/image/{img_path}"
            
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
        filters = vdb.extract_filters_from_query(query)
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
        
        # Step 6: Construct response with image URLs
        result_urls = []
        for item in items_with_metadata:
            img_path = item.get('img_path')
            image_url = f"http://localhost:8000/wardrobe/image/{img_path}" if img_path else None
            
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


class UpdateItemRequest(BaseModel):
    field_name: str
    new_value: Any


@app.patch("/wardrobe/item/{item_id}", response_model=Dict[str, Any])
async def update_item(item_id: str, request: UpdateItemRequest):
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
        logger.info(f"Updating item {item_id}: {request.field_name} = {request.new_value}")
        
        # Validate field name
        valid_fields = [
            "raw_caption", "primary_category", "sub_category", "primary_color",
            "secondary_colors", "pattern", "material", "season", "weather",
            "occasion", "fit", "style_vibe"
        ]
        
        if request.field_name not in valid_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid field name. Valid fields: {', '.join(valid_fields)}"
            )
        
        # Perform the update
        success = vdb.update_by_point(item_id, request.field_name, request.new_value)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Item with ID '{item_id}' not found"
            )
        
        # Retrieve updated item
        updated_item = vdb.get_by_id(item_id)
        
        return {
            "status": "success",
            "message": f"Field '{request.field_name}' updated successfully",
            "id": item_id,
            "field_updated": request.field_name,
            "new_value": request.new_value,
            "re_embedded": request.field_name == "raw_caption",
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


@app.get("/wardrobe/recommend", response_model=Dict[str, Any])
async def recommend_catalogue_items(query: str):
    """
    Recommend clothing items from the catalogue based on a query.
    
    This endpoint uses AI to:
    1. Extract filters from the natural language query
    2. Search the wardrobe based on those filters
    3. Rank results by relevance
    4. Return the top recommendations with image URLs
    
    Args:
        query (str): Natural language query for recommendations (e.g., "cute airport tops")
        
    Returns:
        Dict with:
            - caption: AI-generated description of the recommendations
            - items: List of image URLs for the recommended items
    """
    try:
        logger.info(f"Getting recommendations for query: '{query}'")
        
        # Extract filters from query
        filters = vdb.extract_filters_from_query(query)
        logger.info(f"Extracted Filters: {filters}")
        
        # Count items matching filters
        count = vdb.count_items(filters)
        logger.info(f"Found {count} items matching filters")
        
        # Search with filters if found items, otherwise search all
        items = []
        if count > 1:
            items = vdb.search(query, 10, filters)
            items = [{"id": item['id'], "description": item['raw_caption']} for item in items]
        else:
            items = vdb.search(query, 10)
            items = [{"id": item['id'], "description": item['raw_caption']} for item in items]
        
        logger.info(f"Prepared {len(items)} items for ranking")
        
        # Rank and filter results
        ranked = pipeline.rank_and_filter_results(query, items)
        
        if ranked is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to rank recommendations"
            )
        
        # Get full metadata for each ranked item ID
        ranked_ids = ranked.get('ranked_item_ids', [])
        caption = ranked.get('caption', 'Here are our recommendations.')
        
        # Fetch full item details from vector DB
        items_with_metadata = vdb.search_by_points(ranked_ids)
        logger.info(f"Retrieved full metadata for {len(items_with_metadata)} recommendations")
        
        return {
            "caption": caption,
            "items": [item.get('img_path', '') for item in items_with_metadata]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


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
        
        # Helper function to enrich a single item with metadata and image URL
        def enrich_item(item: Dict[str, Any]) -> Dict[str, Any]:
            if not item or not item.get("id"):
                return None
            
            try:
                # Fetch full metadata from vector DB
                item_id = item.get("id")
                point_data = vdb.get_by_id(item_id)
                
                if not point_data:
                    return item  # Return original if not found
                
                # Extract payload (metadata)
                metadata = point_data.get("payload", {})
                
                # Build image URL
                img_path = metadata.get("img_path")
                image_url = f"http://localhost:8000/wardrobe/image/{img_path}" if img_path else None
                
                # Enrich with description and link
                return {
                    "id": item_id,
                    "description": item.get("description", metadata.get("raw_caption", "")),
                    "link": image_url,
                    "raw_caption": metadata.get("raw_caption"),
                    "primary_category": metadata.get("primary_category"),
                    "primary_color": metadata.get("primary_color"),
                }
            except Exception as e:
                logger.warning(f"Failed to enrich item {item.get('id')}: {e}")
                return item
        
        # Enrich all combinations with metadata and image URLs
        enriched_combinations = []
        for combo in result.get("combinations", []):
            enriched_combo = {
                "combo_id": combo.get("combo_id"),
                "top": enrich_item(combo.get("top")),
                "bottom": enrich_item(combo.get("bottom")),
                "full_body": enrich_item(combo.get("full_body")),
                "footwear": enrich_item(combo.get("footwear")),
                "accessories": [enrich_item(acc) for acc in combo.get("accessories", [])],
                "reasoning": combo.get("reasoning"),
                "style_tips": combo.get("style_tips")
            }
            enriched_combinations.append(enriched_combo)
        
        logger.info(f"Agent generated {result.get('count', 0)} outfit combinations with enriched metadata")
        
        return {
            "combinations": enriched_combinations,
            "count": result.get("count", 0),
            "input": result.get("input"),
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



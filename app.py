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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



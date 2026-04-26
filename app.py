from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import logging
import uuid

from vectordb import WardrobeVectorDB
from s3_utils import generate_presigned_url
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
            
            # Generate presigned URL for the image
            image_url = None
            if img_path:
                try:
                    image_url = generate_presigned_url(
                        bucket=None,  # Uses BUCKET_NAME from env
                        key=img_path,
                        expiration=url_expiration
                    )
                except Exception as e:
                    logger.error(f"Failed to generate presigned URL for {img_path}: {e}")
            
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



import os
import uuid
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct, Filter, FieldCondition, MatchValue, MatchAny,
    PayloadSchemaType
)
from sentence_transformers import SentenceTransformer
from config import *

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class WardrobeVectorDB:
    def __init__(self, collection: str = COLLECTION_NAME):
        load_dotenv()
        self.endpoint = os.getenv("qdrant_endpoint")
        self.api_key = os.getenv("qdrant_apikey")
        self.collection = collection
        self.client = QdrantClient(
            url=self.endpoint,
            api_key=self.api_key,
            prefer_grpc=False,
            check_compatibility=False,
        )
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info(f"Initialized WardrobeVectorDB with collection '{collection}'")

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self.model.encode(texts, show_progress_bar=False)]

    def add(self, img_path: str, metadata: dict) -> str:
        """Add a clothing item to the collection with comprehensive metadata. Returns the point ID."""
        # Use raw_caption for embedding as it's the most descriptive
        text_for_embedding = metadata.get('raw_caption', '')
        
        # Fallback: if no raw_caption, create text from other fields
        if not text_for_embedding:
            parts = [
                metadata.get('sub_category', ''),
                metadata.get('primary_color', ''),
                metadata.get('pattern', ''),
                metadata.get('material', '')
            ]
            text_for_embedding = ' '.join([p for p in parts if p])
        
        vec = self.embed([text_for_embedding])[0]
        now_iso = datetime.utcnow().isoformat() + "Z"
        point_id = str(uuid.uuid4())
        
        # Store all metadata in payload
        payload = {
            "created_at": now_iso,
            "modified_at": now_iso,
            "img_path": img_path,
            "raw_caption": metadata.get('raw_caption', ''),
            "primary_category": metadata.get('primary_category', ''),
            "sub_category": metadata.get('sub_category', ''),
            "primary_color": metadata.get('primary_color', ''),
            "secondary_colors": metadata.get('secondary_colors', []),
            "pattern": metadata.get('pattern', ''),
            "material": metadata.get('material', ''),
            "season": metadata.get('season', []),
            "weather": metadata.get('weather', []),
            "occasion": metadata.get('occasion', []),
            "fit": metadata.get('fit', ''),
            "style_vibe": metadata.get('style_vibe', []),
        }
        
        point = PointStruct(
            id=point_id,
            vector=vec,
            payload=payload,
        )
        self.client.upsert(collection_name=self.collection, points=[point])
        logger.info(f"Added point {point_id} with category '{metadata.get('primary_category')}' sub '{metadata.get('sub_category')}' and img_path '{img_path}'")
        return point_id

    def search(self, query: str, limit: int = 5):
        """Search for similar items. Returns list of dicts with all metadata and score."""
        qvec = self.embed([query])[0]
        logger.info(f"Searching for: '{query}' with limit={limit}")
        # qdrant-client >= 1.7 uses query_points; fallback to search for older versions
        try:
            results = self.client.query_points(
                collection_name=self.collection,
                query=qvec,
                limit=limit,
                with_payload=True,
            )
            # query_points returns a QueryResponse; extract .points
            points = results.points if hasattr(results, "points") else results

            # Extract all metadata from each result
            output = []
            for p in points:
                payload = p.payload if hasattr(p, "payload") else {}
                output.append({
                    "id": p.id if hasattr(p, "id") else None,
                    "score": p.score if hasattr(p, "score") else None,
                    "img_path": payload.get("img_path"),
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
                })
            logger.info(f"Search returned {len(output)} results")
            return output
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []

    def list_all(self, limit: int = 100):
        """List all items in the collection."""
        logger.info(f"Listing all items with limit={limit}")
        return self.client.scroll(
            collection_name=self.collection,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

    def get_by_id(self, point_id: str) -> Optional[Dict[str, Any]]:
        """Get a single point by ID. Returns dict with id, payload, or None if not found."""
        logger.info(f"Fetching point {point_id}")
        try:
            points = self.client.retrieve(
                collection_name=self.collection,
                ids=[point_id],
                with_payload=True,
                with_vectors=False,
            )
            if not points:
                logger.warning(f"Point {point_id} not found")
                return None
            
            point = points[0]
            return {
                "id": point.id,
                "payload": point.payload if hasattr(point, "payload") else {},
            }
        except Exception as e:
            logger.error(f"Error fetching point {point_id}: {e}")
            return None

    def delete_by_image_path(self, img_path: str) -> bool:
        """Delete a point by image path. Returns True on success."""
        logger.warning(f"Deleting point with img_path '{img_path}'")
        self.client.delete(
            collection_name=self.collection,
            points_selector={"filter": {"must": [{"key": "img_path", "match": {"value": img_path}}]}},
        )
        logger.info(f"Deleted point with img_path '{img_path}'")
        return True

    def delete_by_point(self, point_id: str) -> bool:
        """Delete a point by ID. Returns True on success."""
        logger.warning(f"Deleting point {point_id}")
        self.client.delete(
            collection_name=self.collection,
            points_selector=[point_id],
        )
        logger.info(f"Deleted point {point_id}")
        return True

    def update_by_point(self, point_id: str, field_name: str, new_value: Any) -> bool:
        """Update a field for a specific point. 
        
        If field is 'raw_caption', the vector will be re-embedded.
        Otherwise, only the metadata is updated.
        
        Args:
            point_id: The ID of the point to update
            field_name: The field to update (e.g., 'raw_caption', 'primary_color', etc.)
            new_value: The new value for the field
            
        Returns:
            True on success, False if point not found
        """
        logger.info(f"Updating point {point_id}: {field_name} = {new_value}")
        
        # Get existing point
        existing = self.get_by_id(point_id)
        if not existing:
            logger.error(f"Point {point_id} not found, cannot update")
            return False
        
        payload = existing["payload"]
        
        # Update the field in payload
        payload[field_name] = new_value
        
        # Update modified timestamp
        payload["modified_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Check if we need to re-embed
        if field_name == "raw_caption":
            # Re-embed using the new caption
            text_for_embedding = new_value if new_value else ''
            
            # Fallback if caption is empty
            if not text_for_embedding:
                parts = [
                    payload.get('sub_category', ''),
                    payload.get('primary_color', ''),
                    payload.get('pattern', ''),
                    payload.get('material', '')
                ]
                text_for_embedding = ' '.join([p for p in parts if p])
            
            vec = self.embed([text_for_embedding])[0]
            
            # Update point with new vector and payload
            point = PointStruct(
                id=point_id,
                vector=vec,
                payload=payload,
            )
            self.client.upsert(collection_name=self.collection, points=[point])
            logger.info(f"Updated point {point_id} with new embedding for raw_caption")
        else:
            # Just update the payload, no need to re-embed
            self.client.set_payload(
                collection_name=self.collection,
                payload=payload,
                points=[point_id],
            )
            logger.info(f"Updated point {point_id} metadata: {field_name}")
        
        return True

    def count_items(self, filters: Optional[Dict[str, list]] = None) -> int:
        """Count items in the collection based on metadata filters.
        
        Args:
            filters: Dictionary of metadata filters where all values are lists. Example:
                {
                    "primary_category": ["top"],
                    "season": ["summer", "winter"],
                    "primary_color": ["blue"],
                    "style_vibe": ["casual", "sporty"]
                }
                If None or empty, returns total count of all items.
                - All values must be lists
                - Empty lists or None values will be ignored (no filter applied)
                - Single item lists match that one value
                - Multiple item lists match any item in the list (OR logic)
        
        Returns:
            Integer count of matching items
        """
        if not filters:
            # No filters - count all items
            logger.info("Counting all items (no filters)")
            try:
                result = self.client.count(collection_name=self.collection)
                count = result.count if hasattr(result, 'count') else result
                logger.info(f"Total items in collection: {count}")
                return count
            except Exception as e:
                logger.error(f"Error counting all items: {e}")
                return 0
        
        # Build filter conditions
        must_conditions = []
        
        for key, value in filters.items():
            if value is None or not isinstance(value, list) or len(value) == 0:
                # Skip None, non-list, or empty list values
                continue
            
            if len(value) == 1:
                # Single item list - use exact match
                must_conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value[0])
                    )
                )
            else:
                # Multiple items - use "any" match
                must_conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchAny(any=value)
                    )
                )
        
        if not must_conditions:
            # All filters were None or empty - count all items
            logger.info("All filters were empty, counting all items")
            try:
                result = self.client.count(collection_name=self.collection)
                count = result.count if hasattr(result, 'count') else result
                logger.info(f"Total items in collection: {count}")
                return count
            except Exception as e:
                logger.error(f"Error counting all items: {e}")
                return 0
        
        # Build the filter structure using proper Qdrant models
        filter_query = Filter(must=must_conditions)
        
        logger.info(f"Counting items with filters: {filters}")
        logger.debug(f"Filter query: {filter_query}")
        
        try:
            result = self.client.count(
                collection_name=self.collection,
                count_filter=filter_query
            )
            count = result.count if hasattr(result, 'count') else result
            logger.info(f"Found {count} items matching filters")
            return count
        except Exception as e:
            logger.error(f"Error counting items with filters: {e}")
            return 0
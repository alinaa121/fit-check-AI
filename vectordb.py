import os
import uuid
import json
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
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

    def add(self, img_path: str, clothing_type: str, text: str) -> str:
        """Add a clothing item to the collection. Returns the point ID."""
        vec = self.embed([text])[0]
        now_iso = datetime.utcnow().isoformat() + "Z"
        point_id = str(uuid.uuid4())
        point = PointStruct(
            id=point_id,
            vector=vec,
            payload={
                "created_at": now_iso,
                "modified_at": now_iso,
                "type": clothing_type,
                "img_path": img_path,
                "text": text,
            },
        )
        self.client.upsert(collection_name=self.collection, points=[point])
        logger.info(f"Added point {point_id} with type '{clothing_type}' and img_path '{img_path}'")
        return point_id

    def search(self, query: str, limit: int = 5):
        """Search for similar items. Returns list of dicts with text, img_path, type, and score."""
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

            # Extract text and img_path from each result
            output = []
            for p in points:
                payload = p.payload if hasattr(p, "payload") else {}
                output.append({
                    "id": p.id if hasattr(p, "id") else None,
                    "score": p.score if hasattr(p, "score") else None,
                    "text": payload.get("text"),
                    "img_path": payload.get("img_path"),
                    "type": payload.get("type"),
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

    def delete(self, point_id: str) -> bool:
        """Delete a point by ID. Returns True on success."""
        logger.warning(f"Deleting point {point_id}")
        self.client.delete(
            collection_name=self.collection,
            points_selector=[point_id],
        )
        logger.info(f"Deleted point {point_id}")
        return True
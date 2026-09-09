"""MongoDB client and data repository for AlphaWatch agents."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import math
try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    from bson import ObjectId
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    MongoClient = None
    PyMongoError = Exception

    class ObjectId(str):
        pass

from .config import get_settings

logger = logging.getLogger(__name__)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class MongoRepository:
    """Repository handling articles and alerts persistence and vector retrieval."""

    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        settings = get_settings()
        self.uri = uri or settings.mongodb_uri
        self.db_name = db_name or settings.mongodb_db_name
        self.client: Optional[MongoClient] = None
        self.db = None

    def connect(self):
        """Connect to MongoDB."""
        if not PYMONGO_AVAILABLE:
            logger.warning("[Mongo] PyMongo package not installed; running in offline/mock mode.")
            return

        if self.client is None:
            logger.info(f"[Mongo] Connecting to {self.uri} (database: {self.db_name})...")
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.db_name]
            logger.info("[Mongo] Connected successfully.")

    def close(self):
        """Close MongoDB connection."""
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("[Mongo] Connection closed.")

    def get_collection(self, name: str):
        """Get collection with lazy connect."""
        if self.db is None:
            self.connect()
        return self.db[name] if self.db is not None else None

    def upsert_article(self, article_data: Dict[str, Any]) -> Optional[ObjectId]:
        """
        Upsert an article by its contentHash.
        Updates extraction and embedding fields if present.
        """
        try:
            coll = self.get_collection("articles")
            if coll is None:
                return ObjectId("000000000000000000000001")

            content_hash = article_data.get("contentHash")
            if not content_hash:
                raise ValueError("Article missing required contentHash")

            update_doc = {
                "$set": {
                    "title": article_data.get("title", ""),
                    "content": article_data.get("content", ""),
                    "url": article_data.get("url", ""),
                    "source": article_data.get("source", "unknown"),
                    "updatedAt": datetime.now(timezone.utc),
                },
                "$setOnInsert": {
                    "contentHash": content_hash,
                    "publishedAt": article_data.get("publishedAt"),
                    "ingestedAt": article_data.get("ingestedAt") or datetime.now(timezone.utc),
                    "createdAt": datetime.now(timezone.utc),
                }
            }

            if "extraction" in article_data:
                update_doc["$set"]["extraction"] = article_data["extraction"]

            if "embedding" in article_data:
                update_doc["$set"]["embedding"] = article_data["embedding"]

            result = coll.update_one(
                {"contentHash": content_hash},
                update_doc,
                upsert=True
            )

            if result.upserted_id:
                return result.upserted_id
            existing = coll.find_one({"contentHash": content_hash}, {"_id": 1})
            return existing["_id"] if existing else None

        except Exception as e:
            logger.error(f"[Mongo] Failed to upsert article: {e}")
            return None

    def find_article_by_hash(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve article by contentHash."""
        try:
            coll = self.get_collection("articles")
            if coll is None:
                return None
            return coll.find_one({"contentHash": content_hash})
        except Exception as e:
            logger.error(f"[Mongo] Error finding article: {e}")
            return None

    def save_alert(self, alert_data: Dict[str, Any]) -> Optional[ObjectId]:
        """Save an alert to the alerts collection."""
        try:
            coll = self.get_collection("alerts")
            if coll is None:
                return ObjectId("000000000000000000000002")
            doc = {
                "articleId": alert_data.get("articleId"),
                "tickers": alert_data.get("tickers", []),
                "sentiment": alert_data.get("sentiment", "neutral"),
                "sentimentScore": alert_data.get("sentimentScore", 0.5),
                "significanceScore": alert_data.get("significanceScore", 0.0),
                "analysisType": alert_data.get("analysisType", "standard"),
                "comparativeAnalysis": alert_data.get("comparativeAnalysis", ""),
                "alertHeadline": alert_data.get("alertHeadline", ""),
                "alertBody": alert_data.get("alertBody", ""),
                "source": alert_data.get("source", "unknown"),
                "timestamp": alert_data.get("timestamp") or datetime.now(timezone.utc),
                "createdAt": datetime.now(timezone.utc),
            }
            res = coll.insert_one(doc)
            return res.inserted_id
        except PyMongoError as e:
            logger.error(f"[Mongo] Error saving alert: {e}")
            return None

    def retrieve_historical_context(
        self,
        tickers: List[str],
        query_embedding: Optional[List[float]] = None,
        limit: int = 5,
        exclude_id: Optional[ObjectId] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant historical articles.
        If query_embedding is provided, calculates vector cosine similarity across recent articles
        for the given tickers (or overall recent if no tickers match).
        """
        try:
            coll = self.get_collection("articles")
            if coll is None:
                return []
            query: Dict[str, Any] = {}
            if exclude_id:
                query["_id"] = {"$ne": exclude_id}

            if tickers:
                query["extraction.tickers"] = {"$in": tickers}

            # Fetch recent candidate articles
            candidates = list(
                coll.find(query, {
                    "_id": 1,
                    "title": 1,
                    "content": 1,
                    "extraction": 1,
                    "embedding": 1,
                    "publishedAt": 1,
                    "createdAt": 1,
                    "source": 1
                })
                .sort("createdAt", -1)
                .limit(30)
            )

            # If tickers gave no candidates, search recent articles regardless of ticker
            if not candidates and tickers:
                general_query = {"_id": {"$ne": exclude_id}} if exclude_id else {}
                candidates = list(
                    coll.find(general_query, {
                        "_id": 1,
                        "title": 1,
                        "content": 1,
                        "extraction": 1,
                        "embedding": 1,
                        "publishedAt": 1,
                        "createdAt": 1,
                        "source": 1
                    })
                    .sort("createdAt", -1)
                    .limit(20)
                )

            if not query_embedding:
                return candidates[:limit]

            # Rank by cosine similarity
            scored_candidates = []
            for item in candidates:
                item_emb = item.get("embedding")
                score = cosine_similarity(query_embedding, item_emb) if item_emb else 0.0
                item_clean = {k: v for k, v in item.items() if k != "embedding"}
                item_clean["similarityScore"] = round(score, 4)
                scored_candidates.append(item_clean)

            scored_candidates.sort(key=lambda x: x["similarityScore"], reverse=True)
            return scored_candidates[:limit]

        except PyMongoError as e:
            logger.error(f"[Mongo] Error retrieving historical context: {e}")
            return []


_mongo_repo: Optional[MongoRepository] = None


def get_mongo_repo() -> MongoRepository:
    """Singleton getter for MongoRepository."""
    global _mongo_repo
    if _mongo_repo is None:
        _mongo_repo = MongoRepository()
    return _mongo_repo

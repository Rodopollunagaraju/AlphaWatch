"""Embedding generator and vector utilities for AlphaWatch.

Uses Google Gemini's text-embedding-004 (768 dimensions) with a deterministic
fallback for offline testing and development.
"""

import hashlib
import logging
import math
from typing import List, Optional

from .config import get_settings

logger = logging.getLogger(__name__)

# Dimension for text-embedding-004
EMBEDDING_DIM = 768


def _generate_deterministic_fallback_vector(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """
    Generate a deterministic, normalized pseudo-embedding vector for offline use.
    Produces repeatable vectors where similar texts yield reasonable similarity.
    """
    if not text:
        return [0.0] * dim

    vec = [0.0] * dim
    words = text.lower().split()
    for word in words:
        h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [round(x / norm, 6) for x in vec]
    else:
        vec[0] = 1.0
    return vec


class EmbeddingGenerator:
    """Generates vector embeddings using Gemini or deterministic fallback."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model_name = model or settings.embedding_model
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize Gemini client if API key is present."""
        if not self.api_key or self.api_key.startswith("your-"):
            logger.info("[Embeddings] No valid GEMINI_API_KEY found; using fallback embedding mode.")
            return

        try:
            # Try new google-genai SDK first
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                self._client_type = "google-genai"
                logger.info(f"[Embeddings] Initialized google.genai with model {self.model_name}")
                return
            except ImportError:
                pass

            # Fall back to google.generativeai
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai
            self._client_type = "google-generativeai"
            logger.info(f"[Embeddings] Initialized google.generativeai with model {self.model_name}")
        except Exception as e:
            logger.warning(f"[Embeddings] Could not initialize Gemini SDK: {e}. Fallback enabled.")
            self._client = None

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        Returns a list of 768 floats.
        """
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            return [0.0] * EMBEDDING_DIM

        # Try Google Gemini API
        if self._client:
            try:
                if self._client_type == "google-genai":
                    response = self._client.models.embed_content(
                        model=self.model_name,
                        contents=cleaned_text,
                    )
                    # Handle response formats
                    if hasattr(response, "embedding") and hasattr(response.embedding, "values"):
                        return [float(x) for x in response.embedding.values]
                    if hasattr(response, "embeddings") and response.embeddings:
                        return [float(x) for x in response.embeddings[0].values]

                elif self._client_type == "google-generativeai":
                    response = self._client.embed_content(
                        model=f"models/{self.model_name}",
                        content=cleaned_text,
                        task_type="retrieval_document"
                    )
                    if "embedding" in response:
                        return [float(x) for x in response["embedding"]]
            except Exception as e:
                logger.warning(f"[Embeddings] API call failed ({e}); falling back to local vector.")

        return _generate_deterministic_fallback_vector(cleaned_text, EMBEDDING_DIM)

    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [self.generate_embedding(t) for t in texts]


_embedding_generator: Optional[EmbeddingGenerator] = None


def get_embedding_generator() -> EmbeddingGenerator:
    """Singleton getter for EmbeddingGenerator."""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator

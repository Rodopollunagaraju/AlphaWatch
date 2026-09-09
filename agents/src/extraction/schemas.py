"""Pydantic schemas for extracted news data."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ExtractedNews(BaseModel):
    """Structured extraction output from raw market news."""

    tickers: List[str] = Field(
        default_factory=list,
        description="Identified stock ticker symbols (e.g. AAPL, TSLA, MSFT, NVDA)"
    )
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        default="neutral",
        description="Overall market sentiment polarity"
    )
    sentiment_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence-weighted sentiment score between 0.0 (bearish) and 1.0 (bullish)"
    )
    category: str = Field(
        default="general",
        description="Primary financial category (e.g. earnings, mergers, regulatory, macro, guidance)"
    )
    summary: str = Field(
        default="",
        description="Concise 2-3 sentence executive summary of financial impact"
    )
    relevance_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Market relevance score between 0.0 (non-financial/noise) and 1.0 (critical market news)"
    )
    key_entities: List[str] = Field(
        default_factory=list,
        description="Named organizations, individuals, or key regulatory bodies"
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Extraction model confidence"
    )

    def to_mongo_dict(self):
        """Format extraction fields for MongoDB article document."""
        return {
            "tickers": self.tickers,
            "sentiment": self.sentiment,
            "sentimentScore": round(self.sentiment_score, 3),
            "category": self.category,
            "summary": self.summary,
            "relevanceScore": round(self.relevance_score, 3),
            "confidence": round(self.confidence, 3),
        }

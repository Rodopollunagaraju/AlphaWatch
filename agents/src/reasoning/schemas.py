"""Schemas for RAG reasoning and alert evaluation."""

from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class AlertDecision(BaseModel):
    """Result of deep reasoning and significance gate evaluation."""

    should_alert: bool = Field(
        default=False,
        description="Whether this event surpasses the significance threshold for real-time alerting"
    )
    significance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Assessed market impact score between 0.0 (negligible) and 1.0 (black swan / massive market mover)"
    )
    alert_headline: str = Field(
        default="",
        description="Concise, high-impact headline suitable for trader terminals"
    )
    alert_body: str = Field(
        default="",
        description="Comprehensive analysis contrasting current news with historical precedent"
    )
    analysis_type: str = Field(
        default="comparative_rag",
        description="Reasoning methodology applied: comparative_rag or direct"
    )
    comparative_analysis: str = Field(
        default="",
        description="Specific comparison points against past articles or prior earnings/guidance"
    )
    market_impact_hypothesis: str = Field(
        default="",
        description="Predicted price action or market reaction hypothesis"
    )
    tickers: List[str] = Field(
        default_factory=list,
        description="Impacted ticker symbols"
    )
    sentiment: str = Field(
        default="neutral",
        description="Consolidated sentiment polarity (positive, neutral, negative)"
    )
    sentiment_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Consolidated sentiment magnitude"
    )

    def to_kafka_payload(self, article_id: Optional[str] = None, source: str = "market") -> dict:
        """Format payload for the processed-alerts Kafka topic matching API gateway socket relay contract."""
        return {
            "articleId": str(article_id) if article_id else None,
            "tickers": self.tickers,
            "sentiment": self.sentiment,
            "sentimentScore": round(self.sentiment_score, 3),
            "significanceScore": round(self.significance_score, 3),
            "analysisType": self.analysis_type,
            "comparativeAnalysis": self.comparative_analysis,
            "alertHeadline": self.alert_headline,
            "alertBody": self.alert_body,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

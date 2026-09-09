"""AlphaWatch Multi-Agent Processing Pipeline.

Coordinates the complete workflow:
1. Raw article intake from Kafka
2. Structured extraction & relevance gating (gemini-2.0-flash)
3. Embedding generation (text-embedding-004)
4. Persistent article storage in MongoDB
5. Historical context vector retrieval
6. RAG comparative reasoning & alert significance scoring (gemini-2.5-flash)
7. Alert persistence & Kafka processed-alerts publishing
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .config import get_settings
from .extraction.extractor import get_extraction_agent, ExtractionAgent
from .extraction.schemas import ExtractedNews
from .embeddings import get_embedding_generator, EmbeddingGenerator
from .mongo_client import get_mongo_repo, MongoRepository
from .reasoning.reasoner import get_reasoning_agent, ReasoningAgent
from .reasoning.schemas import AlertDecision
from .kafka_producer import get_alert_producer, AlertProducer

logger = logging.getLogger(__name__)


class MultiAgentPipeline:
    """End-to-end orchestrator for AI market intelligence processing."""

    def __init__(
        self,
        extractor: Optional[ExtractionAgent] = None,
        embedding_gen: Optional[EmbeddingGenerator] = None,
        reasoner: Optional[ReasoningAgent] = None,
        mongo_repo: Optional[MongoRepository] = None,
        alert_producer: Optional[AlertProducer] = None
    ):
        self.settings = get_settings()
        self.extractor = extractor or get_extraction_agent()
        self.embedding_gen = embedding_gen or get_embedding_generator()
        self.reasoner = reasoner or get_reasoning_agent()
        self.mongo_repo = mongo_repo or get_mongo_repo()
        self.alert_producer = alert_producer or get_alert_producer()

    def process_article(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single incoming raw news article through the multi-agent pipeline.
        Returns a dict summarizing the pipeline outcome.
        """
        title = raw_article.get("title", "").strip()
        content = raw_article.get("content", "").strip()
        source = raw_article.get("source", "market")
        content_hash = raw_article.get("contentHash")

        if not title and not content:
            logger.warning("[Pipeline] Received empty article, skipping.")
            return {"status": "skipped", "reason": "empty_content"}

        logger.info(f"[Pipeline] Processing: \"{title[:60]}...\" (source: {source})")

        # Step 1: Structured extraction (gemini-2.0-flash)
        extracted: ExtractedNews = self.extractor.extract(title, content, source)
        logger.info(
            f"[Pipeline] Extraction completed: tickers={extracted.tickers}, "
            f"sentiment={extracted.sentiment} ({extracted.sentiment_score}), "
            f"category={extracted.category}, relevance={extracted.relevance_score}"
        )

        # Step 2: Relevance Gate
        if not self.extractor.is_relevant(extracted, self.settings.relevance_gate_threshold):
            logger.info(
                f"[Pipeline] Article below relevance threshold ({extracted.relevance_score} < "
                f"{self.settings.relevance_gate_threshold}), skipping reasoning."
            )
            return {
                "status": "filtered",
                "reason": "below_relevance_threshold",
                "extracted": extracted.model_dump()
            }

        # Step 3: Generate text embedding (text-embedding-004)
        embed_text = f"{title}. {extracted.summary}"
        embedding = self.embedding_gen.generate_embedding(embed_text)

        # Step 4: Upsert article and embedding to MongoDB
        article_doc = {
            "contentHash": content_hash or f"hash_{hash(title + content)}",
            "title": title,
            "content": content,
            "url": raw_article.get("url", ""),
            "source": source,
            "publishedAt": raw_article.get("publishedAt"),
            "ingestedAt": raw_article.get("ingestedAt") or datetime.now(timezone.utc),
            "extraction": extracted.to_mongo_dict(),
            "embedding": embedding
        }
        article_id = self.mongo_repo.upsert_article(article_doc)

        # Step 5: Historical Context Retrieval via Vector Search
        historical_context = self.mongo_repo.retrieve_historical_context(
            tickers=extracted.tickers,
            query_embedding=embedding,
            limit=5,
            exclude_id=article_id
        )
        logger.info(f"[Pipeline] Retrieved {len(historical_context)} historical context articles.")

        # Step 6: RAG Reasoning & Significance Gate (gemini-2.5-flash)
        decision: AlertDecision = self.reasoner.evaluate(
            extracted=extracted,
            raw_article=raw_article,
            historical_context=historical_context,
            threshold=self.settings.alert_significance_threshold
        )
        logger.info(
            f"[Pipeline] Reasoning completed: should_alert={decision.should_alert}, "
            f"significance={decision.significance_score}"
        )

        # Step 7: Alert Dispatch
        alert_dispatched = False
        saved_alert_id = None

        if decision.should_alert:
            # 7a. Save alert in MongoDB
            alert_doc = {
                "articleId": article_id,
                "tickers": decision.tickers,
                "sentiment": decision.sentiment,
                "sentimentScore": decision.sentiment_score,
                "significanceScore": decision.significance_score,
                "analysisType": decision.analysis_type,
                "comparativeAnalysis": decision.comparative_analysis,
                "alertHeadline": decision.alert_headline,
                "alertBody": decision.alert_body,
                "source": source,
                "timestamp": datetime.now(timezone.utc)
            }
            saved_alert_id = self.mongo_repo.save_alert(alert_doc)

            # 7b. Publish to Kafka processed-alerts topic
            kafka_payload = decision.to_kafka_payload(
                article_id=str(article_id) if article_id else None,
                source=source
            )
            alert_dispatched = self.alert_producer.publish_alert(kafka_payload)
            logger.info(
                f"[Pipeline] ALERT DISPATCHED -> Kafka topic '{self.settings.processed_alerts_topic}': "
                f"\"{decision.alert_headline[:60]}...\""
            )
        else:
            logger.info(
                f"[Pipeline] Significance below alert threshold ({decision.significance_score} < "
                f"{self.settings.alert_significance_threshold}); no alert dispatched."
            )

        return {
            "status": "success",
            "article_id": str(article_id) if article_id else None,
            "extracted": extracted.model_dump(),
            "decision": decision.model_dump(),
            "alert_dispatched": alert_dispatched,
            "alert_id": str(saved_alert_id) if saved_alert_id else None
        }


_pipeline_instance: Optional[MultiAgentPipeline] = None


def get_pipeline() -> MultiAgentPipeline:
    """Singleton getter for MultiAgentPipeline."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = MultiAgentPipeline()
    return _pipeline_instance

"""Configuration settings for AlphaWatch Agent Worker."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()


class Settings:
    """Application configuration with environment variable support and fallbacks."""

    def __init__(self):
        # Gemini / AI
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.extraction_model: str = os.getenv("EXTRACTION_MODEL", "gemini-2.0-flash")
        self.reasoning_model: str = os.getenv("REASONING_MODEL", "gemini-2.5-flash")
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

        # Kafka
        self.kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
        self.kafka_client_id: str = os.getenv("KAFKA_CLIENT_ID", "alphawatch-agents")
        self.kafka_consumer_group: str = os.getenv("KAFKA_CONSUMER_GROUP", "alphawatch-agent-workers")
        self.raw_news_topic: str = os.getenv("RAW_NEWS_TOPIC", "raw-news-feed")
        self.processed_alerts_topic: str = os.getenv("PROCESSED_ALERTS_TOPIC", "processed-alerts")

        # MongoDB
        self.mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/alphawatch")
        self.mongodb_db_name: str = os.getenv("MONGODB_DB_NAME", "alphawatch")

        # Redis
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

        # Alert & Relevance Gates
        self.relevance_gate_threshold: float = float(os.getenv("RELEVANCE_GATE_THRESHOLD", "0.3"))
        self.alert_significance_threshold: float = float(os.getenv("ALERT_SIGNIFICANCE_THRESHOLD", "0.6"))

    def __repr__(self) -> str:
        return (
            f"<Settings extraction={self.extraction_model} reasoning={self.reasoning_model} "
            f"kafka={self.kafka_bootstrap_servers} mongo={self.mongodb_db_name}>"
        )


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Singleton getter for application settings."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

"""Kafka producer for processed alert notifications."""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

from .config import get_settings

logger = logging.getLogger(__name__)


def json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for ObjectId and datetime."""
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, (ObjectId,)):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


class AlertProducer:
    """Publishes AI-processed market alerts to the processed-alerts Kafka topic."""

    def __init__(self, bootstrap_servers: Optional[str] = None, topic: Optional[str] = None):
        settings = get_settings()
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.topic = topic or settings.processed_alerts_topic
        self.producer: Optional[Any] = None

    def connect(self):
        """Connect producer to Kafka broker."""
        if not KAFKA_AVAILABLE:
            logger.warning("[Kafka Producer] kafka-python package not installed or unavailable.")
            return

        try:
            logger.info(f"[Kafka Producer] Connecting to {self.bootstrap_servers}...")
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v, default=json_serializer).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                retries=5,
                acks="all"
            )
            logger.info(f"[Kafka Producer] Connected successfully. Target topic: {self.topic}")
        except Exception as e:
            logger.error(f"[Kafka Producer] Connection failed: {e}")
            self.producer = None

    def publish_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Publish an alert to Kafka.

        Expected schema matches processed-alerts contract:
        - articleId (str)
        - tickers (list[str])
        - sentiment ('positive' | 'neutral' | 'negative')
        - sentimentScore (float)
        - significanceScore (float)
        - analysisType (str)
        - comparativeAnalysis (str)
        - alertHeadline (str)
        - alertBody (str)
        - source (str)
        - timestamp (iso str)
        """
        if not self.producer:
            logger.warning("[Kafka Producer] Not connected. Attempting reconnect...")
            self.connect()

        if not self.producer:
            logger.error("[Kafka Producer] Message dropped - producer not available.")
            return False

        try:
            # Format payload
            key = (alert_data.get("tickers") or ["MARKET"])[0]
            future = self.producer.send(self.topic, key=key, value=alert_data)
            # Synchronous wait or flush for guarantee
            future.get(timeout=10)
            logger.info(
                f"[Kafka Producer] Published alert for {alert_data.get('tickers')}: "
                f"\"{alert_data.get('alertHeadline', '')[:50]}...\""
            )
            return True
        except Exception as e:
            logger.error(f"[Kafka Producer] Failed to send alert: {e}")
            return False

    def close(self):
        """Flush and close producer."""
        if self.producer:
            try:
                self.producer.flush(timeout=5)
                self.producer.close()
                logger.info("[Kafka Producer] Disconnected successfully.")
            except Exception as e:
                logger.warning(f"[Kafka Producer] Error closing producer: {e}")
            self.producer = None


_alert_producer: Optional[AlertProducer] = None


def get_alert_producer() -> AlertProducer:
    """Singleton getter for AlertProducer."""
    global _alert_producer
    if _alert_producer is None:
        _alert_producer = AlertProducer()
    return _alert_producer

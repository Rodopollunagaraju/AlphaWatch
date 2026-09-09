"""Kafka consumer for raw news articles feed."""

import json
import logging
import time
from typing import Iterator, Dict, Any, Optional

try:
    from kafka import KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

from .config import get_settings

logger = logging.getLogger(__name__)


class RawNewsConsumer:
    """Consumes raw news articles from Kafka raw-news-feed topic."""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        group_id: Optional[str] = None,
        auto_offset_reset: str = "latest"
    ):
        settings = get_settings()
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.topic = topic or settings.raw_news_topic
        self.group_id = group_id or settings.kafka_consumer_group
        self.auto_offset_reset = auto_offset_reset
        self.consumer: Optional[Any] = None
        self._is_running = False

    def connect(self, max_retries: int = 5, retry_delay: float = 3.0):
        """Connect to Kafka with retry logic."""
        if not KAFKA_AVAILABLE:
            logger.warning("[Kafka Consumer] kafka-python package not installed or unavailable.")
            return

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"[Kafka Consumer] Connecting to {self.bootstrap_servers} "
                    f"(topic: {self.topic}, group: {self.group_id}, attempt {attempt}/{max_retries})..."
                )
                self.consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers.split(","),
                    group_id=self.group_id,
                    auto_offset_reset=self.auto_offset_reset,
                    enable_auto_commit=True,
                    auto_commit_interval_ms=5000,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    consumer_timeout_ms=1000  # unblock poll every 1s for graceful shutdown
                )
                self._is_running = True
                logger.info("[Kafka Consumer] Connected successfully.")
                return
            except Exception as e:
                logger.warning(f"[Kafka Consumer] Connection attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    logger.error("[Kafka Consumer] Could not connect to Kafka after maximum retries.")

    def poll_messages(self) -> Iterator[Dict[str, Any]]:
        """
        Generator yielding incoming messages.
        Returns when consumer is stopped or interrupted.
        """
        if not self.consumer:
            logger.warning("[Kafka Consumer] Consumer is not connected.")
            return

        self._is_running = True
        while self._is_running:
            try:
                msg_batch = self.consumer.poll(timeout_ms=1000)
                for topic_partition, records in msg_batch.items():
                    for record in records:
                        if not self._is_running:
                            break
                        try:
                            val = record.value
                            if isinstance(val, dict):
                                yield val
                            elif isinstance(val, str):
                                yield json.loads(val)
                        except Exception as decode_err:
                            logger.error(f"[Kafka Consumer] Error decoding message: {decode_err}")
            except Exception as poll_err:
                if self._is_running:
                    logger.error(f"[Kafka Consumer] Polling error: {poll_err}")
                    time.sleep(1.0)

    def stop(self):
        """Stop polling and close consumer."""
        self._is_running = False
        if self.consumer:
            try:
                self.consumer.close()
                logger.info("[Kafka Consumer] Gracefully disconnected.")
            except Exception as e:
                logger.warning(f"[Kafka Consumer] Error during close: {e}")
            self.consumer = None

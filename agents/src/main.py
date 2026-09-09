"""AlphaWatch Agent Worker Entry Point.

Runs the Kafka consumption loop, delegating raw news articles
to the Multi-Agent pipeline for extraction, vector retrieval, and RAG reasoning.
"""

import logging
import signal
import sys
import time

from .config import get_settings
from .mongo_client import get_mongo_repo
from .kafka_consumer import RawNewsConsumer
from .kafka_producer import get_alert_producer
from .pipeline import get_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("AlphaWatch-Worker")

# State
is_running = True


def handle_shutdown(signum, frame):
    """Signal handler for graceful worker termination."""
    global is_running
    sig_name = signal.Signals(signum).name
    logger.info(f"[Worker] Received {sig_name}, initiating graceful shutdown...")
    is_running = False


def main():
    """Main execution loop."""
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    settings = get_settings()

    print("\n" + "=" * 50)
    print("  AlphaWatch AI Agent Worker Starting...")
    print("=" * 50)
    print(f"  Kafka Broker:        {settings.kafka_bootstrap_servers}")
    print(f"  Raw News Topic:      {settings.raw_news_topic}")
    print(f"  Processed Alerts:    {settings.processed_alerts_topic}")
    print(f"  MongoDB:             {settings.mongodb_uri}")
    print(f"  Extraction Model:    {settings.extraction_model}")
    print(f"  Reasoning Model:     {settings.reasoning_model}")
    print(f"  Embedding Model:     {settings.embedding_model}")
    print(f"  Relevance Gate:      >= {settings.relevance_gate_threshold}")
    print(f"  Significance Gate:   >= {settings.alert_significance_threshold}")
    print("=" * 50 + "\n")

    # 1. Connect MongoDB repository
    mongo = get_mongo_repo()
    mongo.connect()

    # 2. Connect Kafka Producer
    producer = get_alert_producer()
    producer.connect()

    # 3. Initialize Pipeline
    pipeline = get_pipeline()

    # 4. Connect Kafka Consumer
    consumer = RawNewsConsumer()
    consumer.connect()

    processed_count = 0
    alert_count = 0
    filtered_count = 0

    logger.info("[Worker] Ready and listening for incoming market news events...")

    try:
        for article_msg in consumer.poll_messages():
            if not is_running:
                break

            try:
                result = pipeline.process_article(article_msg)
                processed_count += 1

                if result.get("status") == "filtered":
                    filtered_count += 1
                elif result.get("alert_dispatched"):
                    alert_count += 1

                if processed_count % 10 == 0:
                    logger.info(
                        f"[Worker Stats] Articles: {processed_count} | "
                        f"Alerts Dispatched: {alert_count} | "
                        f"Filtered: {filtered_count}"
                    )
            except Exception as proc_err:
                logger.error(f"[Worker] Error processing article: {proc_err}", exc_info=True)

    except KeyboardInterrupt:
        logger.info("[Worker] Interrupted by user.")
    finally:
        logger.info("[Worker] Shutting down services...")
        consumer.stop()
        producer.close()
        mongo.close()
        logger.info("[Worker] Goodbye.")
        sys.exit(0)


if __name__ == "__main__":
    main()

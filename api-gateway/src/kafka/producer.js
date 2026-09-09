// ============================================
// Kafka Producer
// ============================================
// KafkaJS producer for publishing articles to the raw-news-feed topic.

import { Kafka, CompressionTypes } from 'kafkajs';
import config from '../config/index.js';
import TOPICS from './topics.js';

let kafka = null;
let producer = null;
let isConnected = false;

/**
 * Initialize and connect the Kafka producer.
 */
export async function connectProducer() {
  kafka = new Kafka({
    clientId: config.kafka.clientId,
    brokers: config.kafka.brokers,
    retry: {
      initialRetryTime: 300,
      retries: 10,
    },
  });

  producer = kafka.producer();

  producer.on('producer.connect', () => {
    isConnected = true;
    console.log('[Kafka Producer] Connected');
  });

  producer.on('producer.disconnect', () => {
    isConnected = false;
    console.log('[Kafka Producer] Disconnected');
  });

  await producer.connect();
}

/**
 * Publish an article event to the raw-news-feed topic.
 *
 * @param {Object} article - The article object to publish.
 * @param {string} article.contentHash - SHA-256 hash (used as message key for partitioning).
 * @param {string} article.title - Article title.
 * @param {string} article.content - Article body.
 * @param {string} article.source - Source identifier.
 * @param {string} article.url - Original article URL.
 * @param {string} article.publishedAt - ISO timestamp of publication.
 */
export async function publishArticle(article) {
  if (!producer || !isConnected) {
    console.error('[Kafka Producer] Not connected. Message dropped.');
    return;
  }

  try {
    await producer.send({
      topic: TOPICS.RAW_NEWS_FEED,
      compression: CompressionTypes.GZIP,
      messages: [
        {
          key: article.contentHash,
          value: JSON.stringify({
            ...article,
            ingestedAt: new Date().toISOString(),
          }),
          headers: {
            source: article.source || 'unknown',
          },
        },
      ],
    });

    console.log(`[Kafka Producer] Published: "${article.title?.substring(0, 60)}..."`);
  } catch (err) {
    console.error('[Kafka Producer] Failed to publish:', err.message);
  }
}

/**
 * Gracefully disconnect the producer.
 */
export async function disconnectProducer() {
  if (producer) {
    await producer.disconnect();
    producer = null;
    isConnected = false;
    console.log('[Kafka Producer] Gracefully disconnected');
  }
}

/**
 * Check if the producer is currently connected.
 */
export function isProducerConnected() {
  return isConnected;
}

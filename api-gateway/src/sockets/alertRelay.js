// ============================================
// Kafka Alert Relay — processed-alerts → Redis Pub/Sub
// ============================================
// Consumes from the processed-alerts Kafka topic and
// relays events to Redis Pub/Sub for Socket.io delivery.
// Also persists alerts to MongoDB for history.

import { Kafka } from 'kafkajs';
import { getRedisClient } from '../redis/client.js';
import { Alert } from '../models/index.js';
import config from '../config/index.js';
import TOPICS from '../kafka/topics.js';

let consumer = null;

/**
 * Start consuming from processed-alerts and relay to Redis + MongoDB.
 */
export async function startAlertRelay() {
  const kafka = new Kafka({
    clientId: `${config.kafka.clientId}-alert-relay`,
    brokers: config.kafka.brokers,
    retry: {
      initialRetryTime: 300,
      retries: 10,
    },
  });

  consumer = kafka.consumer({
    groupId: 'alphawatch-alert-relay',
  });

  await consumer.connect();
  await consumer.subscribe({
    topic: TOPICS.PROCESSED_ALERTS,
    fromBeginning: false,
  });

  console.log('[Alert Relay] Consumer connected, listening for processed alerts...');

  await consumer.run({
    eachMessage: async ({ message }) => {
      try {
        const alert = JSON.parse(message.value.toString());
        const redis = getRedisClient();

        // 1. Persist to MongoDB
        await Alert.create({
          articleId: alert.articleId || null,
          tickers: alert.tickers || [],
          sentiment: alert.sentiment,
          sentimentScore: alert.sentimentScore || alert.sentiment_score,
          significanceScore: alert.significanceScore || alert.significance_score,
          analysisType: alert.analysisType || alert.analysis_type,
          comparativeAnalysis: alert.comparativeAnalysis || alert.comparative_analysis,
          alertHeadline: alert.alertHeadline || alert.alert_headline,
          alertBody: alert.alertBody || alert.alert_body,
          source: alert.source,
          timestamp: alert.timestamp ? new Date(alert.timestamp) : new Date(),
        });

        // 2. Publish to Redis Pub/Sub channels
        const alertJson = JSON.stringify(alert);
        await redis.publish('alerts:all', alertJson);

        for (const ticker of alert.tickers || []) {
          await redis.publish(`alerts:${ticker}`, alertJson);
        }

        console.log(
          `[Alert Relay] Relayed alert: "${(alert.alertHeadline || alert.alert_headline || '').substring(0, 50)}..."`
        );
      } catch (err) {
        console.error('[Alert Relay] Error processing message:', err.message);
      }
    },
  });
}

/**
 * Gracefully disconnect the alert relay consumer.
 */
export async function stopAlertRelay() {
  if (consumer) {
    await consumer.disconnect();
    consumer = null;
    console.log('[Alert Relay] Disconnected');
  }
}

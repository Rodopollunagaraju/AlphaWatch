// ============================================
// AlphaWatch API Gateway — Configuration
// ============================================

import dotenv from 'dotenv';
dotenv.config();

const config = {
  // Server
  port: parseInt(process.env.API_PORT || '3001', 10),
  nodeEnv: process.env.NODE_ENV || 'development',

  // Kafka
  kafka: {
    brokers: (process.env.KAFKA_BOOTSTRAP_SERVERS || 'localhost:29092').split(','),
    clientId: process.env.KAFKA_CLIENT_ID || 'alphawatch-api',
    topics: {
      rawNewsFeed: 'raw-news-feed',
      processedAlerts: 'processed-alerts',
    },
  },

  // Redis
  redis: {
    url: process.env.REDIS_URL || 'redis://localhost:6379',
  },

  // MongoDB
  mongo: {
    uri: process.env.MONGODB_URI || 'mongodb://localhost:27017/alphawatch',
    dbName: process.env.MONGODB_DB_NAME || 'alphawatch',
  },

  // News APIs
  newsapi: {
    key: process.env.NEWSAPI_KEY || '',
    rateLimit: parseInt(process.env.NEWSAPI_RATE_LIMIT || '100', 10),
    rateWindowSeconds: parseInt(process.env.NEWSAPI_RATE_WINDOW_SECONDS || '86400', 10),
    fetchIntervalMs: parseInt(process.env.NEWSAPI_FETCH_INTERVAL_MS || '120000', 10),
  },

  // RSS
  rss: {
    fetchIntervalMs: parseInt(process.env.RSS_FETCH_INTERVAL_MS || '60000', 10),
  },

  // Dedup
  dedup: {
    ttlSeconds: parseInt(process.env.DEDUP_TTL_SECONDS || '86400', 10),
  },
};

export default config;

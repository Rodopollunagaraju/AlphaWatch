// ============================================
// Health Check Route
// ============================================

import { Router } from 'express';
import mongoose from 'mongoose';
import { getRedisClient } from '../redis/client.js';
import { isProducerConnected } from '../kafka/producer.js';

const router = Router();

/**
 * GET /api/health
 * Returns the health status of all dependent services.
 */
router.get('/health', async (req, res) => {
  const checks = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    services: {},
  };

  // MongoDB
  try {
    const mongoState = mongoose.connection.readyState;
    checks.services.mongodb = {
      status: mongoState === 1 ? 'connected' : 'disconnected',
      readyState: mongoState,
    };
  } catch {
    checks.services.mongodb = { status: 'error' };
  }

  // Redis
  try {
    const redis = getRedisClient();
    const pong = await redis.ping();
    checks.services.redis = {
      status: pong === 'PONG' ? 'connected' : 'disconnected',
    };
  } catch {
    checks.services.redis = { status: 'error' };
  }

  // Kafka
  checks.services.kafka = {
    status: isProducerConnected() ? 'connected' : 'disconnected',
  };

  // Overall status
  const allHealthy = Object.values(checks.services).every(
    (s) => s.status === 'connected'
  );
  checks.status = allHealthy ? 'ok' : 'degraded';

  const statusCode = allHealthy ? 200 : 503;
  res.status(statusCode).json(checks);
});

export default router;

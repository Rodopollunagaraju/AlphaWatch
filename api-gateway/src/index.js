// ============================================
// AlphaWatch API Gateway — Entry Point
// ============================================
// Express server that orchestrates:
// - REST API endpoints
// - RSS/News fetchers → Redis dedup → Kafka producer
// - Socket.io server for real-time alert delivery
// - Kafka consumer relay (processed-alerts → Redis Pub/Sub)

import express from 'express';
import cors from 'cors';
import { createServer } from 'http';
import mongoose from 'mongoose';
import config from './config/index.js';

// Routes
import healthRouter from './routes/health.js';
import feedsRouter from './routes/feeds.js';
import monitorsRouter from './routes/monitors.js';
import alertsRouter from './routes/alerts.js';

// Infrastructure
import { getRedisClient, disconnectRedis } from './redis/client.js';
import { connectProducer, disconnectProducer } from './kafka/producer.js';

// Fetchers
import { startRSSFetcher, stopRSSFetcher } from './fetchers/rss.js';
import { startNewsAPIFetcher, stopNewsAPIFetcher } from './fetchers/newsapi.js';

// Sockets
import { initSocketServer } from './sockets/index.js';
import { startAlertRelay, stopAlertRelay } from './sockets/alertRelay.js';

// ── Express App ────────────────────────────────────────
const app = express();
const httpServer = createServer(app);

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logging (simple)
app.use((req, _res, next) => {
  if (req.path !== '/api/health') {
    console.log(`[API] ${req.method} ${req.path}`);
  }
  next();
});

// Routes
app.use('/api', healthRouter);
app.use('/api', feedsRouter);
app.use('/api', monitorsRouter);
app.use('/api', alertsRouter);

// 404 handler
app.use((_req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Error handler
app.use((err, _req, res, _next) => {
  console.error('[API] Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// ── Startup Sequence ───────────────────────────────────
async function start() {
  console.log('');
  console.log('══════════════════════════════════════════');
  console.log('  AlphaWatch API Gateway Starting...');
  console.log('══════════════════════════════════════════');
  console.log('');

  try {
    // 1. Connect to MongoDB
    console.log('[Startup] Connecting to MongoDB...');
    await mongoose.connect(config.mongo.uri, {
      dbName: config.mongo.dbName,
    });
    console.log('[Startup] ✓ MongoDB connected');

    // 2. Initialize Redis (connection is eager via the singleton)
    console.log('[Startup] Connecting to Redis...');
    getRedisClient();
    console.log('[Startup] ✓ Redis connected');

    // 3. Connect Kafka producer
    console.log('[Startup] Connecting Kafka producer...');
    await connectProducer();
    console.log('[Startup] ✓ Kafka producer connected');

    // 4. Initialize Socket.io
    console.log('[Startup] Initializing Socket.io...');
    initSocketServer(httpServer);
    console.log('[Startup] ✓ Socket.io initialized');

    // 5. Start alert relay (Kafka consumer → Redis Pub/Sub)
    console.log('[Startup] Starting alert relay...');
    await startAlertRelay().catch((err) => {
      // Non-fatal: alert relay failing shouldn't prevent startup
      console.warn('[Startup] ⚠ Alert relay failed to start:', err.message);
      console.warn('[Startup]   (Will retry on next processed-alerts message)');
    });

    // 6. Start HTTP server
    httpServer.listen(config.port, () => {
      console.log('');
      console.log('══════════════════════════════════════════');
      console.log(`  AlphaWatch API Gateway listening`);
      console.log(`  HTTP:      http://localhost:${config.port}`);
      console.log(`  Health:    http://localhost:${config.port}/api/health`);
      console.log(`  Socket.io: ws://localhost:${config.port}`);
      console.log('══════════════════════════════════════════');
      console.log('');
    });

    // 7. Start fetchers (after server is listening)
    console.log('[Startup] Starting news fetchers...');
    startRSSFetcher();
    startNewsAPIFetcher();
    console.log('[Startup] ✓ Fetchers started');
  } catch (err) {
    console.error('[Startup] Fatal error:', err);
    process.exit(1);
  }
}

// ── Graceful Shutdown ──────────────────────────────────
async function shutdown(signal) {
  console.log(`\n[Shutdown] Received ${signal}, shutting down gracefully...`);

  // Stop fetchers first (no new data)
  stopRSSFetcher();
  stopNewsAPIFetcher();

  // Stop alert relay
  await stopAlertRelay().catch(() => {});

  // Close HTTP server (stops accepting new connections)
  httpServer.close();

  // Disconnect infrastructure
  await disconnectProducer().catch(() => {});
  await disconnectRedis().catch(() => {});
  await mongoose.disconnect().catch(() => {});

  console.log('[Shutdown] Goodbye.');
  process.exit(0);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

// ── Start ──────────────────────────────────────────────
start();

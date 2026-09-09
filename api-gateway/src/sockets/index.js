// ============================================
// Socket.io Server Setup
// ============================================
// Manages WebSocket connections for real-time alert delivery.
// Subscribes to Redis Pub/Sub for alert relay from Kafka consumers.
//
// Full implementation in Day 3 — this is the structural skeleton.

import { Server as SocketIOServer } from 'socket.io';
import Redis from 'ioredis';
import config from '../config/index.js';

let io = null;

/**
 * Initialize Socket.io server and Redis Pub/Sub subscriber.
 *
 * @param {import('http').Server} httpServer - The HTTP server instance.
 * @returns {SocketIOServer} The Socket.io server instance.
 */
export function initSocketServer(httpServer) {
  io = new SocketIOServer(httpServer, {
    cors: {
      origin: '*',
      methods: ['GET', 'POST'],
    },
    pingInterval: 25000,
    pingTimeout: 60000,
  });

  // ── Redis Pub/Sub Subscriber ─────────────────────────
  const redisSubscriber = new Redis(config.redis.url);

  redisSubscriber.psubscribe('alerts:*', (err) => {
    if (err) {
      console.error('[Socket.io] Failed to subscribe to Redis alerts:', err.message);
    } else {
      console.log('[Socket.io] Subscribed to Redis alerts:* channels');
    }
  });

  redisSubscriber.on('pmessage', (_pattern, channel, message) => {
    try {
      const alert = JSON.parse(message);
      const target = channel.replace('alerts:', '');

      // Emit to the specific ticker room
      if (target !== 'all') {
        io.to(target).emit('new-alert', alert);
      }

      // Emit to the global feed room
      io.to('global-feed').emit('new-alert', alert);
    } catch (err) {
      console.error('[Socket.io] Error processing Redis message:', err.message);
    }
  });

  // ── Connection Handling ──────────────────────────────
  io.on('connection', (socket) => {
    console.log(`[Socket.io] Client connected: ${socket.id}`);

    // Every client joins the global feed
    socket.join('global-feed');

    // Client subscribes to specific tickers
    socket.on('subscribe-tickers', (tickers) => {
      if (Array.isArray(tickers)) {
        tickers.forEach((ticker) => {
          const room = ticker.toUpperCase().trim();
          socket.join(room);
          console.log(`[Socket.io] ${socket.id} joined room: ${room}`);
        });
      }
    });

    // Client unsubscribes from tickers
    socket.on('unsubscribe-tickers', (tickers) => {
      if (Array.isArray(tickers)) {
        tickers.forEach((ticker) => {
          socket.leave(ticker.toUpperCase().trim());
        });
      }
    });

    socket.on('disconnect', (reason) => {
      console.log(`[Socket.io] Client disconnected: ${socket.id} (${reason})`);
    });
  });

  console.log('[Socket.io] Server initialized');
  return io;
}

/**
 * Get the Socket.io server instance.
 */
export function getIO() {
  return io;
}

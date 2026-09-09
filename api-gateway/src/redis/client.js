// ============================================
// Redis Client Singleton
// ============================================

import Redis from 'ioredis';
import config from '../config/index.js';

let redisClient = null;

/**
 * Get or create the Redis client singleton.
 * @returns {Redis} The ioredis client instance.
 */
export function getRedisClient() {
  if (!redisClient) {
    redisClient = new Redis(config.redis.url, {
      maxRetriesPerRequest: 3,
      retryStrategy(times) {
        const delay = Math.min(times * 200, 5000);
        console.log(`[Redis] Reconnecting in ${delay}ms (attempt ${times})`);
        return delay;
      },
      lazyConnect: false,
    });

    redisClient.on('connect', () => {
      console.log('[Redis] Connected');
    });

    redisClient.on('error', (err) => {
      console.error('[Redis] Connection error:', err.message);
    });
  }

  return redisClient;
}

/**
 * Gracefully disconnect Redis.
 */
export async function disconnectRedis() {
  if (redisClient) {
    await redisClient.quit();
    redisClient = null;
    console.log('[Redis] Disconnected');
  }
}

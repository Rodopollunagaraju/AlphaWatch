// ============================================
// Redis Rate Limiter
// ============================================
// Fixed-window rate limiter using Redis INCR + EXPIRE.
// Prevents quota exhaustion on third-party news APIs.

import { getRedisClient } from './client.js';

/**
 * Check if a rate limit has been exceeded for a given key.
 * Uses a fixed-window approach: one counter per time window.
 *
 * @param {string} apiName - Identifier for the API (e.g., 'newsapi').
 * @param {number} maxRequests - Maximum requests allowed in the window.
 * @param {number} windowSeconds - Window duration in seconds.
 * @returns {Promise<{allowed: boolean, remaining: number, current: number}>}
 */
export async function checkRateLimit(apiName, maxRequests, windowSeconds) {
  const redis = getRedisClient();
  const windowKey = Math.floor(Date.now() / (windowSeconds * 1000));
  const key = `ratelimit:${apiName}:${windowKey}`;

  try {
    const current = await redis.incr(key);

    // Set expiry on first increment only
    if (current === 1) {
      await redis.expire(key, windowSeconds);
    }

    const allowed = current <= maxRequests;
    const remaining = Math.max(0, maxRequests - current);

    if (!allowed) {
      console.warn(`[RateLimit] ${apiName} limit exceeded: ${current}/${maxRequests}`);
    }

    return { allowed, remaining, current };
  } catch (err) {
    // If Redis is down, allow the request (fail-open)
    console.error('[RateLimit] Redis error, allowing request:', err.message);
    return { allowed: true, remaining: maxRequests, current: 0 };
  }
}

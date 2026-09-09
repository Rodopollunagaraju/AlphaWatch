// ============================================
// Redis Content Deduplication
// ============================================
// Uses SHA-256 hash of article content as a Redis key with TTL.
// If the key exists, the article is a duplicate within the TTL window.

import crypto from 'crypto';
import { getRedisClient } from './client.js';
import config from '../config/index.js';

/**
 * Generate a SHA-256 hash of the article's content for dedup.
 * Combines title + content to catch syndicated articles with different URLs.
 *
 * @param {Object} article - The article object.
 * @param {string} article.title - Article title.
 * @param {string} article.content - Article body content.
 * @returns {string} Hex-encoded SHA-256 hash.
 */
export function hashArticle(article) {
  const payload = `${(article.title || '').trim()}|${(article.content || '').trim()}`;
  return crypto.createHash('sha256').update(payload).digest('hex');
}

/**
 * Check if an article is a duplicate using Redis.
 * If not a duplicate, sets the hash key with a TTL to mark it as seen.
 *
 * @param {Object} article - The article object with title and content.
 * @returns {Promise<{isDuplicate: boolean, hash: string}>}
 */
export async function checkDuplicate(article) {
  const redis = getRedisClient();
  const hash = hashArticle(article);
  const key = `dedup:${hash}`;

  try {
    const exists = await redis.get(key);

    if (exists) {
      return { isDuplicate: true, hash };
    }

    // Mark as seen with TTL
    await redis.set(key, '1', 'EX', config.dedup.ttlSeconds);
    return { isDuplicate: false, hash };
  } catch (err) {
    // If Redis is down, allow the article through (fail-open)
    console.error('[Dedup] Redis error, allowing article through:', err.message);
    return { isDuplicate: false, hash };
  }
}

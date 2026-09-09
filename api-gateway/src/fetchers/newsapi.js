// ============================================
// News API Fetcher (NewsAPI.org)
// ============================================
// Fetches financial news via the NewsAPI.org REST API,
// rate-limited via Redis, deduplicated, and published to Kafka.

import axios from 'axios';
import { Monitor } from '../models/index.js';
import { checkDuplicate } from '../redis/dedup.js';
import { checkRateLimit } from '../redis/rateLimit.js';
import { publishArticle } from '../kafka/producer.js';
import config from '../config/index.js';

let fetchInterval = null;

/**
 * Fetch news from NewsAPI for all active monitor tickers.
 */
async function fetchNewsAPI() {
  if (!config.newsapi.key) {
    // Silently skip if no API key configured
    return;
  }

  try {
    // Check rate limit before making API calls
    const { allowed, remaining } = await checkRateLimit(
      'newsapi',
      config.newsapi.rateLimit,
      config.newsapi.rateWindowSeconds
    );

    if (!allowed) {
      console.log('[NewsAPI] Rate limit reached, skipping this cycle');
      return;
    }

    // Get unique tickers from all active monitors
    const monitors = await Monitor.find({ active: true }).lean();
    const tickers = [...new Set(monitors.flatMap((m) => m.tickers))];

    if (tickers.length === 0) {
      console.log('[NewsAPI] No active monitors with tickers, skipping');
      return;
    }

    // Build query from tickers (e.g., "AAPL OR MSFT OR TSLA")
    const query = tickers.slice(0, 10).join(' OR ');

    console.log(`[NewsAPI] Fetching news for: ${query} (${remaining} requests remaining)`);

    const response = await axios.get('https://newsapi.org/v2/everything', {
      params: {
        q: query,
        language: 'en',
        sortBy: 'publishedAt',
        pageSize: 20,
        apiKey: config.newsapi.key,
      },
      timeout: 15000,
    });

    const articles = response.data?.articles || [];
    let published = 0;
    let duplicates = 0;

    for (const item of articles) {
      const article = normalizeNewsAPIItem(item);

      const { isDuplicate, hash } = await checkDuplicate(article);
      if (isDuplicate) {
        duplicates++;
        continue;
      }

      article.contentHash = hash;
      await publishArticle(article);
      published++;
    }

    console.log(
      `[NewsAPI] Cycle complete: ${published} published, ${duplicates} duplicates skipped`
    );
  } catch (err) {
    if (err.response?.status === 429) {
      console.warn('[NewsAPI] HTTP 429 — rate limited by provider');
    } else {
      console.error('[NewsAPI] Fetch error:', err.message);
    }
  }
}

/**
 * Normalize a NewsAPI article into our standard format.
 */
function normalizeNewsAPIItem(item) {
  return {
    title: (item.title || 'Untitled').trim(),
    content: (item.content || item.description || item.title || '').trim(),
    url: item.url || '',
    source: item.source?.name || 'newsapi',
    sourceCategory: 'news-api',
    publishedAt: item.publishedAt || new Date().toISOString(),
    author: item.author || null,
    imageUrl: item.urlToImage || null,
  };
}

/**
 * Start the NewsAPI fetcher on a recurring interval.
 */
export function startNewsAPIFetcher() {
  if (!config.newsapi.key) {
    console.log('[NewsAPI] No API key configured, fetcher disabled');
    return;
  }

  const intervalMs = config.newsapi.fetchIntervalMs;
  console.log(`[NewsAPI] Starting with interval ${intervalMs}ms`);

  // Run immediately
  fetchNewsAPI();

  // Then on interval
  fetchInterval = setInterval(fetchNewsAPI, intervalMs);
}

/**
 * Stop the NewsAPI fetcher.
 */
export function stopNewsAPIFetcher() {
  if (fetchInterval) {
    clearInterval(fetchInterval);
    fetchInterval = null;
    console.log('[NewsAPI] Stopped');
  }
}

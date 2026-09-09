// ============================================
// RSS Feed Fetcher
// ============================================
// Polls configured RSS feed URLs on an interval, normalizes items,
// deduplicates via Redis, and publishes to Kafka.

import RSSParser from 'rss-parser';
import { Feed } from '../models/index.js';
import { checkDuplicate, hashArticle } from '../redis/dedup.js';
import { publishArticle } from '../kafka/producer.js';
import config from '../config/index.js';

const parser = new RSSParser({
  timeout: 15000,
  headers: {
    'User-Agent': 'AlphaWatch/1.0 (Market Intelligence Platform)',
  },
});

let fetchInterval = null;

/**
 * Fetch and process all active RSS feeds.
 */
async function fetchAllRSSFeeds() {
  try {
    const feeds = await Feed.find({ type: 'rss', active: true }).lean();

    if (feeds.length === 0) {
      console.log('[RSS Fetcher] No active RSS feeds configured');
      return;
    }

    console.log(`[RSS Fetcher] Fetching ${feeds.length} feeds...`);

    const results = await Promise.allSettled(
      feeds.map((feed) => fetchSingleFeed(feed))
    );

    let totalPublished = 0;
    let totalDuplicates = 0;
    let totalErrors = 0;

    for (const result of results) {
      if (result.status === 'fulfilled') {
        totalPublished += result.value.published;
        totalDuplicates += result.value.duplicates;
      } else {
        totalErrors++;
      }
    }

    console.log(
      `[RSS Fetcher] Cycle complete: ${totalPublished} published, ${totalDuplicates} duplicates skipped, ${totalErrors} feed errors`
    );
  } catch (err) {
    console.error('[RSS Fetcher] Fatal error during fetch cycle:', err.message);
  }
}

/**
 * Fetch a single RSS feed and process its items.
 *
 * @param {Object} feed - The feed document from MongoDB.
 * @returns {Promise<{published: number, duplicates: number}>}
 */
async function fetchSingleFeed(feed) {
  let published = 0;
  let duplicates = 0;

  try {
    const result = await parser.parseURL(feed.url);

    for (const item of result.items || []) {
      const article = normalizeRSSItem(item, feed);

      // Dedup check
      const { isDuplicate, hash } = await checkDuplicate(article);
      if (isDuplicate) {
        duplicates++;
        continue;
      }

      article.contentHash = hash;

      // Publish to Kafka
      await publishArticle(article);
      published++;
    }

    // Update last fetched timestamp
    await Feed.updateOne(
      { _id: feed._id },
      { lastFetchedAt: new Date(), errorCount: 0 }
    );
  } catch (err) {
    console.error(`[RSS Fetcher] Error fetching "${feed.name}":`, err.message);

    // Track errors — disable feed after 10 consecutive failures
    await Feed.updateOne(
      { _id: feed._id },
      {
        $inc: { errorCount: 1 },
        ...(feed.errorCount >= 9 ? { active: false } : {}),
      }
    );
  }

  return { published, duplicates };
}

/**
 * Normalize an RSS item into our standard article format.
 */
function normalizeRSSItem(item, feed) {
  const content =
    item.contentSnippet ||
    item.content ||
    item.summary ||
    item.description ||
    item.title ||
    '';

  return {
    title: (item.title || 'Untitled').trim(),
    content: content.trim(),
    url: item.link || item.guid || '',
    source: feed.name || 'rss',
    sourceCategory: feed.category || 'general',
    publishedAt: item.pubDate
      ? new Date(item.pubDate).toISOString()
      : new Date().toISOString(),
  };
}

/**
 * Start the RSS fetcher on a recurring interval.
 */
export function startRSSFetcher() {
  const intervalMs = config.rss.fetchIntervalMs;
  console.log(`[RSS Fetcher] Starting with interval ${intervalMs}ms`);

  // Run immediately on startup
  fetchAllRSSFeeds();

  // Then run on interval
  fetchInterval = setInterval(fetchAllRSSFeeds, intervalMs);
}

/**
 * Stop the RSS fetcher.
 */
export function stopRSSFetcher() {
  if (fetchInterval) {
    clearInterval(fetchInterval);
    fetchInterval = null;
    console.log('[RSS Fetcher] Stopped');
  }
}

// ============================================
// AlphaWatch — MongoDB Initialization Script
// ============================================
// This runs automatically on first container startup via
// /docker-entrypoint-initdb.d mount.

db = db.getSiblingDB('alphawatch');

// ── Articles Collection ──────────────────────────────────
db.createCollection('articles');

// Unique index on content hash to prevent duplicates at the DB level
db.articles.createIndex({ contentHash: 1 }, { unique: true });

// Compound index for ticker-based queries with time ordering
db.articles.createIndex({ 'extraction.tickers': 1, createdAt: -1 });

// TTL index — auto-delete articles older than 180 days (optional)
// Remove or adjust if you want to keep all historical data
// db.articles.createIndex({ createdAt: 1 }, { expireAfterSeconds: 15552000 });

// Text index for basic search (fallback if vector search not available)
db.articles.createIndex({ title: 'text', 'extraction.summary': 'text' });

print('✓ Created articles collection with indexes');

// ── Monitors Collection ──────────────────────────────────
db.createCollection('monitors');

// Index on tickers for fast watchlist lookups
db.monitors.createIndex({ tickers: 1 });

// Index on active status
db.monitors.createIndex({ active: 1 });

print('✓ Created monitors collection with indexes');

// ── Alerts Collection ────────────────────────────────────
db.createCollection('alerts');

// Compound index for querying alerts by ticker and time
db.alerts.createIndex({ tickers: 1, timestamp: -1 });

// Index for pagination by timestamp
db.alerts.createIndex({ timestamp: -1 });

// Index for significance-based queries
db.alerts.createIndex({ significanceScore: -1 });

print('✓ Created alerts collection with indexes');

// ── Feeds Collection (RSS/API source configs) ────────────
db.createCollection('feeds');

db.feeds.createIndex({ url: 1 }, { unique: true });
db.feeds.createIndex({ active: 1, type: 1 });

// Seed some default RSS feeds
db.feeds.insertMany([
  {
    name: 'Yahoo Finance - Market News',
    url: 'https://finance.yahoo.com/news/rssindex',
    type: 'rss',
    active: true,
    category: 'market',
    createdAt: new Date()
  },
  {
    name: 'Google News - Business',
    url: 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB',
    type: 'rss',
    active: true,
    category: 'business',
    createdAt: new Date()
  },
  {
    name: 'SEC EDGAR - Company Filings',
    url: 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&dateb=&owner=include&count=40&search_text=&start=0&output=atom',
    type: 'rss',
    active: true,
    category: 'filings',
    createdAt: new Date()
  },
  {
    name: 'CNBC - Top News',
    url: 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114',
    type: 'rss',
    active: true,
    category: 'market',
    createdAt: new Date()
  }
]);

print('✓ Created feeds collection with default RSS sources');
print('');
print('══════════════════════════════════════════');
print('  AlphaWatch MongoDB initialized ✓');
print('══════════════════════════════════════════');

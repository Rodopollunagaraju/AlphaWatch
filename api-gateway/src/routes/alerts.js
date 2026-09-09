// ============================================
// Alert Routes — Read/Query Alerts
// ============================================

import { Router } from 'express';
import { Alert } from '../models/index.js';

const router = Router();

/**
 * GET /api/alerts
 * Paginated list of alerts, newest first.
 * Query params: ?page=1&limit=20&ticker=AAPL&minSignificance=0.5
 */
router.get('/alerts', async (req, res) => {
  try {
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '20', 10)));
    const skip = (page - 1) * limit;

    const filter = {};
    if (req.query.ticker) {
      filter.tickers = req.query.ticker.toUpperCase();
    }
    if (req.query.minSignificance) {
      filter.significanceScore = {
        $gte: parseFloat(req.query.minSignificance),
      };
    }

    const [alerts, total] = await Promise.all([
      Alert.find(filter).sort({ timestamp: -1 }).skip(skip).limit(limit).lean(),
      Alert.countDocuments(filter),
    ]);

    res.json({
      alerts,
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit),
      },
    });
  } catch (err) {
    console.error('[Alerts] List error:', err.message);
    res.status(500).json({ error: 'Failed to list alerts' });
  }
});

/**
 * GET /api/alerts/stats
 * Aggregate alert statistics.
 */
router.get('/alerts/stats', async (req, res) => {
  try {
    const now = new Date();
    const last24h = new Date(now - 24 * 60 * 60 * 1000);
    const last7d = new Date(now - 7 * 24 * 60 * 60 * 1000);

    const [totalAlerts, last24hCount, last7dCount, byTicker, bySentiment, avgSignificance] =
      await Promise.all([
        Alert.countDocuments(),
        Alert.countDocuments({ timestamp: { $gte: last24h } }),
        Alert.countDocuments({ timestamp: { $gte: last7d } }),
        Alert.aggregate([
          { $unwind: '$tickers' },
          { $group: { _id: '$tickers', count: { $sum: 1 } } },
          { $sort: { count: -1 } },
          { $limit: 10 },
        ]),
        Alert.aggregate([
          { $group: { _id: '$sentiment', count: { $sum: 1 } } },
        ]),
        Alert.aggregate([
          {
            $group: {
              _id: null,
              avgScore: { $avg: '$significanceScore' },
            },
          },
        ]),
      ]);

    res.json({
      stats: {
        totalAlerts,
        last24h: last24hCount,
        last7d: last7dCount,
        avgSignificanceScore: avgSignificance[0]?.avgScore || 0,
        topTickers: byTicker.map((t) => ({
          ticker: t._id,
          count: t.count,
        })),
        sentimentDistribution: bySentiment.reduce(
          (acc, s) => ({ ...acc, [s._id || 'unknown']: s.count }),
          {}
        ),
      },
    });
  } catch (err) {
    console.error('[Alerts] Stats error:', err.message);
    res.status(500).json({ error: 'Failed to get alert stats' });
  }
});

/**
 * GET /api/articles
 * List recent processed articles (from MongoDB, not Kafka).
 * Query params: ?page=1&limit=20&ticker=AAPL
 */
router.get('/articles', async (req, res) => {
  try {
    // Dynamic import to avoid circular dependency
    const { Article } = await import('../models/index.js');

    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '20', 10)));
    const skip = (page - 1) * limit;

    const filter = {};
    if (req.query.ticker) {
      filter['extraction.tickers'] = req.query.ticker.toUpperCase();
    }

    const [articles, total] = await Promise.all([
      Article.find(filter)
        .select('-embedding -content')
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(limit)
        .lean(),
      Article.countDocuments(filter),
    ]);

    res.json({
      articles,
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit),
      },
    });
  } catch (err) {
    console.error('[Articles] List error:', err.message);
    res.status(500).json({ error: 'Failed to list articles' });
  }
});

export default router;

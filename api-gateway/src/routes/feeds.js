// ============================================
// Feeds Routes — CRUD for RSS/API Sources
// ============================================

import { Router } from 'express';
import { Feed } from '../models/index.js';

const router = Router();

/**
 * GET /api/feeds
 * List all configured feed sources.
 * Query params: ?active=true|false, ?type=rss|api
 */
router.get('/feeds', async (req, res) => {
  try {
    const filter = {};
    if (req.query.active !== undefined) {
      filter.active = req.query.active === 'true';
    }
    if (req.query.type) {
      filter.type = req.query.type;
    }

    const feeds = await Feed.find(filter)
      .sort({ createdAt: -1 })
      .lean();

    res.json({ feeds, total: feeds.length });
  } catch (err) {
    console.error('[Feeds] List error:', err.message);
    res.status(500).json({ error: 'Failed to list feeds' });
  }
});

/**
 * POST /api/feeds
 * Add a new feed source.
 * Body: { name, url, type: "rss"|"api", category? }
 */
router.post('/feeds', async (req, res) => {
  try {
    const { name, url, type, category } = req.body;

    if (!name || !url || !type) {
      return res.status(400).json({
        error: 'Missing required fields: name, url, type',
      });
    }

    if (!['rss', 'api'].includes(type)) {
      return res.status(400).json({
        error: 'type must be "rss" or "api"',
      });
    }

    // Check for duplicate URL
    const existing = await Feed.findOne({ url });
    if (existing) {
      return res.status(409).json({
        error: 'A feed with this URL already exists',
        feed: existing,
      });
    }

    const feed = await Feed.create({
      name,
      url,
      type,
      category: category || 'general',
      active: true,
    });

    res.status(201).json({ feed });
  } catch (err) {
    console.error('[Feeds] Create error:', err.message);
    res.status(500).json({ error: 'Failed to create feed' });
  }
});

/**
 * PATCH /api/feeds/:id
 * Update a feed (e.g., toggle active, change name).
 */
router.patch('/feeds/:id', async (req, res) => {
  try {
    const { name, active, category } = req.body;
    const update = {};
    if (name !== undefined) update.name = name;
    if (active !== undefined) update.active = active;
    if (category !== undefined) update.category = category;

    const feed = await Feed.findByIdAndUpdate(req.params.id, update, {
      new: true,
    });

    if (!feed) {
      return res.status(404).json({ error: 'Feed not found' });
    }

    res.json({ feed });
  } catch (err) {
    console.error('[Feeds] Update error:', err.message);
    res.status(500).json({ error: 'Failed to update feed' });
  }
});

/**
 * DELETE /api/feeds/:id
 * Remove a feed source.
 */
router.delete('/feeds/:id', async (req, res) => {
  try {
    const feed = await Feed.findByIdAndDelete(req.params.id);

    if (!feed) {
      return res.status(404).json({ error: 'Feed not found' });
    }

    res.json({ message: 'Feed deleted', feed });
  } catch (err) {
    console.error('[Feeds] Delete error:', err.message);
    res.status(500).json({ error: 'Failed to delete feed' });
  }
});

export default router;

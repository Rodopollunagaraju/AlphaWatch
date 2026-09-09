// ============================================
// Monitor Routes — CRUD for Watchlists
// ============================================

import { Router } from 'express';
import { Monitor } from '../models/index.js';

const router = Router();

/**
 * GET /api/monitors
 * List all monitors (watchlist rules).
 * Query params: ?active=true|false
 */
router.get('/monitors', async (req, res) => {
  try {
    const filter = {};
    if (req.query.active !== undefined) {
      filter.active = req.query.active === 'true';
    }

    const monitors = await Monitor.find(filter)
      .sort({ createdAt: -1 })
      .lean();

    res.json({ monitors, total: monitors.length });
  } catch (err) {
    console.error('[Monitors] List error:', err.message);
    res.status(500).json({ error: 'Failed to list monitors' });
  }
});

/**
 * POST /api/monitors
 * Create a new monitor.
 * Body: { name, tickers: [...], keywords?: [...], sentimentThreshold?, categories?: [...] }
 */
router.post('/monitors', async (req, res) => {
  try {
    const { name, tickers, keywords, sentimentThreshold, categories } = req.body;

    if (!name || !tickers || !Array.isArray(tickers) || tickers.length === 0) {
      return res.status(400).json({
        error: 'Missing required fields: name, tickers (non-empty array)',
      });
    }

    // Normalize tickers to uppercase
    const normalizedTickers = tickers.map((t) => t.toUpperCase().trim());

    const monitor = await Monitor.create({
      name,
      tickers: normalizedTickers,
      keywords: keywords || [],
      sentimentThreshold: sentimentThreshold ?? 0.5,
      categories: categories || [],
      active: true,
    });

    res.status(201).json({ monitor });
  } catch (err) {
    console.error('[Monitors] Create error:', err.message);
    res.status(500).json({ error: 'Failed to create monitor' });
  }
});

/**
 * GET /api/monitors/:id
 * Get a single monitor by ID.
 */
router.get('/monitors/:id', async (req, res) => {
  try {
    const monitor = await Monitor.findById(req.params.id).lean();

    if (!monitor) {
      return res.status(404).json({ error: 'Monitor not found' });
    }

    res.json({ monitor });
  } catch (err) {
    console.error('[Monitors] Get error:', err.message);
    res.status(500).json({ error: 'Failed to get monitor' });
  }
});

/**
 * PATCH /api/monitors/:id
 * Update a monitor.
 */
router.patch('/monitors/:id', async (req, res) => {
  try {
    const { name, tickers, keywords, sentimentThreshold, categories, active } =
      req.body;

    const update = {};
    if (name !== undefined) update.name = name;
    if (tickers !== undefined)
      update.tickers = tickers.map((t) => t.toUpperCase().trim());
    if (keywords !== undefined) update.keywords = keywords;
    if (sentimentThreshold !== undefined)
      update.sentimentThreshold = sentimentThreshold;
    if (categories !== undefined) update.categories = categories;
    if (active !== undefined) update.active = active;

    const monitor = await Monitor.findByIdAndUpdate(req.params.id, update, {
      new: true,
    });

    if (!monitor) {
      return res.status(404).json({ error: 'Monitor not found' });
    }

    res.json({ monitor });
  } catch (err) {
    console.error('[Monitors] Update error:', err.message);
    res.status(500).json({ error: 'Failed to update monitor' });
  }
});

/**
 * DELETE /api/monitors/:id
 * Delete a monitor.
 */
router.delete('/monitors/:id', async (req, res) => {
  try {
    const monitor = await Monitor.findByIdAndDelete(req.params.id);

    if (!monitor) {
      return res.status(404).json({ error: 'Monitor not found' });
    }

    res.json({ message: 'Monitor deleted', monitor });
  } catch (err) {
    console.error('[Monitors] Delete error:', err.message);
    res.status(500).json({ error: 'Failed to delete monitor' });
  }
});

export default router;

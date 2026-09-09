// ============================================
// Mongoose Models
// ============================================

import mongoose from 'mongoose';

// ── Article Schema ───────────────────────────────────────
const articleSchema = new mongoose.Schema(
  {
    contentHash: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    title: { type: String, required: true },
    content: { type: String, required: true },
    url: { type: String },
    source: { type: String, required: true },
    publishedAt: { type: Date },
    ingestedAt: { type: Date, default: Date.now },

    // Populated by the extraction agent (Day 2)
    extraction: {
      tickers: [String],
      sentiment: { type: String, enum: ['positive', 'neutral', 'negative'] },
      sentimentScore: { type: Number, min: 0, max: 1 },
      category: { type: String },
      summary: { type: String },
    },

    // Vector embedding for RAG (Day 2)
    embedding: { type: [Number] },
  },
  {
    timestamps: true,
    collection: 'articles',
  }
);

// ── Monitor Schema ───────────────────────────────────────
const monitorSchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    tickers: { type: [String], required: true, index: true },
    keywords: [String],
    sentimentThreshold: {
      type: Number,
      default: 0.5,
      min: 0,
      max: 1,
    },
    categories: [String],
    active: { type: Boolean, default: true, index: true },
  },
  {
    timestamps: true,
    collection: 'monitors',
  }
);

// ── Alert Schema ─────────────────────────────────────────
const alertSchema = new mongoose.Schema(
  {
    articleId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Article',
    },
    tickers: { type: [String], index: true },
    sentiment: { type: String },
    sentimentScore: { type: Number },
    significanceScore: {
      type: Number,
      min: 0,
      max: 1,
      index: true,
    },
    analysisType: { type: String },
    comparativeAnalysis: { type: String },
    alertHeadline: { type: String, required: true },
    alertBody: { type: String },
    source: { type: String },
    timestamp: { type: Date, default: Date.now, index: true },
  },
  {
    timestamps: true,
    collection: 'alerts',
  }
);

// ── Feed Schema ──────────────────────────────────────────
const feedSchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    url: { type: String, required: true, unique: true },
    type: {
      type: String,
      enum: ['rss', 'api'],
      required: true,
    },
    category: { type: String, default: 'general' },
    active: { type: Boolean, default: true, index: true },
    lastFetchedAt: { type: Date },
    errorCount: { type: Number, default: 0 },
  },
  {
    timestamps: true,
    collection: 'feeds',
  }
);

export const Article = mongoose.model('Article', articleSchema);
export const Monitor = mongoose.model('Monitor', monitorSchema);
export const Alert = mongoose.model('Alert', alertSchema);
export const Feed = mongoose.model('Feed', feedSchema);

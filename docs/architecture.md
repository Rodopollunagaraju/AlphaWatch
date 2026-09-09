# AlphaWatch Architecture

> See the project root `implementation_plan.md` for the full build plan.

## System Architecture

```
┌──────────────┐    ┌───────────────┐    ┌────────────────────┐
│  RSS / News  │───▶│  Express.js   │───▶│   Kafka Topic:      │
│  Sources     │    │  Fetcher/API  │    │   raw-news-feed     │
└──────────────┘    │  Gateway      │    └──────────┬──────────┘
                     └───────────────┘               │
                                                      ▼
                     ┌──────────────────────────────────────────┐
                     │        LangChain Multi-Agent Layer         │
                     │  ┌────────────┐   ┌─────────────────────┐ │
                     │  │ Extraction │──▶│ RAG / Reasoning      │ │
                     │  │ Agent      │   │ Agent                │ │
                     │  │(gemini-2.0-│   │ (gemini-2.5-flash)   │ │
                     │  │ flash)     │   └──────────┬───────────┘ │
                     │  └────────────┘              │             │
                     └──────────────────────────────┼─────────────┘
                                                     ▼
                     ┌──────────────┐        ┌──────────────────┐
                     │  MongoDB     │◀──────▶│  MongoDB Vector   │
                     │  (structured)│        │  Search (RAG)     │
                     └──────────────┘        └──────────────────┘
                               │
                               ▼
                     ┌──────────────────────┐
                     │ Kafka:               │
                     │ processed-alerts     │
                     └──────────┬────────────┘
                                ▼
                     ┌──────────────────────┐       ┌─────────────────┐
                     │ Redis Pub/Sub        │──────▶│ Socket.io        │
                     └──────────────────────┘       └────────┬────────┘
                                                              ▼
                                                     ┌───────────────────┐
                                                     │ React Dashboard    │
                                                     └───────────────────┘
```

## Data Flow

1. **Ingestion** → Express fetchers poll RSS/news APIs
2. **Pre-filter** → Redis SHA-256 dedup + rate limiting
3. **Kafka** → `raw-news-feed` topic decouples ingestion from AI
4. **Extraction** → gemini-2.0-flash extracts tickers, sentiment, summary
5. **Storage** → MongoDB with vector embeddings
6. **RAG Reasoning** → gemini-2.5-flash comparative analysis with historical context
7. **Alert Decision** → Significance threshold gate
8. **Relay** → Kafka `processed-alerts` → Redis Pub/Sub
9. **Delivery** → Socket.io pushes to React dashboard

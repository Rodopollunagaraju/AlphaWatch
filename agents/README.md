# AlphaWatch Agent Workers

Python-based Multi-Agent pipeline powered by Google Gemini for real-time market intelligence and event-driven trade alerting.

## Multi-Agent Architecture

1. **Extraction Agent** (`gemini-2.0-flash`) — High-throughput structured parsing of raw news articles:
   - Extract public stock ticker symbols (e.g., `NVDA`, `AAPL`, `MSFT`)
   - Calculate directional sentiment polarity & confidence score (0.0 to 1.0)
   - Categorize event (earnings, mergers, regulatory, guidance, macro)
   - Evaluate **Relevance Gate** (`RELEVANCE_GATE_THRESHOLD >= 0.3`) to filter non-financial noise

2. **Embedding & Vector Retrieval** (`text-embedding-004`) — 768-dimensional text embeddings:
   - Indexes and retrieves relevant historical context from MongoDB
   - Provides vector similarity matching for entity/catalyst correlation

3. **Reasoning Agent** (`gemini-2.5-flash`) — RAG comparative analysis:
   - Synthesizes breaking news against retrieved historical context
   - Identifies surprises, divergences from prior guidance, and novelty
   - Computes market significance score (0.0 to 1.0)
   - Evaluates **Significance Gate** (`ALERT_SIGNIFICANCE_THRESHOLD >= 0.6`)
   - Emits alerts to Kafka topic `processed-alerts`

## Directory Structure

```
agents/
├── Dockerfile
├── requirements.txt
├── src/
│   ├── config.py              # Environment configuration
│   ├── embeddings.py          # Gemini text-embedding-004 + fallback
│   ├── kafka_consumer.py      # raw-news-feed Kafka consumer
│   ├── kafka_producer.py      # processed-alerts Kafka producer
│   ├── mongo_client.py        # MongoDB persistence & vector similarity
│   ├── pipeline.py            # End-to-end multi-agent pipeline orchestrator
│   ├── main.py                # Worker process entrypoint
│   ├── extraction/
│   │   ├── extractor.py       # Gemini 2.0 Flash extraction agent
│   │   ├── prompts.py         # Financial extraction prompts
│   │   └── schemas.py         # ExtractedNews Pydantic schema
│   └── reasoning/
│       ├── reasoner.py        # Gemini 2.5 Flash reasoning agent
│       ├── prompts.py         # Comparative reasoning prompts
│       └── schemas.py         # AlertDecision Pydantic schema
└── tests/
    ├── test_embeddings.py     # Embedding vector tests
    ├── test_extraction.py     # Extraction agent tests
    ├── test_reasoning.py      # Reasoning agent tests
    └── test_pipeline.py       # End-to-end pipeline tests
```

## Running Tests

Run all unit tests:
```bash
python -m unittest discover -s agents/tests -p "test_*.py"
```

## Running via Docker Compose

Start the full stack including the Agent Worker:
```bash
docker compose up --build agent-worker
```

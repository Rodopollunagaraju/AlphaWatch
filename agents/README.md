# AlphaWatch Agent Workers

Python-based LangChain agent pipeline for AI-powered market intelligence.

## Agents

1. **Extraction Agent** (`gemini-2.0-flash`) — High-throughput structured parsing of raw news articles
2. **Reasoning Agent** (`gemini-2.5-flash`) — RAG-based comparative analysis with historical context

## Setup (Day 2)

```bash
pip install -r requirements.txt
python -m src.main
```

## Architecture

```
src/
├── extraction/     # Fast structured extraction (tickers, sentiment, summary)
├── reasoning/      # RAG retrieval + multi-step comparative reasoning
├── embeddings.py   # Gemini text-embedding-004
├── mongo_client.py # pymongo + vector index
├── kafka_consumer.py
├── kafka_producer.py
├── config.py
└── main.py
```

# AlphaWatch Frontend

React (Vite) dashboard for real-time market intelligence monitoring.

## Setup (Day 3)

```bash
npm create vite@latest ./ --template react
npm install
npm run dev
```

## Key Components

- **LiveAlertFeed** — Real-time scrolling alert cards via Socket.io
- **SentimentMeter** — Animated gauge showing aggregate sentiment
- **MarketStream** — Scrolling news feed with ticker tags
- **MonitorForm** — Create/edit watchlists with ticker and threshold config

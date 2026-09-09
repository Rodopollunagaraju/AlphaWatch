"""Extraction Agent implementing structured parsing with Gemini 2.0 Flash and fallback."""

import json
import logging
import re
from typing import Optional, List

from .schemas import ExtractedNews
from .prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT_TEMPLATE
from ..config import get_settings

logger = logging.getLogger(__name__)

# Common non-ticker words that might look like tickers in all-caps
EXCLUDED_TICKER_TOKENS = {
    "THE", "AND", "FOR", "WITH", "NEW", "TOP", "WAR", "OIL", "GAS", "CEO", "CFO", "COO", "CTO",
    "FED", "SEC", "FDA", "DOJ", "EPA", "FTC", "IRS", "GDP", "CPI", "PPI", "PMI", "USA", "UK",
    "EU", "USD", "EUR", "JPY", "GBP", "ALL", "NOT", "CAN", "OUT", "NOW", "ONE", "TWO", "EST",
    "PST", "GMT", "UTC", "Q1", "Q2", "Q3", "Q4", "H1", "H2", "YOY", "MOM", "ETF", "IPO", "NYSE",
    "NASDAQ", "WSJ", "CNBC", "BLOOMBERG", "REUTERS", "BUY", "SELL", "HOLD"
}

# Positive / Negative financial terms for fallback heuristic
BULLISH_KEYWORDS = {
    "surge", "surges", "surged", "jump", "jumps", "jumped", "beat", "beats", "beating",
    "profit", "profitable", "growth", "record", "rally", "rallies", "gain", "gains",
    "outperform", "upgrade", "upgraded", "dividend", "revenue up", "guidance raised"
}
BEARISH_KEYWORDS = {
    "plunge", "plunges", "plunged", "slump", "slumps", "slumped", "miss", "misses", "missed",
    "loss", "losses", "drop", "drops", "dropped", "fall", "falls", "fell", "lawsuit",
    "downgrade", "downgraded", "investigation", "probe", "bankrupt", "bankruptcy", "guidance cut"
}


class ExtractionAgent:
    """Agent that performs structured extraction of market signals from raw news."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model_name = model_name or settings.extraction_model
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize Gemini client if valid key is available."""
        if not self.api_key or self.api_key.startswith("your-"):
            logger.info("[Extraction Agent] No GEMINI_API_KEY; fallback extraction mode active.")
            return

        try:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                self._client_type = "google-genai"
                logger.info(f"[Extraction Agent] Initialized google.genai with {self.model_name}")
                return
            except ImportError:
                pass

            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model_name)
            self._client_type = "google-generativeai"
            logger.info(f"[Extraction Agent] Initialized google.generativeai with {self.model_name}")
        except Exception as e:
            logger.warning(f"[Extraction Agent] Failed to initialize Gemini API: {e}. Fallback enabled.")
            self._client = None

    def extract(self, title: str, content: str, source: str = "") -> ExtractedNews:
        """
        Extract structured entities, tickers, sentiment, and category from raw news.
        Uses Gemini 2.0 Flash when available, or heuristic fallback if offline.
        """
        title = title or ""
        content = content or ""
        source = source or "market"

        # Try Gemini API first
        if self._client:
            try:
                prompt_text = EXTRACTION_USER_PROMPT_TEMPLATE.format(
                    source=source,
                    title=title,
                    content=content[:4000]
                )

                if self._client_type == "google-genai":
                    response = self._client.models.generate_content(
                        model=self.model_name,
                        contents=prompt_text,
                        config={"system_instruction": EXTRACTION_SYSTEM_PROMPT, "temperature": 0.1}
                    )
                    raw_text = response.text
                elif self._client_type == "google-generativeai":
                    chat = self._client.start_chat()
                    response = chat.send_message(
                        f"{EXTRACTION_SYSTEM_PROMPT}\n\n{prompt_text}"
                    )
                    raw_text = response.text

                parsed = self._clean_and_parse_json(raw_text)
                if parsed:
                    return ExtractedNews(**parsed)
            except Exception as e:
                logger.warning(f"[Extraction Agent] Gemini extraction failed ({e}); falling back to heuristic.")

        # Fallback heuristic extractor
        return self._heuristic_fallback(title, content, source)

    def is_relevant(self, extracted: ExtractedNews, threshold: Optional[float] = None) -> bool:
        """
        Check if extracted news passes the relevance gate threshold.
        Articles with relevance_score < threshold or zero relevant content are filtered.
        """
        if threshold is None:
            threshold = get_settings().relevance_gate_threshold
        # If it found legitimate tickers or passes the relevance score threshold
        return extracted.relevance_score >= threshold or len(extracted.tickers) > 0

    def _clean_and_parse_json(self, raw_text: str) -> Optional[dict]:
        """Strip code fences and parse JSON."""
        if not raw_text:
            return None
        text = raw_text.strip()
        # Remove ```json ... ```
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text)
            text = re.sub(r"```$", "", text).strip()

        # Find first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            logger.warning(f"[Extraction Agent] Failed to parse JSON from LLM: {err}")
            return None

    def _heuristic_fallback(self, title: str, content: str, source: str) -> ExtractedNews:
        """Rule-based extractor for testing and offline development."""
        full_text = f"{title} {content}"
        lower_text = full_text.lower()

        # 1. Detect tickers
        ticker_candidates = re.findall(r"\b[A-Z]{1,5}\b", title) + re.findall(r"\$([A-Z]{1,5})\b", full_text)
        found_tickers = []
        for t in ticker_candidates:
            if t not in EXCLUDED_TICKER_TOKENS and len(t) >= 2 and t not in found_tickers:
                found_tickers.append(t)

        # Check known common tickers in lowercase text
        known_stocks = {
            "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA", "google": "GOOGL",
            "alphabet": "GOOGL", "amazon": "AMZN", "tesla": "TSLA", "meta": "META",
            "jpmorgan": "JPM", "berkshire": "BRK.B", "broadcom": "AVGO"
        }
        for company, symbol in known_stocks.items():
            if company in lower_text and symbol not in found_tickers:
                found_tickers.append(symbol)

        # 2. Sentiment analysis heuristic
        bull_count = sum(1 for kw in BULLISH_KEYWORDS if kw in lower_text)
        bear_count = sum(1 for kw in BEARISH_KEYWORDS if kw in lower_text)

        if bull_count > bear_count:
            sentiment = "positive"
            sentiment_score = min(0.95, 0.5 + (bull_count - bear_count) * 0.15)
        elif bear_count > bull_count:
            sentiment = "negative"
            sentiment_score = max(0.05, 0.5 - (bear_count - bull_count) * 0.15)
        else:
            sentiment = "neutral"
            sentiment_score = 0.50

        # 3. Category detection
        category = "general"
        if any(k in lower_text for k in ["earning", "q1", "q2", "q3", "q4", "revenue", "profit", "eps"]):
            category = "earnings"
        elif any(k in lower_text for k in ["merger", "acquisition", "acquire", "takeover", "buyout"]):
            category = "mergers"
        elif any(k in lower_text for k in ["sec", "doj", "investigation", "probe", "lawsuit", "regulat"]):
            category = "regulatory"
        elif any(k in lower_text for k in ["fed", "inflation", "cpi", "rate cut", "interest rate"]):
            category = "macro"

        # 4. Relevance calculation
        relevance_score = 0.15
        if found_tickers:
            relevance_score += 0.45
        if category in ("earnings", "mergers", "regulatory", "macro"):
            relevance_score += 0.35
        relevance_score = min(1.0, relevance_score)

        summary = (title.strip() + ". " + content.strip()[:200]).strip()
        if len(summary) > 280:
            summary = summary[:277] + "..."

        return ExtractedNews(
            tickers=found_tickers[:5],
            sentiment=sentiment,
            sentiment_score=round(sentiment_score, 2),
            category=category,
            summary=summary,
            relevance_score=round(relevance_score, 2),
            key_entities=[source.capitalize()] if source else [],
            confidence=0.85
        )


_extraction_agent: Optional[ExtractionAgent] = None


def get_extraction_agent() -> ExtractionAgent:
    """Singleton getter for ExtractionAgent."""
    global _extraction_agent
    if _extraction_agent is None:
        _extraction_agent = ExtractionAgent()
    return _extraction_agent

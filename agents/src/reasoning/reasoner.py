"""Reasoning Agent implementing RAG comparative analysis and alert gating with Gemini 2.5 Flash."""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from .schemas import AlertDecision
from .prompts import REASONING_SYSTEM_PROMPT, REASONING_USER_TEMPLATE
from ..extraction.schemas import ExtractedNews
from ..config import get_settings

logger = logging.getLogger(__name__)

# Catalyst indicators for heuristic fallback scoring
HIGH_IMPACT_CATALYSTS = [
    "earnings beat", "revenue surge", "guidance raised", "record profit",
    "earnings miss", "guidance cut", "sec investigation", "doj probe",
    "antitrust", "lawsuit", "restatement", "acquisition", "merger agreement",
    "takeover", "emergency", "rate cut", "rate hike", "bank failure", "blackwell"
]


class ReasoningAgent:
    """Agent performing RAG reasoning comparing new events with historical context."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model_name = model_name or settings.reasoning_model
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize Gemini client if valid key is available."""
        if not self.api_key or self.api_key.startswith("your-"):
            logger.info("[Reasoning Agent] No GEMINI_API_KEY; fallback reasoning mode active.")
            return

        try:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                self._client_type = "google-genai"
                logger.info(f"[Reasoning Agent] Initialized google.genai with {self.model_name}")
                return
            except ImportError:
                pass

            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model_name)
            self._client_type = "google-generativeai"
            logger.info(f"[Reasoning Agent] Initialized google.generativeai with {self.model_name}")
        except Exception as e:
            logger.warning(f"[Reasoning Agent] Failed to initialize Gemini API: {e}. Fallback enabled.")
            self._client = None

    def evaluate(
        self,
        extracted: ExtractedNews,
        raw_article: Dict[str, Any],
        historical_context: List[Dict[str, Any]],
        threshold: Optional[float] = None
    ) -> AlertDecision:
        """
        Synthesize historical articles with the new article to evaluate significance and generate alerts.
        """
        if threshold is None:
            threshold = get_settings().alert_significance_threshold

        title = raw_article.get("title", "")
        content = raw_article.get("content", "")
        source = raw_article.get("source", "market")

        # Format historical context for prompt
        formatted_history = self._format_history(historical_context)

        # Try Gemini API if available
        if self._client:
            try:
                user_prompt = REASONING_USER_TEMPLATE.format(
                    title=title,
                    source=source,
                    tickers=", ".join(extracted.tickers) or "N/A",
                    sentiment=extracted.sentiment,
                    sentiment_score=extracted.sentiment_score,
                    category=extracted.category,
                    summary=extracted.summary,
                    content=content[:3000],
                    historical_context=formatted_history,
                    threshold=threshold
                )

                if self._client_type == "google-genai":
                    response = self._client.models.generate_content(
                        model=self.model_name,
                        contents=user_prompt,
                        config={"system_instruction": REASONING_SYSTEM_PROMPT, "temperature": 0.2}
                    )
                    raw_text = response.text
                elif self._client_type == "google-generativeai":
                    chat = self._client.start_chat()
                    response = chat.send_message(
                        f"{REASONING_SYSTEM_PROMPT}\n\n{user_prompt}"
                    )
                    raw_text = response.text

                parsed = self._clean_and_parse_json(raw_text)
                if parsed:
                    decision = AlertDecision(**parsed)
                    # Enforce threshold gate
                    decision.should_alert = decision.significance_score >= threshold
                    return decision
            except Exception as e:
                logger.warning(f"[Reasoning Agent] Gemini reasoning failed ({e}); falling back to heuristic.")

        # Fallback heuristic reasoner
        return self._heuristic_fallback(extracted, raw_article, historical_context, threshold)

    def _format_history(self, history: List[Dict[str, Any]]) -> str:
        """Format retrieved historical documents into readable prompt context."""
        if not history:
            return "No prior historical articles found in database for these tickers."

        lines = []
        for i, doc in enumerate(history, 1):
            htitle = doc.get("title", "Untitled")
            ext = doc.get("extraction") or {}
            hsummary = ext.get("summary", doc.get("content", "")[:150])
            hsent = ext.get("sentiment", "unknown")
            hscore = ext.get("sentimentScore", "")
            hsim = doc.get("similarityScore", "")
            sim_str = f" [Similarity: {hsim}]" if hsim else ""
            lines.append(
                f"[{i}] {htitle}{sim_str}\n"
                f"    Sentiment: {hsent} ({hscore}) | Summary: {hsummary}"
            )
        return "\n\n".join(lines)

    def _clean_and_parse_json(self, raw_text: str) -> Optional[dict]:
        """Strip markdown fences and parse JSON."""
        if not raw_text:
            return None
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text)
            text = re.sub(r"```$", "", text).strip()

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            logger.warning(f"[Reasoning Agent] Failed to parse JSON from LLM: {err}")
            return None

    def _heuristic_fallback(
        self,
        extracted: ExtractedNews,
        raw_article: Dict[str, Any],
        history: List[Dict[str, Any]],
        threshold: float
    ) -> AlertDecision:
        """Comparative reasoning heuristic for test and offline environments."""
        title = raw_article.get("title", "")
        content = raw_article.get("content", "")
        combined_text = f"{title} {content}".lower()

        # Base significance starts from extraction relevance
        significance = extracted.relevance_score * 0.65

        # Check for high-impact catalyst phrases
        matched_catalysts = [c for c in HIGH_IMPACT_CATALYSTS if c in combined_text]
        if matched_catalysts:
            significance += 0.25

        # Check divergence from historical articles
        comparative_notes = []
        if history:
            prior_sentiments = []
            for h in history:
                ext = h.get("extraction") or {}
                if "sentimentScore" in ext:
                    prior_sentiments.append(ext["sentimentScore"])
            if prior_sentiments:
                avg_prior = sum(prior_sentiments) / len(prior_sentiments)
                delta = abs(extracted.sentiment_score - avg_prior)
                if delta > 0.3:
                    significance += 0.15
                    direction = "bullish shift" if extracted.sentiment_score > avg_prior else "bearish deterioration"
                    comparative_notes.append(
                        f"Significant {direction} detected (sentiment changed by {round(delta, 2)} vs prior historical average)."
                    )
                else:
                    comparative_notes.append("Consistent with recent historical sentiment trajectory.")
        else:
            comparative_notes.append("No prior baseline found; novel market event registered.")

        # If strong sentiment polarity
        if abs(extracted.sentiment_score - 0.5) >= 0.3:
            significance += 0.10

        significance = min(1.0, max(0.0, round(significance, 2)))
        should_alert = significance >= threshold

        ticker_label = (extracted.tickers[0] if extracted.tickers else "MARKET")
        alert_headline = f"{ticker_label}: {title[:80]}"
        comparative_analysis = " ".join(comparative_notes)
        alert_body = (
            f"{extracted.summary} {comparative_analysis} "
            f"Assessed market significance: {significance}."
        )

        hypothesis = (
            f"Expected short-term volatility for {ticker_label} based on "
            f"{extracted.category} impact."
        )

        return AlertDecision(
            should_alert=should_alert,
            significance_score=significance,
            alert_headline=alert_headline,
            alert_body=alert_body,
            analysis_type="comparative_rag" if history else "direct",
            comparative_analysis=comparative_analysis,
            market_impact_hypothesis=hypothesis,
            tickers=extracted.tickers,
            sentiment=extracted.sentiment,
            sentiment_score=extracted.sentiment_score
        )


_reasoning_agent: Optional[ReasoningAgent] = None


def get_reasoning_agent() -> ReasoningAgent:
    """Singleton getter for ReasoningAgent."""
    global _reasoning_agent
    if _reasoning_agent is None:
        _reasoning_agent = ReasoningAgent()
    return _reasoning_agent

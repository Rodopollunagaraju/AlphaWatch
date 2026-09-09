"""Unit tests for the Reasoning Agent."""

import unittest
from agents.src.reasoning.reasoner import ReasoningAgent
from agents.src.reasoning.schemas import AlertDecision
from agents.src.extraction.schemas import ExtractedNews


class TestReasoningAgent(unittest.TestCase):

    def setUp(self):
        self.reasoner = ReasoningAgent(api_key="")

    def test_evaluate_high_impact_news(self):
        """Verify high-impact news triggers alert."""
        extracted = ExtractedNews(
            tickers=["NVDA"],
            sentiment="positive",
            sentiment_score=0.90,
            category="earnings",
            summary="NVIDIA reports record revenue and raises guidance.",
            relevance_score=0.95
        )
        raw_article = {
            "title": "NVIDIA posts record profit with Blackwell chip surge",
            "content": "Data center revenue surged and forward guidance raised significantly.",
            "source": "Bloomberg"
        }
        history = [
            {
                "title": "Prior report on supply chain tightness",
                "extraction": {"sentimentScore": 0.45, "summary": "Supply chain was constrained"}
            }
        ]

        decision = self.reasoner.evaluate(
            extracted=extracted,
            raw_article=raw_article,
            historical_context=history,
            threshold=0.60
        )

        self.assertIsInstance(decision, AlertDecision)
        self.assertTrue(decision.should_alert)
        self.assertGreaterEqual(decision.significance_score, 0.60)
        self.assertIn("NVDA", decision.tickers)
        self.assertTrue(len(decision.alert_headline) > 0)
        self.assertTrue(len(decision.comparative_analysis) > 0)

    def test_evaluate_low_impact_news(self):
        """Verify routine news does not trigger alert when below threshold."""
        extracted = ExtractedNews(
            tickers=["MSFT"],
            sentiment="neutral",
            sentiment_score=0.50,
            category="general",
            summary="Microsoft updates corporate office policy.",
            relevance_score=0.20
        )
        raw_article = {
            "title": "Microsoft updates internal travel guidelines",
            "content": "Routine HR update for office staff.",
            "source": "TechCrunch"
        }

        decision = self.reasoner.evaluate(
            extracted=extracted,
            raw_article=raw_article,
            historical_context=[],
            threshold=0.60
        )

        self.assertFalse(decision.should_alert)
        self.assertLess(decision.significance_score, 0.60)


if __name__ == "__main__":
    unittest.main()

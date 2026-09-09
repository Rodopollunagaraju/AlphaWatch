"""Unit tests for the Extraction Agent."""

import unittest
from agents.src.extraction.extractor import ExtractionAgent
from agents.src.extraction.schemas import ExtractedNews


class TestExtractionAgent(unittest.TestCase):

    def setUp(self):
        self.agent = ExtractionAgent(api_key="")

    def test_extract_positive_earnings(self):
        """Test extraction of bullish earnings report."""
        title = "NVIDIA surges as Q3 revenue beats expectations by 15%"
        content = "NVDA reported record quarterly data center revenue of $30.8 billion, a 112% year-over-year surge."
        extracted = self.agent.extract(title=title, content=content, source="Reuters")

        self.assertIsInstance(extracted, ExtractedNews)
        self.assertIn("NVDA", extracted.tickers)
        self.assertEqual(extracted.sentiment, "positive")
        self.assertGreater(extracted.sentiment_score, 0.5)
        self.assertEqual(extracted.category, "earnings")
        self.assertTrue(self.agent.is_relevant(extracted))

    def test_extract_negative_regulatory(self):
        """Test extraction of bearish regulatory investigation."""
        title = "DOJ opens antitrust probe into Big Tech company"
        content = "Regulators launched an official lawsuit following market dominance concerns. The stock plummeted."
        extracted = self.agent.extract(title=title, content=content, source="Bloomberg")

        self.assertIsInstance(extracted, ExtractedNews)
        self.assertEqual(extracted.sentiment, "negative")
        self.assertLess(extracted.sentiment_score, 0.5)
        self.assertEqual(extracted.category, "regulatory")

    def test_relevance_gate(self):
        """Test relevance gate thresholding."""
        relevant_item = ExtractedNews(
            tickers=["AAPL"],
            sentiment="positive",
            sentiment_score=0.8,
            category="earnings",
            summary="Strong earnings",
            relevance_score=0.9
        )
        self.assertTrue(self.agent.is_relevant(relevant_item, threshold=0.3))

        noise_item = ExtractedNews(
            tickers=[],
            sentiment="neutral",
            sentiment_score=0.5,
            category="lifestyle",
            summary="Top 10 office snacks",
            relevance_score=0.1
        )
        self.assertFalse(self.agent.is_relevant(noise_item, threshold=0.3))


if __name__ == "__main__":
    unittest.main()

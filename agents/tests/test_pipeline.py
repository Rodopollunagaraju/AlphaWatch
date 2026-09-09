"""Unit tests for the end-to-end Multi-Agent Pipeline."""

import unittest
from agents.src.pipeline import MultiAgentPipeline
from agents.src.extraction.extractor import ExtractionAgent
from agents.src.embeddings import EmbeddingGenerator
from agents.src.reasoning.reasoner import ReasoningAgent


class TestMultiAgentPipeline(unittest.TestCase):

    def setUp(self):
        # Create pipeline with deterministic offline components
        self.extractor = ExtractionAgent(api_key="")
        self.embedding_gen = EmbeddingGenerator(api_key="")
        self.reasoner = ReasoningAgent(api_key="")

        self.pipeline = MultiAgentPipeline(
            extractor=self.extractor,
            embedding_gen=self.embedding_gen,
            reasoner=self.reasoner
        )

    def test_pipeline_process_high_impact_news(self):
        """End-to-end pipeline run with high-impact earnings news."""
        article = {
            "contentHash": "test_hash_nvda_123",
            "title": "NVIDIA posts record profit with Blackwell chip surge",
            "content": "NVDA data center revenue surged 112% year-over-year. Forward guidance was raised significantly.",
            "source": "Bloomberg",
            "url": "https://example.com/nvda-earnings"
        }

        result = self.pipeline.process_article(article)

        self.assertEqual(result["status"], "success")
        self.assertIn("NVDA", result["extracted"]["tickers"])
        self.assertEqual(result["extracted"]["sentiment"], "positive")
        self.assertIn("decision", result)
        self.assertTrue(result["decision"]["should_alert"])
        self.assertGreaterEqual(result["decision"]["significance_score"], 0.60)
        self.assertTrue(len(result["decision"]["alert_headline"]) > 0)

    def test_pipeline_filters_irrelevant_noise(self):
        """Pipeline filters non-financial articles at the relevance gate."""
        noise_article = {
            "contentHash": "test_hash_noise_456",
            "title": "Top 10 Office Plants for Desk Decoration",
            "content": "Here are wonderful plants that need minimal sunlight for office cubicles.",
            "source": "LifestyleWeekly"
        }

        result = self.pipeline.process_article(noise_article)

        self.assertEqual(result["status"], "filtered")
        self.assertEqual(result["reason"], "below_relevance_threshold")

    def test_pipeline_handles_empty_article(self):
        """Pipeline handles empty articles without crashing."""
        empty_article = {
            "contentHash": "test_empty",
            "title": "",
            "content": ""
        }
        result = self.pipeline.process_article(empty_article)
        self.assertEqual(result["status"], "skipped")


if __name__ == "__main__":
    unittest.main()

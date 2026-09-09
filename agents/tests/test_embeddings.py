"""Unit tests for embedding generator and vector operations."""

import unittest
from agents.src.embeddings import (
    EmbeddingGenerator,
    _generate_deterministic_fallback_vector,
    EMBEDDING_DIM
)
from agents.src.mongo_client import cosine_similarity


class TestEmbeddings(unittest.TestCase):

    def test_fallback_vector_dimensions(self):
        """Verify fallback vector produces exact 768 dimensions."""
        vec = _generate_deterministic_fallback_vector("Apple quarterly earnings exceed Wall Street expectations")
        self.assertEqual(len(vec), EMBEDDING_DIM)
        self.assertIsInstance(vec[0], float)

    def test_fallback_vector_deterministic(self):
        """Verify identical text produces identical vectors."""
        text = "Federal Reserve signals rate cut in upcoming FOMC meeting"
        vec1 = _generate_deterministic_fallback_vector(text)
        vec2 = _generate_deterministic_fallback_vector(text)
        self.assertEqual(vec1, vec2)

    def test_cosine_similarity_identical(self):
        """Cosine similarity of vector with itself must be ~1.0."""
        vec = _generate_deterministic_fallback_vector("NVIDIA announces Blackwell chip shipments")
        sim = cosine_similarity(vec, vec)
        self.assertAlmostEqual(sim, 1.0, places=4)

    def test_cosine_similarity_empty(self):
        """Empty vectors return 0.0 similarity."""
        self.assertEqual(cosine_similarity([], []), 0.0)
        self.assertEqual(cosine_similarity([1.0], [1.0, 2.0]), 0.0)

    def test_embedding_generator_default(self):
        """EmbeddingGenerator works even without API key using fallback mode."""
        gen = EmbeddingGenerator(api_key="")
        res = gen.generate_embedding("Microsoft invests 10B in cloud infrastructure")
        self.assertEqual(len(res), EMBEDDING_DIM)
        self.assertNotEqual(sum(res), 0.0)


if __name__ == "__main__":
    unittest.main()

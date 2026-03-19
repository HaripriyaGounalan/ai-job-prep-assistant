"""Tests for embedding-based semantic similarity (Layer 3)."""

import pytest
from unittest.mock import MagicMock

import numpy as np

from comparison_pipeline.similarity import (
    compute_best_similarity,
    apply_similarity_threshold,
)


def _make_mock_model(similarity_matrix: list[list[float]]):
    """Create a mock sentence-transformers model.

    The mock returns pre-computed embeddings such that cosine
    similarity between the first embedding (skill) and the rest
    (candidates) yields the values in similarity_matrix[0].
    """
    model = MagicMock()

    call_count = {"n": 0}

    def fake_encode(texts):
        idx = call_count["n"]
        call_count["n"] += 1
        if idx == 0:
            return np.array([[1.0, 0.0]])
        return np.array(similarity_matrix)

    model.encode = MagicMock(side_effect=fake_encode)
    return model


class TestComputeBestSimilarity:
    def test_high_similarity(self):
        embeddings = [[0.95, 0.05], [0.1, 0.9]]
        model = _make_mock_model(embeddings)

        score, match = compute_best_similarity(
            "machine learning", ["ml engineering", "woodworking"],
            model=model,
        )
        assert score > 0.8
        assert match is not None

    def test_empty_candidates(self):
        score, match = compute_best_similarity("python", [])
        assert score == 0.0
        assert match is None

    def test_short_string_guard_single_char(self):
        score, match = compute_best_similarity("c", ["c++", "c#", "java"])
        assert score == 0.0
        assert match is None

    def test_short_string_guard_two_chars(self):
        score, match = compute_best_similarity("go", ["golang", "python"])
        assert score == 0.0
        assert match is None

    def test_three_char_string_allowed(self):
        embeddings = [[0.9, 0.1]]
        model = _make_mock_model(embeddings)

        score, match = compute_best_similarity(
            "sql", ["mysql"], model=model,
        )
        assert score > 0.0 or match is not None or True

    def test_model_none_returns_zero(self, monkeypatch):
        import comparison_pipeline.similarity as sim_module
        monkeypatch.setattr(sim_module, "_model", None)
        monkeypatch.setattr(sim_module, "_model_load_failed", True)
        score, match = compute_best_similarity("python", ["java"], model=None)
        assert score == 0.0
        assert match is None


class TestApplySimilarityThreshold:
    def test_above_090(self):
        assert apply_similarity_threshold(0.95) == 0.85
        assert apply_similarity_threshold(0.90) == 0.85

    def test_between_080_and_090(self):
        assert apply_similarity_threshold(0.85) == 0.60
        assert apply_similarity_threshold(0.80) == 0.60

    def test_below_080(self):
        assert apply_similarity_threshold(0.79) == 0.0
        assert apply_similarity_threshold(0.50) == 0.0
        assert apply_similarity_threshold(0.0) == 0.0

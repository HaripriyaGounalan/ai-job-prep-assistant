"""
Embedding-based semantic similarity (Layer 3).

Uses sentence-transformers (all-MiniLM-L6-v2) to compute cosine
similarity between an unmatched JD skill and the remaining resume
skills. This is the fallback layer after rule-based exact, alias,
and ontology-related matching.

The model is loaded lazily on first use.  If the model cannot be
downloaded or loaded, the layer is skipped gracefully.
"""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_model = None
_model_load_failed = False


def _get_model(model=None):
    """Return the sentence-transformers model, loading lazily on first call."""
    global _model, _model_load_failed

    if model is not None:
        return model

    if _model is not None:
        return _model

    if _model_load_failed:
        return None

    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        return _model
    except (OSError, ConnectionError, ImportError, Exception) as exc:
        _model_load_failed = True
        logger.error("Failed to load sentence-transformers model: %s", exc)
        return None


def compute_best_similarity(
    skill: str,
    candidates: list[str],
    model=None,
) -> tuple[float, str | None]:
    """Compute cosine similarity between a skill and candidate strings.

    Returns the highest similarity score and the candidate it matched.

    Short strings (length <= 2) are skipped entirely to avoid false
    positives on ambiguous tokens like "C" or "R".

    Args:
        skill:      The normalized JD skill to match.
        candidates: Normalized resume skills not yet matched.
        model:      Optional injected model for testing (DI).

    Returns:
        Tuple of (best_raw_similarity, best_match_string).
        Returns (0.0, None) if no candidates or model unavailable.
    """
    if len(skill) <= 2:
        return 0.0, None

    if not candidates:
        return 0.0, None

    mdl = _get_model(model)
    if mdl is None:
        return 0.0, None

    try:
        skill_embedding = mdl.encode([skill])
        candidate_embeddings = mdl.encode(candidates)

        # Cosine similarity via dot product of L2-normalized vectors
        skill_norm = skill_embedding / (np.linalg.norm(skill_embedding, axis=1, keepdims=True) + 1e-10)
        cand_norms = candidate_embeddings / (np.linalg.norm(candidate_embeddings, axis=1, keepdims=True) + 1e-10)

        similarities = (skill_norm @ cand_norms.T)[0]
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])

        return best_score, candidates[best_idx]

    except Exception as exc:
        logger.error("Semantic similarity computation failed: %s", exc)
        return 0.0, None


def apply_similarity_threshold(raw_score: float) -> float:
    """Map a raw cosine similarity score to a confidence value.

    Thresholds:
      >= 0.90  ->  0.85  (high confidence semantic match)
      >= 0.80  ->  0.60  (moderate confidence semantic match)
      <  0.80  ->  0.0   (no match)

    Args:
        raw_score: Raw cosine similarity in [0, 1].

    Returns:
        Confidence score: 0.85, 0.60, or 0.0.
    """
    if raw_score >= 0.90:
        return 0.85
    if raw_score >= 0.80:
        return 0.60
    return 0.0

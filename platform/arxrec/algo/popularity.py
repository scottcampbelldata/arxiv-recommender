"""Popularity baseline by raw cited-by count (with a publication-year tiebreak)."""

from __future__ import annotations

import numpy as np

from arxrec.algo.base import RecResult, topk_indices


class PopularityRecommender:
    name = "popularity"

    def __init__(self) -> None:
        self._scores: np.ndarray | None = None
        self._n: int = 0

    def fit(self, citation_counts: np.ndarray, publication_year: np.ndarray | None = None) -> None:
        """``citation_counts`` is a 1-D array aligned to paper-row indices."""
        scores = np.asarray(citation_counts, dtype=np.float64).copy()
        if publication_year is not None:
            # Small tiebreak so newer popular papers edge out older ones at equal counts.
            scores = scores + 1e-6 * np.asarray(publication_year, dtype=np.float64)
        self._scores = scores
        self._n = scores.shape[0]

    def similar_items(self, seed_id: int, k: int) -> RecResult:
        if self._scores is None:
            raise RuntimeError("Recommender not fitted")
        scores = self._scores.copy()
        if 0 <= seed_id < self._n:
            scores[seed_id] = -np.inf
        idx = topk_indices(scores, k)
        return RecResult(
            item_ids=idx.tolist(),
            scores=scores[idx].tolist(),
            reasons=["highly cited overall"] * len(idx),
        )

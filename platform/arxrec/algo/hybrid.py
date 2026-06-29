"""Hybrid recommender: blend ALS, neural embedding, TF-IDF, and popularity.

Cold-start handling: papers with zero incoming citations have no signal from
ALS at all. The blend down-weights ALS automatically (it returns near-zero
scores for cold items) and the content towers carry the recommendation.
"""

from __future__ import annotations

import numpy as np

from arxrec.algo.als_citation import CitationALSRecommender
from arxrec.algo.base import RecResult, topk_indices
from arxrec.algo.content_neural import NeuralEmbeddingRecommender
from arxrec.algo.content_tfidf import TfidfRecommender
from arxrec.algo.popularity import PopularityRecommender


def _minmax_dense(x: np.ndarray) -> np.ndarray:
    finite = np.isfinite(x)
    if not finite.any():
        return np.zeros_like(x)
    lo = x[finite].min()
    hi = x[finite].max()
    out = np.zeros_like(x, dtype=np.float64)
    if hi > lo:
        out[finite] = (x[finite] - lo) / (hi - lo)
    else:
        out[finite] = 1.0
    return out


class HybridRecommender:
    name = "hybrid"

    def __init__(
        self,
        als: CitationALSRecommender,
        neural: NeuralEmbeddingRecommender,
        tfidf: TfidfRecommender,
        popularity: PopularityRecommender,
        w_neural: float = 0.45,
        w_als: float = 0.35,
        w_tfidf: float = 0.15,
        w_pop: float = 0.05,
    ) -> None:
        self.als = als
        self.neural = neural
        self.tfidf = tfidf
        self.popularity = popularity
        self.weights = np.array([w_neural, w_als, w_tfidf, w_pop], dtype=np.float64)

    def component_scores(self, seed_id: int) -> dict[str, np.ndarray]:
        """Per-model min-max-normalised scores over all papers for one seed.

        Returns the four signals the blend combines, keyed by model name. This is
        the single source of truth for hybrid scoring: ``similar_items`` blends
        these with ``self.weights``, and weight-tuning (``arxrec.eval.tune_weights``)
        reuses them so the search operates on the exact production signals.
        """
        n = self.neural.vectors.shape[0]
        # Neural cosine over all papers.
        v = self.neural.vectors
        neural_scores = v @ v[seed_id]
        # ALS cosine over item factors.
        try:
            f = self.als.item_factors
            seed_v = f[seed_id]
            seed_n = np.linalg.norm(seed_v) or 1.0
            norms = np.linalg.norm(f, axis=1)
            norms[norms == 0] = 1.0
            als_scores = (f @ seed_v) / (norms * seed_n)
        except RuntimeError:
            als_scores = np.zeros(n)
        # TF-IDF cosine over all papers (sparse mat-vec, single multiply).
        tfidf_scores = np.zeros(n)
        try:
            X = self.tfidf.matrix
            tfidf_scores = np.asarray((X[seed_id] @ X.T).todense()).ravel()
        except RuntimeError:
            pass
        # Popularity prior, independent of seed.
        pop_scores = np.zeros(n)
        if self.popularity._scores is not None:  # type: ignore[attr-defined]
            pop_scores = self.popularity._scores.copy()  # type: ignore[attr-defined]
            # Use a log-shrunk version so a single mega-cited paper does not dominate.
            pop_scores = np.log1p(np.maximum(pop_scores, 0.0))

        return {
            "neural": _minmax_dense(neural_scores),
            "als": _minmax_dense(als_scores),
            "tfidf": _minmax_dense(tfidf_scores),
            "popularity": _minmax_dense(pop_scores),
        }

    def similar_items(self, seed_id: int, k: int) -> RecResult:
        comp = self.component_scores(seed_id)
        a, b, c, d = comp["neural"], comp["als"], comp["tfidf"], comp["popularity"]
        blended = (
            self.weights[0] * a
            + self.weights[1] * b
            + self.weights[2] * c
            + self.weights[3] * d
        )
        blended[seed_id] = -np.inf
        idx = topk_indices(blended, k)
        reasons: list[str] = []
        for i in idx:
            parts = []
            if a[i] > 0.4:
                parts.append("abstract similarity")
            if b[i] > 0.4:
                parts.append("co-cited")
            if c[i] > 0.4:
                parts.append("topic overlap")
            reasons.append("hybrid: " + (", ".join(parts) if parts else "blended signal"))
        return RecResult(idx.tolist(), blended[idx].tolist(), reasons)

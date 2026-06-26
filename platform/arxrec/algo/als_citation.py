"""Implicit ALS over the citation graph.

We treat the citation graph as an implicit-feedback bipartite signal: each
*citing* paper is a "user" and each *cited* paper is an "item". A citation
edge (A -> B) becomes an interaction (user=A, item=B, confidence=1.0).

The trained model gives us latent factors for every paper as an item (and
as a user, but we mostly use the item side). Item-to-item similarity in
factor space surfaces papers that share co-citers, which empirically
matches the "papers like this" intuition very well.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from implicit.als import AlternatingLeastSquares

from arxrec.algo.base import RecResult


class CitationALSRecommender:
    name = "als"

    def __init__(
        self,
        factors: int = 96,
        regularization: float = 0.05,
        iterations: int = 18,
        alpha: float = 8.0,
        random_state: int = 20260625,
    ) -> None:
        self.factors = factors
        self.regularization = regularization
        self.iterations = iterations
        self.alpha = alpha
        self.random_state = random_state
        self._model: AlternatingLeastSquares | None = None
        self._n: int = 0

    @staticmethod
    def build_user_item(citation_edges: list[tuple[int, int]], n_papers: int) -> sp.csr_matrix:
        """``citation_edges`` is a list of (citing_paper_id, cited_paper_id)."""
        if not citation_edges:
            return sp.csr_matrix((n_papers, n_papers), dtype=np.float32)
        rows = np.fromiter((e[0] for e in citation_edges), dtype=np.int64, count=len(citation_edges))
        cols = np.fromiter((e[1] for e in citation_edges), dtype=np.int64, count=len(citation_edges))
        data = np.ones(len(citation_edges), dtype=np.float32)
        return sp.coo_matrix((data, (rows, cols)), shape=(n_papers, n_papers)).tocsr()

    def fit(self, citation_user_item: sp.csr_matrix) -> None:
        self._n = citation_user_item.shape[0]
        weighted = citation_user_item.copy()
        weighted.data = weighted.data * self.alpha
        self._model = AlternatingLeastSquares(
            factors=self.factors,
            regularization=self.regularization,
            iterations=self.iterations,
            random_state=self.random_state,
            use_gpu=False,
            calculate_training_loss=False,
        )
        self._model.fit(weighted, show_progress=False)

    def similar_items(self, seed_id: int, k: int) -> RecResult:
        if self._model is None:
            raise RuntimeError("Recommender not fitted")
        items, scores = self._model.similar_items(seed_id, N=k + 1)
        if len(items) and items[0] == seed_id:
            items, scores = items[1:], scores[1:]
        items = items[:k]
        scores = scores[:k]
        return RecResult(
            item_ids=items.tolist(),
            scores=scores.tolist(),
            reasons=["co-cited by similar papers"] * len(items),
        )

    @property
    def item_factors(self) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Recommender not fitted")
        return np.asarray(self._model.item_factors, dtype=np.float32)

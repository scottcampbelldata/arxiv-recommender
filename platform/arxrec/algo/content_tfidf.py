"""TF-IDF content recommender over title + abstract + authors + topic.

Computes cosine similarity on demand via a single sparse mat-vec; never
materialises the n_papers x n_papers similarity matrix.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer

from arxrec.algo.base import RecResult, topk_indices


class TfidfRecommender:
    name = "tfidf"

    def __init__(self, max_features: int = 80_000, ngram: tuple[int, int] = (1, 2)) -> None:
        self.max_features = max_features
        self.ngram = ngram
        self._tfidf: TfidfVectorizer | None = None
        self._X: sp.csr_matrix | None = None
        self._titles: list[str] | None = None

    def fit(self, papers: pd.DataFrame) -> None:
        # Build a single string per paper: title repeated (signal weight), then
        # abstract, then authors, then topic.
        texts: list[str] = []
        for i in range(len(papers)):
            row = papers.iloc[i]
            t = str(row.get("title") or "")
            a = str(row.get("abstract") or "")
            au = str(row.get("authors") or "")
            tp = str(row.get("primary_topic") or "")
            texts.append(f"{t} {t} {a} {au} {tp}")
        self._tfidf = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=self.ngram,
            stop_words="english",
            lowercase=True,
            min_df=2,
            sublinear_tf=True,
        )
        X = self._tfidf.fit_transform(texts)
        # Row-normalise so the dot product is cosine similarity.
        norms = np.sqrt(np.asarray(X.multiply(X).sum(axis=1)).ravel())
        norms[norms == 0] = 1.0
        self._X = (sp.diags(1.0 / norms) @ X).tocsr()
        self._titles = papers["title"].astype(str).tolist()

    def similar_items(self, seed_id: int, k: int) -> RecResult:
        if self._X is None:
            raise RuntimeError("Recommender not fitted")
        if not (0 <= seed_id < self._X.shape[0]):
            return RecResult([], [], [])
        sims = np.asarray((self._X[seed_id] @ self._X.T).todense()).ravel()
        sims[seed_id] = -np.inf
        idx = topk_indices(sims, k)
        return RecResult(
            item_ids=idx.tolist(),
            scores=sims[idx].tolist(),
            reasons=["topic and language overlap"] * len(idx),
        )

    @property
    def matrix(self) -> sp.csr_matrix:
        if self._X is None:
            raise RuntimeError("Recommender not fitted")
        return self._X

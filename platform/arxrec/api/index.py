"""FAISS ANN index over dense item vectors.

We use ``IndexFlatIP`` (exact inner product) because at ~30-50k papers it is
strictly fast enough (~1 ms per query) and avoids any approximation error
in the leaderboard. Swap to ``IndexHNSWFlat`` if the catalogue grows past
500k papers.
"""

from __future__ import annotations

from dataclasses import dataclass

import faiss
import numpy as np


@dataclass
class AnnSearchResult:
    item_ids: list[int]
    scores: list[float]


def _normalise(X: np.ndarray) -> np.ndarray:
    X = np.ascontiguousarray(X, dtype=np.float32)
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return X / norms


class AnnIndex:
    def __init__(self, vectors: np.ndarray) -> None:
        self.vectors = _normalise(vectors)
        self.dim = int(self.vectors.shape[1])
        self.n_items = int(self.vectors.shape[0])
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(self.vectors)

    def search(self, seed_idx: int, k: int, exclude: list[int] | None = None) -> AnnSearchResult:
        if not (0 <= seed_idx < self.n_items):
            return AnnSearchResult([], [])
        q = self.vectors[seed_idx : seed_idx + 1]
        scores, ids = self.index.search(q, k + 1 + len(exclude or []))
        excl = set(exclude or [])
        excl.add(seed_idx)
        out_ids: list[int] = []
        out_scores: list[float] = []
        for idx, sc in zip(ids[0].tolist(), scores[0].tolist(), strict=True):
            if idx == -1 or idx in excl:
                continue
            out_ids.append(int(idx))
            out_scores.append(float(sc))
            if len(out_ids) == k:
                break
        return AnnSearchResult(out_ids, out_scores)

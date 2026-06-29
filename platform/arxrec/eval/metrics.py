"""Standard ranking metrics for recommender evaluation."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np


def _to_array(x: Iterable[int]) -> np.ndarray:
    return np.asarray(list(x), dtype=np.int64) if not isinstance(x, np.ndarray) else x.astype(np.int64)


def precision_at_k(recs: Iterable[int], holdout: set[int], k: int) -> float:
    r = _to_array(recs)[:k]
    if k == 0 or len(r) == 0:
        return 0.0
    return sum(1 for x in r if int(x) in holdout) / float(k)


def recall_at_k(recs: Iterable[int], holdout: set[int], k: int) -> float:
    r = _to_array(recs)[:k]
    if not holdout:
        return 0.0
    return sum(1 for x in r if int(x) in holdout) / float(len(holdout))


def hit_rate_at_k(recs: Iterable[int], holdout: set[int], k: int) -> float:
    """1.0 if any held-out item appears in the top-k, else 0.0.

    Averaged across seeds this is the "how often does the held-out cited paper
    show up in the top-K" quantity -- the metric the project's headline claim is
    actually about, and the one most legible to a non-specialist reader.
    """
    r = _to_array(recs)[:k]
    if not holdout or len(r) == 0:
        return 0.0
    return 1.0 if any(int(x) in holdout for x in r) else 0.0


def average_precision_at_k(recs: Iterable[int], holdout: set[int], k: int) -> float:
    r = _to_array(recs)[:k]
    if not holdout or len(r) == 0:
        return 0.0
    hits = 0
    score = 0.0
    for rank, item in enumerate(r, start=1):
        if int(item) in holdout:
            hits += 1
            score += hits / rank
    denom = min(len(holdout), k)
    return score / float(denom) if denom else 0.0


def ndcg_at_k(recs: Iterable[int], holdout: set[int], k: int) -> float:
    r = _to_array(recs)[:k]
    if not holdout or len(r) == 0:
        return 0.0
    gains = np.zeros(len(r), dtype=np.float64)
    for i, item in enumerate(r):
        if int(item) in holdout:
            gains[i] = 1.0
    discounts = 1.0 / np.log2(np.arange(2, len(r) + 2))
    dcg = float((gains * discounts).sum())
    ideal = min(len(holdout), k)
    idcg = float(discounts[:ideal].sum())
    return dcg / idcg if idcg else 0.0


def coverage(all_recs: Iterable[Iterable[int]], n_items: int) -> float:
    seen: set[int] = set()
    for r in all_recs:
        for x in r:
            seen.add(int(x))
    return len(seen) / float(max(n_items, 1))


def intra_list_similarity(rec_list: Iterable[int], item_vectors: np.ndarray) -> float:
    idx = _to_array(rec_list)
    if idx.shape[0] < 2:
        return 0.0
    V = item_vectors[idx]
    norms = np.linalg.norm(V, axis=1)
    norms[norms == 0] = 1.0
    V = V / norms[:, None]
    sims = V @ V.T
    iu = np.triu_indices(sims.shape[0], k=1)
    return float(sims[iu].mean())


def diversity(rec_list: Iterable[int], item_vectors: np.ndarray) -> float:
    return 1.0 - intra_list_similarity(rec_list, item_vectors)

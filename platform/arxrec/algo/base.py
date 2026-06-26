"""Recommender protocol + shared dataclass returned by every algorithm."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np


@dataclass
class RecResult:
    """A ranked list of recommended paper IDs with scores and reasons."""

    item_ids: list[int]
    scores: list[float]
    reasons: list[str] = field(default_factory=list)


@runtime_checkable
class Recommender(Protocol):
    name: str

    def similar_items(self, seed_id: int, k: int) -> RecResult: ...


def topk_indices(scores: np.ndarray, k: int) -> np.ndarray:
    """Return indices of top-k entries of ``scores`` in descending order.

    ``-inf`` entries are dropped from the result so the returned array can be
    shorter than ``k`` when not enough finite scores exist.
    """
    k = min(int(k), scores.shape[0])
    if k <= 0:
        return np.empty(0, dtype=np.int64)
    if k == scores.shape[0]:
        order = np.argsort(-scores, kind="stable")
    else:
        part = np.argpartition(-scores, k - 1)[:k]
        order = part[np.argsort(-scores[part], kind="stable")]
    finite = np.isfinite(scores[order])
    return order[finite]

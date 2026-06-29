"""Data-driven selection of the hybrid blend weights.

The shipped hybrid uses hand-set weights (neural 0.45, ALS 0.35, TF-IDF 0.15,
popularity 0.05). The evaluation shows TF-IDF is the strongest single model and
ALS the weakest, so those weights are worth questioning empirically rather than
defending by intuition. This module searches the weight simplex on a *held-out*
set of seeds and returns the blend that maximises NDCG@k, alongside the
incumbent weights' score so the change is justified by a measured delta.

The optimiser is pure: it consumes a per-seed candidate pool (the union of each
model's top items, with that model's already-normalised scores) plus the
held-out relevant items. Building that pool from trained models is the caller's
job (see ``build_candidates`` for the standard construction); keeping the search
itself free of model objects makes it fast and unit-testable.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np


@dataclass
class SeedCandidates:
    """One validation seed's candidate pool for blend scoring.

    ``item_ids`` are the candidate paper ids; ``scores`` maps each model name to
    a same-length array of that model's normalised scores over those candidates;
    ``relevant`` is the set of held-out items that count as hits.
    """

    item_ids: np.ndarray
    scores: dict[str, np.ndarray]
    relevant: set[int]


@dataclass
class WeightSearchResult:
    models: list[str]
    best_weights: dict[str, float]
    best_ndcg: float
    baseline_weights: dict[str, float]
    baseline_ndcg: float
    leaderboard: list[tuple[dict[str, float], float]] = field(default_factory=list)

    @property
    def improvement(self) -> float:
        return self.best_ndcg - self.baseline_ndcg


def _ndcg_from_hits(hit_flags: np.ndarray, n_relevant: int, k: int) -> float:
    r = hit_flags[:k]
    if n_relevant == 0 or r.size == 0:
        return 0.0
    discounts = 1.0 / np.log2(np.arange(2, r.size + 2))
    dcg = float((r * discounts).sum())
    ideal = min(n_relevant, k)
    idcg = float(discounts[:ideal].sum())
    return dcg / idcg if idcg else 0.0


def blend_ndcg(candidates: Sequence[SeedCandidates], weights: dict[str, float], k: int = 10) -> float:
    """Mean NDCG@k over candidates for a given weight vector."""
    if not candidates:
        return 0.0
    total = 0.0
    for c in candidates:
        blended = np.zeros(c.item_ids.shape[0], dtype=np.float64)
        for model, w in weights.items():
            if w:
                blended += w * c.scores[model]
        order = np.argsort(-blended, kind="stable")
        ranked = c.item_ids[order]
        hits = np.array([1.0 if int(x) in c.relevant else 0.0 for x in ranked], dtype=np.float64)
        total += _ndcg_from_hits(hits, len(c.relevant), k)
    return total / len(candidates)


def _simplex_grid(n: int, step: float) -> list[tuple[float, ...]]:
    """All weight vectors of length ``n`` on the simplex (sum=1) at the given step."""
    steps = int(round(1.0 / step))

    def rec(remaining: int, slots: int) -> list[list[int]]:
        if slots == 1:
            return [[remaining]]
        out: list[list[int]] = []
        for i in range(remaining + 1):
            for tail in rec(remaining - i, slots - 1):
                out.append([i, *tail])
        return out

    return [tuple(v / steps for v in combo) for combo in rec(steps, n)]


def grid_search_weights(
    candidates: Sequence[SeedCandidates],
    models: Sequence[str],
    *,
    baseline: dict[str, float],
    step: float = 0.05,
    k: int = 10,
    top_n: int = 10,
) -> WeightSearchResult:
    """Exhaustive simplex search for the NDCG@k-optimal blend weights."""
    model_list = list(models)
    scored: list[tuple[dict[str, float], float]] = []
    for combo in _simplex_grid(len(model_list), step):
        weights = dict(zip(model_list, combo, strict=True))
        scored.append((weights, blend_ndcg(candidates, weights, k)))
    scored.sort(key=lambda t: t[1], reverse=True)
    best_weights, best_ndcg = scored[0]
    return WeightSearchResult(
        models=model_list,
        best_weights=best_weights,
        best_ndcg=best_ndcg,
        baseline_weights=dict(baseline),
        baseline_ndcg=blend_ndcg(candidates, baseline, k),
        leaderboard=scored[:top_n],
    )

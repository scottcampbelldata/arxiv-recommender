"""Item-to-item evaluation.

The arXiv recommender is fundamentally a "papers like this paper" tool, so
the eval setup differs from a classic user-to-item evaluation:

For each held-out edge (citing -> cited), we ask: when we use ``citing`` as
the seed, does ``cited`` appear in the top-K? This is the standard
co-citation eval used in the academic-search literature. We then aggregate
Precision, Recall, MAP, and NDCG at K with bootstrap CIs.

The held-out set is built by removing 10% of citation edges before training
and using them as ground-truth at eval time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from arxrec.algo.base import Recommender
from arxrec.eval import metrics as M


@dataclass
class MetricCI:
    value: float
    ci_low: float
    ci_high: float


@dataclass
class EvalResult:
    algorithm: str
    k: int
    n_seeds_eval: int
    precision: MetricCI
    recall: MetricCI
    map_: MetricCI
    ndcg: MetricCI
    coverage: float
    diversity: float
    ils: float
    latency_p50_ms: float
    latency_p95_ms: float
    segments: dict[str, dict[str, float]] = field(default_factory=dict)

    def as_row(self) -> dict[str, float | str | int]:
        return {
            "algorithm": self.algorithm,
            "k": self.k,
            "n_seeds_eval": self.n_seeds_eval,
            "precision@k": self.precision.value,
            "recall@k": self.recall.value,
            "map@k": self.map_.value,
            "map_ci_lo": self.map_.ci_low,
            "map_ci_hi": self.map_.ci_high,
            "ndcg@k": self.ndcg.value,
            "ndcg_ci_lo": self.ndcg.ci_low,
            "ndcg_ci_hi": self.ndcg.ci_high,
            "coverage": self.coverage,
            "diversity": self.diversity,
            "ils": self.ils,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
        }


def _bootstrap_ci(values: np.ndarray, n_boot: int = 1000, alpha: float = 0.05, seed: int = 0) -> MetricCI:
    if values.size == 0:
        return MetricCI(0.0, 0.0, 0.0)
    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot, dtype=np.float64)
    n = values.size
    for i in range(n_boot):
        boot[i] = values[rng.integers(0, n, n)].mean()
    return MetricCI(
        float(values.mean()),
        float(np.quantile(boot, alpha / 2)),
        float(np.quantile(boot, 1 - alpha / 2)),
    )


def run_similar_items_eval(
    rec: Recommender,
    *,
    holdout: dict[int, set[int]],   # seed_paper_id -> set of cited paper ids held out
    n_items: int,
    item_vectors: np.ndarray | None = None,
    k: int = 10,
    max_seeds: int | None = None,
    seed: int = 0,
    cold_seeds: set[int] | None = None,
) -> EvalResult:
    seeds = sorted(holdout.keys())
    if max_seeds is not None and len(seeds) > max_seeds:
        rng = np.random.default_rng(seed)
        seeds = sorted(rng.choice(seeds, max_seeds, replace=False).tolist())

    per_p = np.empty(len(seeds), dtype=np.float64)
    per_r = np.empty(len(seeds), dtype=np.float64)
    per_ap = np.empty(len(seeds), dtype=np.float64)
    per_ndcg = np.empty(len(seeds), dtype=np.float64)
    rec_lists: list[list[int]] = []
    latencies: list[float] = []

    for i, s in enumerate(seeds):
        held = holdout[s]
        t0 = time.perf_counter()
        r = rec.similar_items(int(s), k)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        per_p[i] = M.precision_at_k(r.item_ids, held, k)
        per_r[i] = M.recall_at_k(r.item_ids, held, k)
        per_ap[i] = M.average_precision_at_k(r.item_ids, held, k)
        per_ndcg[i] = M.ndcg_at_k(r.item_ids, held, k)
        rec_lists.append(list(r.item_ids))

    cov = M.coverage(rec_lists, n_items)
    if item_vectors is not None:
        ils_vals = [M.intra_list_similarity(rl, item_vectors) for rl in rec_lists if len(rl) >= 2]
        ils = float(np.mean(ils_vals)) if ils_vals else 0.0
        div = 1.0 - ils
    else:
        ils = 0.0
        div = 0.0

    segments: dict[str, dict[str, float]] = {}
    if cold_seeds:
        mask = np.array([int(s) in cold_seeds for s in seeds])
        if mask.any():
            segments["cold_seed"] = {
                "precision@k": float(per_p[mask].mean()),
                "recall@k": float(per_r[mask].mean()),
                "map@k": float(per_ap[mask].mean()),
                "ndcg@k": float(per_ndcg[mask].mean()),
                "n": int(mask.sum()),
            }
        warm = ~mask
        if warm.any():
            segments["warm_seed"] = {
                "precision@k": float(per_p[warm].mean()),
                "recall@k": float(per_r[warm].mean()),
                "map@k": float(per_ap[warm].mean()),
                "ndcg@k": float(per_ndcg[warm].mean()),
                "n": int(warm.sum()),
            }

    lat = np.asarray(latencies, dtype=np.float64)
    return EvalResult(
        algorithm=rec.name,
        k=k,
        n_seeds_eval=len(seeds),
        precision=_bootstrap_ci(per_p, seed=seed),
        recall=_bootstrap_ci(per_r, seed=seed + 1),
        map_=_bootstrap_ci(per_ap, seed=seed + 2),
        ndcg=_bootstrap_ci(per_ndcg, seed=seed + 3),
        coverage=cov,
        diversity=div,
        ils=ils,
        segments=segments,
        latency_p50_ms=float(np.quantile(lat, 0.5)) if lat.size else 0.0,
        latency_p95_ms=float(np.quantile(lat, 0.95)) if lat.size else 0.0,
    )

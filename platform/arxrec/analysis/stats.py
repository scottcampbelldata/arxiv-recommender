"""Pure reductions over a behavioural sample.

Every function here is deterministic and dependency-light (numpy only) so the
case study's numbers are reproducible and unit-testable without a running API,
a database, or the model artefacts. A "record" is one seed paper's result:

    {
        "seed": int,
        "meta": {"cited_by_count": int, "publication_year": int | None,
                 "primary_topic": str | None},
        "recs": {algo: [item_id, ...]},      # top-k ids per algorithm
        "latency_ms": {algo: float},
    }

These match the JSON written by :mod:`arxrec.analysis.collect`.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def jaccard(a: Sequence[int], b: Sequence[int]) -> float:
    """Jaccard overlap between two recommendation lists (order ignored)."""
    sa, sb = set(a), set(b)
    union = sa | sb
    return len(sa & sb) / len(union) if union else 0.0


def mean_overlap_matrix(
    records: Sequence[dict], algos: Sequence[str]
) -> tuple[np.ndarray, list[str]]:
    """Mean pairwise Jaccard overlap between every pair of algorithms.

    Returns a symmetric ``(n_algos, n_algos)`` matrix (diagonal = 1.0) and the
    ordered label list. A record contributes to an algorithm pair only when it
    has a non-empty list for both, so partial failures do not bias the mean.
    """
    labels = list(algos)
    n = len(labels)
    mat = np.eye(n, dtype=np.float64)
    for i in range(n):
        for j in range(i + 1, n):
            vals = [
                jaccard(r["recs"][labels[i]], r["recs"][labels[j]])
                for r in records
                if r["recs"].get(labels[i]) and r["recs"].get(labels[j])
            ]
            m = float(np.mean(vals)) if vals else 0.0
            mat[i, j] = mat[j, i] = m
    return mat, labels


def hybrid_attribution(
    records: Sequence[dict], hybrid: str, bases: Sequence[str]
) -> dict[str, float]:
    """Mean Jaccard overlap of the hybrid's picks with each base model.

    This is the "what does the blend actually inherit" measurement: a high
    number means the hybrid's output looks like that base model regardless of
    the nominal blend weights.
    """
    out: dict[str, float] = {}
    for b in bases:
        vals = [
            jaccard(r["recs"][hybrid], r["recs"][b])
            for r in records
            if r["recs"].get(hybrid) and r["recs"].get(b)
        ]
        out[b] = float(np.mean(vals)) if vals else 0.0
    return out


def gini(values: Sequence[float]) -> float:
    """Gini coefficient of a non-negative distribution (0 = uniform, 1 = all mass on one point).

    Used to quantify how concentrated an algorithm's recommendations are across
    the catalogue: a model that keeps recommending the same popular papers has a
    high Gini, a model that spreads attention has a low one.
    """
    x = np.asarray(values, dtype=np.float64)
    if x.size == 0 or x.sum() == 0:
        return 0.0
    if np.any(x < 0):
        raise ValueError("gini is undefined for negative values")
    x = np.sort(x)
    n = x.size
    index = np.arange(1, n + 1)
    return float((np.sum((2 * index - n - 1) * x)) / (n * x.sum()))


def recommendation_frequencies(records: Sequence[dict], algo: str) -> dict[int, int]:
    """Count how many times each item is recommended across all seeds, for one algorithm."""
    counts: dict[int, int] = {}
    for r in records:
        for item in r["recs"].get(algo, []):
            counts[item] = counts.get(item, 0) + 1
    return counts


def recommendation_concentration(
    records: Sequence[dict], algo: str, n_catalogue: int
) -> dict[str, float]:
    """Concentration summary for one algorithm over the sampled seeds.

    - ``gini``: inequality of the recommendation-frequency distribution.
    - ``unique_items``: distinct papers ever recommended.
    - ``catalogue_coverage``: ``unique_items / n_catalogue``.
    - ``top1pct_share``: fraction of all recommendation slots captured by the
      most-recommended 1% of items (a popularity-bias tell).
    """
    counts = recommendation_frequencies(records, algo)
    if not counts:
        return {"gini": 0.0, "unique_items": 0.0, "catalogue_coverage": 0.0, "top1pct_share": 0.0}
    freqs = np.array(sorted(counts.values(), reverse=True), dtype=np.float64)
    total = float(freqs.sum())
    top_n = max(1, int(round(len(freqs) * 0.01)))
    return {
        "gini": gini(freqs),
        "unique_items": float(len(freqs)),
        "catalogue_coverage": len(freqs) / float(max(n_catalogue, 1)),
        "top1pct_share": float(freqs[:top_n].sum() / total) if total else 0.0,
    }


def cold_warm_split(records: Sequence[dict], threshold: int) -> tuple[list[dict], list[dict]]:
    """Partition records into (cold, warm) by the seed's ``cited_by_count``.

    Cold seeds (``cited_by_count < threshold``) are the hard case for any model
    that leans on the citation graph; reporting them separately is how cold-start
    behaviour is made visible rather than averaged away.
    """
    cold = [r for r in records if int(r["meta"].get("cited_by_count") or 0) < threshold]
    warm = [r for r in records if int(r["meta"].get("cited_by_count") or 0) >= threshold]
    return cold, warm

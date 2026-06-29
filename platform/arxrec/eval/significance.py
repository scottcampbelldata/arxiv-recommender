"""Paired significance testing between two recommenders.

A leaderboard of point estimates cannot tell you whether model A is *reliably*
better than model B or whether the gap is sampling noise. Because every model
is evaluated on the *same* seeds, the right tool is a paired test: resample
seeds (not models), recompute the mean difference on each resample, and read
the confidence interval and two-sided p-value off the bootstrap distribution.
This is the same bootstrap machinery the leaderboard already uses for its CIs,
applied to per-seed *differences*.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass
class DiffResult:
    """Paired comparison of metric ``a`` minus metric ``b``."""

    mean_diff: float
    ci_low: float
    ci_high: float
    p_value: float
    n: int

    @property
    def significant(self) -> bool:
        """True when the 95% CI for the difference excludes zero."""
        return self.ci_low > 0.0 or self.ci_high < 0.0


def paired_bootstrap_diff(
    a: Sequence[float],
    b: Sequence[float],
    *,
    n_boot: int = 10000,
    alpha: float = 0.05,
    seed: int = 0,
) -> DiffResult:
    """Bootstrap the paired difference ``mean(a) - mean(b)`` over shared seeds.

    ``a`` and ``b`` are per-seed metric values (e.g. NDCG@10) for two models,
    aligned position-by-position to the same seeds. The two-sided p-value is the
    standard bootstrap approximation: twice the smaller tail mass of the
    resampled differences around zero, clipped to [0, 1].
    """
    arr_a = np.asarray(a, dtype=np.float64)
    arr_b = np.asarray(b, dtype=np.float64)
    if arr_a.shape != arr_b.shape:
        raise ValueError(f"paired arrays must align: {arr_a.shape} vs {arr_b.shape}")
    n = arr_a.size
    if n == 0:
        return DiffResult(0.0, 0.0, 0.0, 1.0, 0)

    diff = arr_a - arr_b
    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot, dtype=np.float64)
    for i in range(n_boot):
        boot[i] = diff[rng.integers(0, n, n)].mean()

    mean_diff = float(diff.mean())
    ci_low = float(np.quantile(boot, alpha / 2))
    ci_high = float(np.quantile(boot, 1 - alpha / 2))
    # Two-sided bootstrap p-value: smaller tail mass around zero, doubled.
    tail = min(float(np.mean(boot <= 0.0)), float(np.mean(boot >= 0.0)))
    p_value = float(min(1.0, 2.0 * tail))
    return DiffResult(mean_diff, ci_low, ci_high, p_value, n)

"""Tests for the behavioural-analysis reductions."""

from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from arxrec.analysis.stats import (
    cold_warm_split,
    gini,
    hybrid_attribution,
    jaccard,
    mean_overlap_matrix,
    recommendation_concentration,
)


def _rec(seed, cited, recs):
    return {"seed": seed, "meta": {"cited_by_count": cited}, "recs": recs, "latency_ms": {}}


def test_jaccard_known_values():
    assert jaccard([1, 2, 3], [1, 2, 3]) == 1.0
    assert jaccard([1, 2], [3, 4]) == 0.0
    assert jaccard([1, 2, 3, 4], [3, 4, 5, 6]) == 2 / 6
    assert jaccard([], []) == 0.0


def test_overlap_matrix_is_symmetric_with_unit_diagonal():
    records = [
        _rec(1, 10, {"a": [1, 2, 3], "b": [2, 3, 4]}),
        _rec(2, 10, {"a": [5, 6], "b": [5, 9]}),
    ]
    mat, labels = mean_overlap_matrix(records, ["a", "b"])
    assert labels == ["a", "b"]
    assert mat[0, 0] == 1.0 and mat[1, 1] == 1.0
    assert math.isclose(mat[0, 1], mat[1, 0])
    # seed1: |{2,3}|/|{1,2,3,4}| = 0.5 ; seed2: |{5}|/|{5,6,9}| = 1/3
    assert math.isclose(mat[0, 1], (0.5 + 1 / 3) / 2)


def test_hybrid_attribution_picks_the_dominant_base():
    records = [_rec(1, 10, {"hybrid": [1, 2, 3], "x": [1, 2, 3], "y": [7, 8, 9]})]
    attr = hybrid_attribution(records, "hybrid", ["x", "y"])
    assert attr["x"] == 1.0
    assert attr["y"] == 0.0


def test_gini_bounds_and_extremes():
    assert gini([1, 1, 1, 1]) == 0.0  # perfectly uniform
    # all mass on one point -> approaches (n-1)/n
    g = gini([0, 0, 0, 10])
    assert 0.7 < g <= 1.0
    assert gini([]) == 0.0


@given(
    vals=st.lists(st.floats(min_value=0, max_value=1e6, allow_nan=False), min_size=1, max_size=50)
)
@settings(max_examples=200, deadline=None)
def test_gini_bounded(vals):
    assert 0.0 <= gini(vals) <= 1.0 + 1e-9


def test_concentration_flags_repeated_recommendations():
    # model "hot" keeps recommending the same two papers; "spread" never repeats
    records = [_rec(i, 10, {"hot": [1, 2], "spread": [i * 2, i * 2 + 1]}) for i in range(20)]
    hot = recommendation_concentration(records, "hot", n_catalogue=1000)
    spread = recommendation_concentration(records, "spread", n_catalogue=1000)
    assert hot["unique_items"] == 2
    assert spread["unique_items"] == 40
    assert hot["catalogue_coverage"] < spread["catalogue_coverage"]


def test_cold_warm_split_partitions_by_citations():
    records = [_rec(1, 0, {}), _rec(2, 2, {}), _rec(3, 50, {})]
    cold, warm = cold_warm_split(records, threshold=3)
    assert [r["seed"] for r in cold] == [1, 2]
    assert [r["seed"] for r in warm] == [3]
    assert len(cold) + len(warm) == len(records)

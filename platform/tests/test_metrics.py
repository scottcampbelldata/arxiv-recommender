"""Property-based tests on the ranking metrics."""

from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from arxrec.eval.metrics import (
    average_precision_at_k,
    coverage,
    hit_rate_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def test_precision_known_value():
    assert precision_at_k([1, 2, 3, 4, 5], {1, 2, 3}, 5) == 3 / 5


def test_recall_known_value():
    assert recall_at_k([1, 2, 3, 4, 5], {1, 6, 7}, 5) == 1 / 3


def test_ap_known_value():
    assert math.isclose(average_precision_at_k([1, 2, 3], {1, 3}, 3), (1.0 + 2 / 3) / 2, abs_tol=1e-9)


def test_ndcg_perfect_is_one():
    assert math.isclose(ndcg_at_k([1, 2, 3], {1, 2, 3}, 3), 1.0, abs_tol=1e-9)


def test_hit_rate_known_values():
    assert hit_rate_at_k([1, 2, 3], {3, 9}, 3) == 1.0
    assert hit_rate_at_k([1, 2, 3], {9}, 3) == 0.0
    # a hit beyond k does not count
    assert hit_rate_at_k([1, 2, 3, 4], {4}, 3) == 0.0


def test_empty_inputs():
    assert precision_at_k([], {1}, 5) == 0.0
    assert recall_at_k([1], set(), 5) == 0.0
    assert ndcg_at_k([], set(), 5) == 0.0
    assert hit_rate_at_k([], {1}, 5) == 0.0
    assert hit_rate_at_k([1], set(), 5) == 0.0


def test_coverage_basic():
    assert coverage([[0, 1], [2, 3]], n_items=4) == 1.0
    assert coverage([[0, 1], [2, 3]], n_items=8) == 0.5


item_strategy = st.integers(min_value=0, max_value=500)
unique_list = st.lists(item_strategy, min_size=0, max_size=20, unique=True)


@given(recs=unique_list, holdout=st.sets(item_strategy, min_size=0, max_size=20),
       k=st.integers(min_value=1, max_value=20))
@settings(max_examples=200, deadline=None)
def test_all_metrics_bounded_zero_one(recs, holdout, k):
    assert 0.0 <= precision_at_k(recs, holdout, k) <= 1.0
    assert 0.0 <= recall_at_k(recs, holdout, k) <= 1.0
    assert 0.0 <= average_precision_at_k(recs, holdout, k) <= 1.0
    assert 0.0 <= ndcg_at_k(recs, holdout, k) <= 1.0 + 1e-9
    assert hit_rate_at_k(recs, holdout, k) in (0.0, 1.0)

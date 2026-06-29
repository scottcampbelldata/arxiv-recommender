"""Tests for the paired bootstrap significance test."""

from __future__ import annotations

import numpy as np
import pytest

from arxrec.eval.significance import paired_bootstrap_diff


def test_clear_difference_is_significant():
    rng = np.random.default_rng(0)
    a = rng.uniform(0.4, 0.6, size=400)
    b = a - 0.1  # a is uniformly better by 0.1 on every paired seed
    res = paired_bootstrap_diff(a, b, seed=1)
    assert res.mean_diff > 0.09
    assert res.significant
    assert res.p_value < 0.05
    assert res.ci_low > 0.0


def test_no_difference_is_not_significant():
    rng = np.random.default_rng(2)
    a = rng.uniform(0.0, 1.0, size=300)
    b = a.copy()  # identical -> zero difference
    res = paired_bootstrap_diff(a, b, seed=3)
    assert res.mean_diff == 0.0
    assert not res.significant
    assert res.p_value >= 0.05


def test_ci_brackets_the_mean_difference():
    rng = np.random.default_rng(4)
    a = rng.normal(0.5, 0.1, size=200)
    b = rng.normal(0.45, 0.1, size=200)
    res = paired_bootstrap_diff(a, b, seed=5)
    assert res.ci_low <= res.mean_diff <= res.ci_high


def test_mismatched_shapes_raise():
    with pytest.raises(ValueError):
        paired_bootstrap_diff([0.1, 0.2], [0.1], seed=0)


def test_empty_is_handled():
    res = paired_bootstrap_diff([], [], seed=0)
    assert res.n == 0 and res.p_value == 1.0 and not res.significant

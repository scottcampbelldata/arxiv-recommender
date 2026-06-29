"""Tests for the data-driven blend weight search."""

from __future__ import annotations

import numpy as np

from arxrec.eval.tune_weights import (
    SeedCandidates,
    blend_ndcg,
    grid_search_weights,
)

MODELS = ["good", "bad"]


def _candidates_where_good_model_wins(n_seeds: int = 30) -> list[SeedCandidates]:
    """Build a pool with graded relevance where the 'good' model ranks the
    relevant items high and the 'bad' model buries them under distractors, so
    NDCG@k increases monotonically with the good model's weight and the optimum
    is sharply at all-good (not a flat tie)."""
    rng = np.random.default_rng(0)
    cands = []
    for _ in range(n_seeds):
        items = np.arange(20)
        relevant = {0, 1, 2}
        good = rng.uniform(0.0, 0.3, size=20)
        good[[0, 1, 2]] = [1.0, 0.95, 0.9]  # good ranks the relevant items at the top
        bad = rng.uniform(0.7, 1.0, size=20)
        bad[[0, 1, 2]] = [0.0, 0.05, 0.1]  # bad ranks distractors above them
        cands.append(SeedCandidates(item_ids=items, scores={"good": good, "bad": bad}, relevant=relevant))
    return cands


def test_blend_ndcg_rewards_the_informative_model():
    cands = _candidates_where_good_model_wins()
    all_good = blend_ndcg(cands, {"good": 1.0, "bad": 0.0}, k=10)
    all_bad = blend_ndcg(cands, {"good": 0.0, "bad": 1.0}, k=10)
    assert all_good > all_bad
    assert all_good == 1.0  # relevant items occupy the top ranks


def test_grid_search_recovers_the_better_model():
    cands = _candidates_where_good_model_wins()
    res = grid_search_weights(
        cands, MODELS, baseline={"good": 0.5, "bad": 0.5}, step=0.1, k=10
    )
    # the better model should dominate the optimal blend
    assert res.best_weights["good"] >= res.best_weights["bad"]
    assert res.best_ndcg == 1.0
    assert res.best_ndcg >= res.baseline_ndcg
    assert res.improvement >= 0.0


def test_grid_weights_form_a_simplex():
    cands = _candidates_where_good_model_wins(n_seeds=5)
    res = grid_search_weights(cands, MODELS, baseline={"good": 0.5, "bad": 0.5}, step=0.25, k=5)
    for weights, _ in res.leaderboard:
        assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_empty_candidates_score_zero():
    assert blend_ndcg([], {"good": 1.0, "bad": 0.0}, k=10) == 0.0

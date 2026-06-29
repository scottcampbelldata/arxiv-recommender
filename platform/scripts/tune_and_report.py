"""Run the blend-weight search and the hybrid-vs-TF-IDF significance test
against the trained models, and write a JSON report.

Unlike ``arxrec.train`` this does NOT retrain: it loads the existing pickled
models and the dataset holdout, so it is cheap to run after a normal training
run. It answers the two questions the case study leaves open, using a proper
split: the eval seeds are partitioned into disjoint validation and test folds,
weights are tuned on validation, and the gain is measured on test.

  1. What blend weights maximise NDCG@k (tuned on the validation fold), and how
     much do they beat the original weights *out-of-sample* on the test fold?
  2. Is the deployed hybrid's accuracy gain over TF-IDF statistically
     significant on the test fold (paired bootstrap over seeds)?

Run from ``platform`` with the project venv::

    python scripts/tune_and_report.py --max-seeds 2000 --out data/models/tuning_report.json
"""

from __future__ import annotations

import argparse
import json
import pickle

import numpy as np

from arxrec.config import SETTINGS
from arxrec.data.dataset import build_dataset
from arxrec.eval import run_similar_items_eval
from arxrec.eval.significance import paired_bootstrap_diff
from arxrec.eval.tune_weights import blend_ndcg, build_candidates, grid_search_weights

MODELS = ["neural", "als", "tfidf", "popularity"]
# Original hand-set weights, kept as the comparison baseline so the report shows
# the gain over the configuration that motivated this analysis. The tuned optimum
# is now the default in arxrec.algo.hybrid.
SHIPPED = {"neural": 0.45, "als": 0.35, "tfidf": 0.15, "popularity": 0.05}


def _load(name: str):
    # Loads our own training artefacts (same pickles arxrec.train writes and the
    # API loads at startup); the path is operator-controlled, not user input.
    with open(SETTINGS.data_models / f"{name}.pkl", "rb") as fh:
        return pickle.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--max-seeds", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260625)
    ap.add_argument("--step", type=float, default=0.05, help="weight-simplex grid step")
    ap.add_argument("--pool-per-model", type=int, default=50)
    ap.add_argument("--val-frac", type=float, default=0.5, help="fraction of seeds used to tune weights")
    ap.add_argument("--out", default="data/models/tuning_report.json")
    args = ap.parse_args()

    ds = build_dataset(seed=args.seed)
    hybrid = _load("hybrid")

    # Deterministic seed sample, then split into disjoint validation / test folds.
    # Weights are tuned on validation ONLY; the reported gain is measured on the
    # held-out test fold, so it is an honest out-of-sample estimate.
    seeds = sorted(ds.test_holdout.keys())
    rng = np.random.default_rng(args.seed)
    if len(seeds) > args.max_seeds:
        seeds = sorted(int(s) for s in rng.choice(seeds, args.max_seeds, replace=False))
    shuffled = rng.permutation(seeds)
    n_val = int(len(shuffled) * args.val_frac)
    val_seeds = sorted(int(s) for s in shuffled[:n_val])
    test_seeds = sorted(int(s) for s in shuffled[n_val:])

    # 1) Tune weights on the VALIDATION fold.
    val_cands = build_candidates(
        hybrid.component_scores, val_seeds, ds.test_holdout,
        models=MODELS, pool_per_model=args.pool_per_model,
    )
    search = grid_search_weights(val_cands, MODELS, baseline=SHIPPED, step=args.step, k=args.k)

    # 2) Measure the chosen weights on the held-out TEST fold (out-of-sample).
    test_cands = build_candidates(
        hybrid.component_scores, test_seeds, ds.test_holdout,
        models=MODELS, pool_per_model=args.pool_per_model,
    )
    test_ndcg_original = blend_ndcg(test_cands, SHIPPED, k=args.k)
    test_ndcg_tuned = blend_ndcg(test_cands, search.best_weights, k=args.k)

    # 3) Significance of the deployed hybrid vs TF-IDF, paired over the test fold.
    holdout = {s: ds.test_holdout[s] for s in test_seeds}
    tfidf = hybrid.tfidf
    ev_hyb = run_similar_items_eval(hybrid, holdout=holdout, n_items=ds.n_papers, k=args.k, seed=args.seed)
    ev_tf = run_similar_items_eval(tfidf, holdout=holdout, n_items=ds.n_papers, k=args.k, seed=args.seed)
    diff = paired_bootstrap_diff(ev_hyb.per_seed["ndcg"], ev_tf.per_seed["ndcg"], seed=args.seed)

    report = {
        "k": args.k,
        "n_val_seeds": len(val_seeds),
        "n_test_seeds": len(test_seeds),
        "weight_search": {
            "tuned_on": "validation fold",
            "original_weights": SHIPPED,
            "best_weights": {m: round(w, 3) for m, w in search.best_weights.items()},
            "val_ndcg_original": round(search.baseline_ndcg, 4),
            "val_ndcg_tuned": round(search.best_ndcg, 4),
            "test_ndcg_original": round(test_ndcg_original, 4),
            "test_ndcg_tuned": round(test_ndcg_tuned, 4),
            "out_of_sample_improvement": round(test_ndcg_tuned - test_ndcg_original, 4),
            "top_blends": [
                {"weights": {m: round(w, 3) for m, w in wts.items()}, "val_ndcg": round(nd, 4)}
                for wts, nd in search.leaderboard
            ],
        },
        "hybrid_vs_tfidf_ndcg_testfold": {
            "hybrid_ndcg": round(ev_hyb.ndcg.value, 4),
            "tfidf_ndcg": round(ev_tf.ndcg.value, 4),
            "mean_diff": round(diff.mean_diff, 4),
            "ci_low": round(diff.ci_low, 4),
            "ci_high": round(diff.ci_high, 4),
            "p_value": round(diff.p_value, 5),
            "significant": diff.significant,
        },
    }
    out = SETTINGS.data_models / args.out if not args.out.startswith("/") else args.out
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

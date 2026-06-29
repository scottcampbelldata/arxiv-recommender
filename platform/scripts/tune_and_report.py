"""Run the blend-weight search and the hybrid-vs-TF-IDF significance test
against the trained models, and write a JSON report.

Unlike ``arxrec.train`` this does NOT retrain: it loads the existing pickled
models and the dataset holdout, so it is cheap to run after a normal training
run. It answers the two questions the case study leaves open:

  1. What blend weights maximise NDCG@k on held-out citations, and how much do
     they beat the shipped weights?
  2. Is the hybrid's accuracy gain over TF-IDF statistically significant
     (paired bootstrap over seeds)?

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
from arxrec.eval.tune_weights import build_candidates, grid_search_weights

MODELS = ["neural", "als", "tfidf", "popularity"]
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
    ap.add_argument("--out", default="data/models/tuning_report.json")
    args = ap.parse_args()

    ds = build_dataset(seed=args.seed)
    hybrid = _load("hybrid")

    # Deterministic seed sample, shared by the search and the significance test.
    seeds = sorted(ds.test_holdout.keys())
    rng = np.random.default_rng(args.seed)
    if len(seeds) > args.max_seeds:
        seeds = sorted(int(s) for s in rng.choice(seeds, args.max_seeds, replace=False))

    # 1) Weight search on the held-out citation pool.
    cands = build_candidates(
        hybrid.component_scores, seeds, ds.test_holdout,
        models=MODELS, pool_per_model=args.pool_per_model,
    )
    search = grid_search_weights(cands, MODELS, baseline=SHIPPED, step=args.step, k=args.k)

    # 2) Significance of hybrid vs TF-IDF, paired over the same seeds.
    holdout = {s: ds.test_holdout[s] for s in seeds}
    tfidf = hybrid.tfidf
    ev_hyb = run_similar_items_eval(hybrid, holdout=holdout, n_items=ds.n_papers, k=args.k, seed=args.seed)
    ev_tf = run_similar_items_eval(tfidf, holdout=holdout, n_items=ds.n_papers, k=args.k, seed=args.seed)
    diff = paired_bootstrap_diff(ev_hyb.per_seed["ndcg"], ev_tf.per_seed["ndcg"], seed=args.seed)

    report = {
        "k": args.k,
        "n_seeds": len(seeds),
        "weight_search": {
            "shipped_weights": search.baseline_weights,
            "shipped_ndcg": round(search.baseline_ndcg, 4),
            "best_weights": {m: round(w, 3) for m, w in search.best_weights.items()},
            "best_ndcg": round(search.best_ndcg, 4),
            "improvement": round(search.improvement, 4),
            "top_blends": [
                {"weights": {m: round(w, 3) for m, w in wts.items()}, "ndcg": round(nd, 4)}
                for wts, nd in search.leaderboard
            ],
        },
        "hybrid_vs_tfidf_ndcg": {
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

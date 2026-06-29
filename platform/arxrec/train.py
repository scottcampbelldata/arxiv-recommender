"""End-to-end training + evaluation entry point.

Run with::

    python -m arxrec.train --max-eval-seeds 1500 --k 10

Writes model artefacts to ``data/models/`` and logs metrics to
``ml.model_run`` + ``ml.eval_metric`` in Postgres.
"""

from __future__ import annotations

import argparse
import json
import pickle
import time

import numpy as np
import psycopg

from arxrec.algo import (
    CitationALSRecommender,
    HybridRecommender,
    NeuralEmbeddingRecommender,
    PopularityRecommender,
    TfidfRecommender,
)
from arxrec.config import SETTINGS
from arxrec.data.dataset import build_dataset
from arxrec.eval import run_similar_items_eval
from arxrec.utils.logging import configure_logging, get_logger
from arxrec.utils.seed import seed_all

LOG = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--max-eval-seeds", type=int, default=1500)
    p.add_argument("--seed", type=int, default=SETTINGS.seed)
    p.add_argument("--skip-neural", action="store_true",
                   help="Skip sentence-transformer encoding (much faster smoke).")
    p.add_argument("--algorithms", nargs="*",
                   default=["popularity", "tfidf", "neural", "als", "hybrid"])
    return p.parse_args()


def _persist_run(algo: str, params: dict, artifact: str | None, eval_result) -> int:
    with psycopg.connect(SETTINGS.dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ml.model_run (algorithm, params, artifact, notes) "
            "VALUES (%s, %s, %s, %s) RETURNING run_id",
            (algo, json.dumps(params), artifact, json.dumps(eval_result.segments)),
        )
        run_id = int(cur.fetchone()[0])
        rows = [
            (run_id, "precision", eval_result.k, eval_result.precision.value, eval_result.precision.ci_low, eval_result.precision.ci_high, "all"),
            (run_id, "recall", eval_result.k, eval_result.recall.value, eval_result.recall.ci_low, eval_result.recall.ci_high, "all"),
            (run_id, "map", eval_result.k, eval_result.map_.value, eval_result.map_.ci_low, eval_result.map_.ci_high, "all"),
            (run_id, "ndcg", eval_result.k, eval_result.ndcg.value, eval_result.ndcg.ci_low, eval_result.ndcg.ci_high, "all"),
            (run_id, "hit_rate", eval_result.k, eval_result.hit_rate.value, eval_result.hit_rate.ci_low, eval_result.hit_rate.ci_high, "all"),
            (run_id, "coverage", eval_result.k, eval_result.coverage, None, None, "all"),
            (run_id, "diversity", eval_result.k, eval_result.diversity, None, None, "all"),
            (run_id, "ils", eval_result.k, eval_result.ils, None, None, "all"),
            (run_id, "latency_p50_ms", eval_result.k, eval_result.latency_p50_ms, None, None, "all"),
            (run_id, "latency_p95_ms", eval_result.k, eval_result.latency_p95_ms, None, None, "all"),
        ]
        for seg, metrics in eval_result.segments.items():
            for m_name, val in metrics.items():
                if m_name == "n":
                    continue
                rows.append((run_id, m_name.replace("@k", ""), eval_result.k, float(val), None, None, seg))
        cur.executemany(
            "INSERT INTO ml.eval_metric (run_id, metric, k, value, ci_low, ci_high, segment) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (run_id, metric, k, segment) DO UPDATE SET value = EXCLUDED.value",
            rows,
        )
    return run_id


def main() -> int:
    configure_logging(SETTINGS.log_level)
    args = parse_args()
    seed_all(args.seed)

    LOG.info("training.start", seed=args.seed)
    t0 = time.perf_counter()
    ds = build_dataset(seed=args.seed)
    LOG.info(
        "dataset.built",
        n_papers=ds.n_papers,
        n_train_edges=len(ds.train_edges),
        n_test_seeds=len(ds.test_holdout),
        cold_seeds=len(ds.cold_seeds),
        seconds=round(time.perf_counter() - t0, 1),
    )

    SETTINGS.data_models.mkdir(parents=True, exist_ok=True)
    fitted: dict[str, object] = {}

    if "popularity" in args.algorithms:
        t = time.perf_counter()
        pop = PopularityRecommender()
        pop.fit(
            ds.papers["cited_by_count"].to_numpy(),
            publication_year=ds.papers["publication_year"].to_numpy(),
        )
        fitted["popularity"] = pop
        LOG.info("trained.popularity", seconds=round(time.perf_counter() - t, 1))

    if "tfidf" in args.algorithms or "hybrid" in args.algorithms:
        t = time.perf_counter()
        tfidf = TfidfRecommender(max_features=80_000)
        tfidf.fit(ds.papers)
        fitted["tfidf"] = tfidf
        LOG.info("trained.tfidf", seconds=round(time.perf_counter() - t, 1))

    if "als" in args.algorithms or "hybrid" in args.algorithms:
        t = time.perf_counter()
        ui = CitationALSRecommender.build_user_item(ds.train_edges, ds.n_papers)
        als = CitationALSRecommender(factors=96, iterations=18, alpha=8.0,
                                       random_state=args.seed)
        als.fit(ui)
        fitted["als"] = als
        LOG.info("trained.als", seconds=round(time.perf_counter() - t, 1))

    if ("neural" in args.algorithms or "hybrid" in args.algorithms) and not args.skip_neural:
        t = time.perf_counter()
        neural = NeuralEmbeddingRecommender()
        neural.fit(ds.papers)
        fitted["neural"] = neural
        np.save(SETTINGS.data_models / "neural_vectors.npy", neural.vectors)
        LOG.info("trained.neural", seconds=round(time.perf_counter() - t, 1))

    if "hybrid" in args.algorithms and all(k in fitted for k in ("popularity", "tfidf", "als")):
        # Neural is optional in the hybrid; build a dummy zero-weight neural
        # if it's missing so the eval still runs.
        neural = fitted.get("neural")
        if neural is None:
            neural = NeuralEmbeddingRecommender()
            neural.load_vectors(np.zeros((ds.n_papers, 8), dtype=np.float32))
            fitted["neural"] = neural
        hyb = HybridRecommender(
            als=fitted["als"],        # type: ignore[arg-type]
            neural=neural,            # type: ignore[arg-type]
            tfidf=fitted["tfidf"],    # type: ignore[arg-type]
            popularity=fitted["popularity"],  # type: ignore[arg-type]
        )
        fitted["hybrid"] = hyb

    item_vectors_for_ils = (
        fitted["als"].item_factors if "als" in fitted else None  # type: ignore[union-attr]
    )

    leaderboard = []
    for name, model in fitted.items():
        t = time.perf_counter()
        result = run_similar_items_eval(
            model,                       # type: ignore[arg-type]
            holdout=ds.test_holdout,
            n_items=ds.n_papers,
            item_vectors=item_vectors_for_ils,
            k=args.k,
            max_seeds=args.max_eval_seeds,
            seed=args.seed,
            cold_seeds=ds.cold_seeds,
        )
        LOG.info(
            "evaluated",
            algorithm=name,
            map_at_k=round(result.map_.value, 4),
            ndcg_at_k=round(result.ndcg.value, 4),
            recall_at_k=round(result.recall.value, 4),
            coverage=round(result.coverage, 3),
            latency_p50_ms=round(result.latency_p50_ms, 2),
            seconds=round(time.perf_counter() - t, 1),
        )
        artifact = None
        try:
            artifact = str(SETTINGS.data_models / f"{name}.pkl")
            with open(artifact, "wb") as f:
                pickle.dump(model, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as exc:
            LOG.warning("artifact.save_failed", algorithm=name, error=str(exc))
        run_id = _persist_run(name, {"k": args.k, "seed": args.seed}, artifact, result)
        row = result.as_row()
        row["run_id"] = run_id
        leaderboard.append(row)

    out = SETTINGS.data_models / "leaderboard.json"
    out.write_text(json.dumps(leaderboard, indent=2))
    LOG.info("leaderboard.written", path=str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

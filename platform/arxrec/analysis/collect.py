"""Sample online recommendation behaviour from a running arxrec API.

This deliberately uses only the public HTTP surface (``/healthz``,
``/papers/{id}``, ``/similar/{id}``) and the standard library, so it runs
against the live deployment without database credentials or the model
artefacts. The output is a single JSON document that
:mod:`arxrec.analysis.stats` and the case-study figures consume.

Usage::

    python -m arxrec.analysis.collect --base-url https://api.papers.scottcampbell.io \
        --n-seeds 200 --out docs/analysis/data/behavioral_sample.json
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import numpy as np

DEFAULT_ALGOS = ("popularity", "tfidf", "neural", "als", "hybrid")
DEFAULT_BASE_URL = "https://api.papers.scottcampbell.io"


def _get_json(url: str, *, timeout: float, retries: int = 2) -> Any:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            last = exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
        time.sleep(0.5 * (attempt + 1))
    if last is not None:
        raise last
    return None


def _sample_seed_ids(n_papers: int, n_seeds: int, seed: int) -> list[int]:
    """Deterministic, evenly spread sample of 1-based paper ids."""
    rng = np.random.default_rng(seed)
    n = min(n_seeds, n_papers)
    ids = rng.choice(np.arange(1, n_papers + 1), size=n, replace=False)
    return sorted(int(x) for x in ids)


def collect_behavioral(
    base_url: str = DEFAULT_BASE_URL,
    *,
    n_seeds: int = 200,
    k: int = 10,
    algos: tuple[str, ...] = DEFAULT_ALGOS,
    seed: int = 20260625,
    pause_s: float = 0.0,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Query every algorithm for a deterministic sample of seeds; return raw behaviour."""
    base = base_url.rstrip("/")
    health = _get_json(f"{base}/healthz", timeout=timeout)
    if not health:
        raise RuntimeError(f"API at {base} did not return /healthz")
    n_papers = int(health["n_papers"])
    seed_ids = _sample_seed_ids(n_papers, n_seeds, seed)

    records: list[dict[str, Any]] = []
    skipped = 0
    for sid in seed_ids:
        meta = _get_json(f"{base}/papers/{sid}", timeout=timeout)
        if not meta:
            skipped += 1
            continue
        recs: dict[str, list[int]] = {}
        latency: dict[str, float] = {}
        ok = True
        for algo in algos:
            qs = urllib.parse.urlencode({"k": k, "algo": algo})
            payload = _get_json(f"{base}/similar/{sid}?{qs}", timeout=timeout)
            if not payload:
                ok = False
                break
            recs[algo] = [int(it["paper"]["paper_id"]) for it in payload["items"]]
            latency[algo] = float(payload.get("latency_ms", 0.0))
            if pause_s:
                time.sleep(pause_s)
        if not ok:
            skipped += 1
            continue
        records.append(
            {
                "seed": sid,
                "meta": {
                    "cited_by_count": int(meta.get("cited_by_count") or 0),
                    "publication_year": meta.get("publication_year"),
                    "primary_topic": meta.get("primary_topic"),
                },
                "recs": recs,
                "latency_ms": latency,
            }
        )

    return {
        "base_url": base,
        "k": k,
        "algos": list(algos),
        "n_papers": n_papers,
        "n_seeds_requested": len(seed_ids),
        "n_seeds_collected": len(records),
        "n_skipped": skipped,
        "sample_seed": seed,
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "records": records,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect online recommendation behaviour from the arxrec API.")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--n-seeds", type=int, default=200)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260625)
    ap.add_argument("--pause-s", type=float, default=0.0, help="politeness delay between calls")
    ap.add_argument("--out", default="docs/analysis/data/behavioral_sample.json")
    args = ap.parse_args()

    sample = collect_behavioral(
        args.base_url, n_seeds=args.n_seeds, k=args.k, seed=args.seed, pause_s=args.pause_s
    )
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(sample, fh, indent=2)
    print(
        f"collected {sample['n_seeds_collected']}/{sample['n_seeds_requested']} seeds "
        f"({sample['n_skipped']} skipped) -> {args.out}"
    )


if __name__ == "__main__":
    main()

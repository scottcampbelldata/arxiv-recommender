"""Build the in-memory training/eval objects from Postgres.

We load every paper as a contiguous 0-indexed array, then build the
citation user-item matrix with rows = citing paper, cols = cited paper.
Train / test split holds out 10% of citation edges per citing paper.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from arxrec.config import SETTINGS


@dataclass
class Dataset:
    papers: pd.DataFrame                  # contiguous 0..N-1 paper_idx column
    paper_id_to_idx: dict[int, int]
    train_edges: list[tuple[int, int]]    # (citing_idx, cited_idx)
    test_holdout: dict[int, set[int]]     # seed_idx -> held-out cited idxs
    n_papers: int
    cold_seeds: set[int]                  # citing papers with <3 train edges


def _engine():
    return create_engine(SETTINGS.sqlalchemy_url, pool_pre_ping=True)


def build_dataset(holdout_frac: float = 0.10, seed: int | None = None) -> Dataset:
    seed = SETTINGS.seed if seed is None else seed
    rng = np.random.default_rng(seed)
    eng = _engine()
    papers = pd.read_sql(
        "SELECT paper_id, arxiv_id, doi, title, abstract, authors, primary_topic, "
        "       publication_year, cited_by_count "
        "FROM core.papers ORDER BY paper_id",
        eng,
    )
    paper_id_to_idx = {int(p): i for i, p in enumerate(papers["paper_id"].tolist())}
    papers["paper_idx"] = np.arange(len(papers))
    n = len(papers)

    edges = pd.read_sql("SELECT citing_paper_id, cited_paper_id FROM core.citations", eng)
    edges["u"] = edges["citing_paper_id"].map(paper_id_to_idx)
    edges["i"] = edges["cited_paper_id"].map(paper_id_to_idx)
    edges = edges.dropna(subset=["u", "i"]).copy()
    edges["u"] = edges["u"].astype(np.int64)
    edges["i"] = edges["i"].astype(np.int64)

    train_edges: list[tuple[int, int]] = []
    test_holdout: dict[int, set[int]] = {}
    cold_seeds: set[int] = set()
    for u, grp in edges.groupby("u", sort=False):
        ix = grp["i"].to_numpy()
        m = len(ix)
        if m == 0:
            continue
        if m == 1:
            train_edges.append((int(u), int(ix[0])))
            continue
        h = max(1, round(m * holdout_frac))
        h = min(h, m - 1)  # always keep at least one train edge
        perm = rng.permutation(m)
        test_idx = perm[:h]
        train_idx = perm[h:]
        for j in train_idx:
            train_edges.append((int(u), int(ix[j])))
        test_holdout[int(u)] = {int(ix[j]) for j in test_idx}
        if len(train_idx) <= 2:
            cold_seeds.add(int(u))

    return Dataset(
        papers=papers,
        paper_id_to_idx=paper_id_to_idx,
        train_edges=train_edges,
        test_holdout=test_holdout,
        n_papers=n,
        cold_seeds=cold_seeds,
    )

"""Unit tests for popularity, TF-IDF, and ALS on tiny synthetic data."""

from __future__ import annotations

import numpy as np
import pandas as pd

from arxrec.algo.als_citation import CitationALSRecommender
from arxrec.algo.base import topk_indices
from arxrec.algo.content_tfidf import TfidfRecommender
from arxrec.algo.popularity import PopularityRecommender


def test_topk_descending_drops_inf():
    s = np.array([0.1, np.inf * -1, 0.3, 0.2])
    s[1] = -np.inf
    idx = topk_indices(s, 10)
    assert idx.tolist() == [2, 3, 0]


def test_topk_zero_k():
    assert topk_indices(np.array([1.0, 2.0]), 0).size == 0


def _toy_papers() -> pd.DataFrame:
    return pd.DataFrame({
        "paper_id": [1, 2, 3, 4, 5],
        "title": [
            "Attention is all you need",
            "BERT pretraining",
            "Vision transformers",
            "Reinforcement learning survey",
            "Graph neural network basics",
        ],
        "abstract": [
            "transformer attention self heads",
            "transformer encoder pretrain bidirectional",
            "vit image patches attention transformer",
            "policy gradient value function",
            "graph message passing node embedding",
        ],
        "authors": ["A B", "C D", "E F", "G H", "I J"],
        "primary_topic": ["nlp", "nlp", "vision", "rl", "graph"],
    })


def test_tfidf_finds_transformer_neighbours_first():
    tf = TfidfRecommender(max_features=200)
    tf.fit(_toy_papers())
    r = tf.similar_items(seed_id=0, k=3)
    # Seed is "Attention is all you need". Top neighbours should be the other
    # two transformer-flavoured papers.
    assert set(r.item_ids[:2]) == {1, 2}


def test_popularity_orders_by_count():
    pop = PopularityRecommender()
    pop.fit(np.array([5, 100, 3, 200, 50]))
    r = pop.similar_items(seed_id=0, k=4)
    assert r.item_ids == [3, 1, 4, 2]


def test_als_runs_on_tiny_graph():
    # 5 papers, citations: 0->2, 0->3, 1->2, 1->3, 4->3
    edges = [(0, 2), (0, 3), (1, 2), (1, 3), (4, 3)]
    ui = CitationALSRecommender.build_user_item(edges, n_papers=5)
    assert ui.shape == (5, 5)
    als = CitationALSRecommender(factors=4, iterations=3, alpha=1.0)
    als.fit(ui)
    # similar_items on paper 2 should not blow up and should return some items.
    r = als.similar_items(2, k=3)
    assert len(r.item_ids) > 0

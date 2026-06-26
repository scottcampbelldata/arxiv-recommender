"""Recommender algorithm implementations."""

from arxrec.algo.als_citation import CitationALSRecommender
from arxrec.algo.base import Recommender, RecResult
from arxrec.algo.content_neural import NeuralEmbeddingRecommender
from arxrec.algo.content_tfidf import TfidfRecommender
from arxrec.algo.hybrid import HybridRecommender
from arxrec.algo.popularity import PopularityRecommender

__all__ = [
    "CitationALSRecommender",
    "HybridRecommender",
    "NeuralEmbeddingRecommender",
    "PopularityRecommender",
    "RecResult",
    "Recommender",
    "TfidfRecommender",
]

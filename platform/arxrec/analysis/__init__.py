"""Behavioural analysis of the recommender, complementing the offline eval.

The offline leaderboard (``arxrec.eval``) answers *is each algorithm accurate*
against held-out citations. This package answers a different, equally senior
question: *how do the five algorithms behave relative to one another in
production* -- do they agree on what to recommend, how concentrated are their
picks across the catalogue, and what does the hybrid actually inherit from its
parts. The two views together are what turns a leaderboard into a findings
report.

``collect`` samples the live HTTP API; ``stats`` reduces the raw sample to the
quantities the case study reports. Neither touches the database.
"""

from arxrec.analysis.stats import (
    cold_warm_split,
    gini,
    hybrid_attribution,
    jaccard,
    mean_overlap_matrix,
    recommendation_concentration,
)

__all__ = [
    "cold_warm_split",
    "gini",
    "hybrid_attribution",
    "jaccard",
    "mean_overlap_matrix",
    "recommendation_concentration",
]

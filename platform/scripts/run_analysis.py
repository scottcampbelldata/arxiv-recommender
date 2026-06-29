"""Turn the raw eval + behavioural data into the case-study figures and a
derived-statistics file.

Inputs (all under ``platform/docs/analysis/data/``):
  - ``leaderboard_offline.json``  offline held-out metrics (point estimates)
  - ``behavioral_sample.json``    online behaviour sampled from the live API
  - ``eval_metric.csv``           optional; bootstrap CIs exported from Postgres

Outputs:
  - ``platform/docs/analysis/figures/*.png``
  - ``platform/docs/analysis/data/derived_stats.json``  every number the prose cites

Run from the ``platform`` directory::

    python scripts/run_analysis.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from arxrec.analysis.stats import (
    cold_warm_split,
    hybrid_attribution,
    mean_overlap_matrix,
    recommendation_concentration,
)

DATA = Path(__file__).resolve().parent.parent / "docs" / "analysis" / "data"
FIGS = Path(__file__).resolve().parent.parent / "docs" / "analysis" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

ALGOS = ["popularity", "tfidf", "neural", "als", "hybrid"]
COLORS = {
    "popularity": "#9aa0aa",
    "tfidf": "#4f8bf5",
    "neural": "#f5a04f",
    "als": "#b56bf5",
    "hybrid": "#2bbf7a",
}
COLD_THRESHOLD = 10  # seed cited_by_count below this => "cold" segment

plt.rcParams.update(
    {
        "figure.dpi": 130,
        "savefig.bbox": "tight",
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.axisbelow": True,
    }
)


def _load() -> tuple[dict, dict]:
    lb = json.loads((DATA / "leaderboard_offline.json").read_text())
    sample = json.loads((DATA / "behavioral_sample.json").read_text())
    return lb, sample


def _lb_map(lb: dict) -> dict[str, dict]:
    return {r["algorithm"]: r for r in lb["rows"]}


def fig_accuracy(lb: dict) -> None:
    rows = _lb_map(lb)
    metrics = [("recall@k", "Recall@10"), ("map@k", "MAP@10"), ("ndcg@k", "NDCG@10")]
    x = np.arange(len(metrics))
    width = 0.16
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    for i, algo in enumerate(ALGOS):
        vals = [rows[algo][m] for m, _ in metrics]
        # asymmetric error bars from the bootstrap 95% CIs, when present
        err_lo, err_hi = [], []
        for m, _ in metrics:
            ci = rows[algo].get(m.replace("@k", "") + "_ci")
            if ci and ci[0] is not None and ci[1] is not None:
                err_lo.append(rows[algo][m] - ci[0])
                err_hi.append(ci[1] - rows[algo][m])
            else:
                err_lo.append(0.0)
                err_hi.append(0.0)
        ax.bar(x + (i - 2) * width, vals, width, label=algo, color=COLORS[algo],
               yerr=[err_lo, err_hi], capsize=2, ecolor="#33373f", error_kw={"lw": 0.8})
    ax.set_xticks(x)
    ax.set_xticklabels([lbl for _, lbl in metrics])
    ax.set_ylabel("score")
    ax.set_title("Accuracy on held-out citations (k=10, 2,000 seeds, 95% bootstrap CIs)")
    ax.legend(ncol=5, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.10), frameon=False)
    fig.savefig(FIGS / "fig1_accuracy.png")
    plt.close(fig)


def fig_tradeoff(lb: dict) -> None:
    rows = _lb_map(lb)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
    for ax, (ykey, ylabel) in zip(axes, [("coverage", "Catalogue coverage"), ("diversity", "Diversity")], strict=True):
        for algo in ALGOS:
            ax.scatter(rows[algo]["recall@k"], rows[algo][ykey], s=170, color=COLORS[algo], edgecolor="white", zorder=3)
            ax.annotate(algo, (rows[algo]["recall@k"], rows[algo][ykey]), textcoords="offset points",
                        xytext=(7, 4), fontsize=9)
        ax.set_xlabel("Recall@10 (accuracy)")
        ax.set_ylabel(ylabel)
    axes[0].set_title("Accuracy vs coverage")
    axes[1].set_title("Accuracy vs diversity")
    fig.suptitle("The hybrid trades breadth for accuracy", fontweight="bold")
    fig.savefig(FIGS / "fig2_tradeoff.png")
    plt.close(fig)


def fig_overlap(sample: dict) -> np.ndarray:
    mat, labels = mean_overlap_matrix(sample["records"], ALGOS)
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    im = ax.imshow(mat, cmap="viridis", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)), labels, rotation=30, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center",
                    color="white" if mat[i, j] < 0.6 else "black", fontsize=9)
    ax.set_title("Mean top-10 overlap between algorithms (Jaccard)")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.savefig(FIGS / "fig3_overlap_heatmap.png")
    plt.close(fig)
    return mat


def fig_attribution(post: dict, lb: dict, pre: dict | None) -> dict[str, dict[str, float]]:
    """Before/after: how much the hybrid's top-10 overlaps each base model,
    pre-tuning (neural-heavy weights) vs post-tuning (the deployed blend)."""
    bases = ["popularity", "tfidf", "neural", "als"]
    attr_post = hybrid_attribution(post["records"], "hybrid", bases)
    attr_pre = hybrid_attribution(pre["records"], "hybrid", bases) if pre else None
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    x = np.arange(len(bases))
    if attr_pre:
        ax.bar(x - 0.2, [attr_pre[b] for b in bases], 0.4,
               label="before re-tuning (neural-heavy weights)", color="#c9ccd2")
        ax.bar(x + 0.2, [attr_post[b] for b in bases], 0.4,
               label="after re-tuning (deployed weights)", color="#2bbf7a")
        ax.set_title("Re-tuning flipped what the hybrid follows: neural → TF-IDF")
    else:
        ax.bar(x, [attr_post[b] for b in bases], 0.5, label="overlap with hybrid", color="#2bbf7a")
        ax.set_title("What the hybrid actually inherits")
    ax.set_xticks(x, bases)
    ax.set_ylabel("mean Jaccard overlap with hybrid top-10")
    ax.legend(frameon=False, fontsize=9)
    fig.savefig(FIGS / "fig4_hybrid_attribution.png")
    plt.close(fig)
    return {"pre": attr_pre or {}, "post": attr_post}


def fig_latency(lb: dict) -> None:
    rows = _lb_map(lb)
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    vals = [rows[a]["latency_p95_ms"] for a in ALGOS]
    ax.bar(ALGOS, vals, color=[COLORS[a] for a in ALGOS])
    ax.set_yscale("log")
    ax.set_ylabel("p95 latency (ms, log scale)")
    ax.set_title("Latency is dominated by TF-IDF, not the neural model")
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:g}", ha="center", va="bottom", fontsize=9)
    fig.savefig(FIGS / "fig5_latency.png")
    plt.close(fig)


def fig_concentration(sample: dict, conc: dict[str, dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    x = np.arange(len(ALGOS))
    cov = [conc[a]["catalogue_coverage"] for a in ALGOS]
    ax.bar(x, cov, color=[COLORS[a] for a in ALGOS])
    ax.set_xticks(x, ALGOS)
    ax.set_ylabel(f"catalogue coverage over {sample['n_seeds_collected']} sampled seeds")
    ax.set_title("How widely each algorithm spreads its recommendations")
    for i, a in enumerate(ALGOS):
        ax.text(i, cov[i], f"gini={conc[a]['gini']:.2f}", ha="center", va="bottom", fontsize=8)
    fig.savefig(FIGS / "fig6_concentration.png")
    plt.close(fig)


def main() -> None:
    lb, sample = _load()
    rows = _lb_map(lb)
    n_cat = sample["n_papers"]
    pre_path = DATA / "_pretune_behavioral_sample.json"
    pre = json.loads(pre_path.read_text()) if pre_path.exists() else None

    fig_accuracy(lb)
    fig_tradeoff(lb)
    mat = fig_overlap(sample)
    attr = fig_attribution(sample, lb, pre)
    fig_latency(lb)
    conc = {a: recommendation_concentration(sample["records"], a, n_cat) for a in ALGOS}
    fig_concentration(sample, conc)

    # cold/warm behavioural split sizes
    cold, warm = cold_warm_split(sample["records"], COLD_THRESHOLD)
    idx = {a: i for i, a in enumerate(ALGOS)}
    derived = {
        "n_seeds_collected": sample["n_seeds_collected"],
        "n_catalogue": n_cat,
        "cold_threshold": COLD_THRESHOLD,
        "n_cold_seeds": len(cold),
        "n_warm_seeds": len(warm),
        "overlap": {f"{a}|{b}": round(float(mat[idx[a], idx[b]]), 4)
                    for a in ALGOS for b in ALGOS if idx[a] < idx[b]},
        "hybrid_attribution_pre": {k: round(v, 4) for k, v in attr["pre"].items()},
        "hybrid_attribution_post": {k: round(v, 4) for k, v in attr["post"].items()},
        "concentration": {a: {k: round(v, 6) for k, v in conc[a].items()} for a in ALGOS},
        "offline": {a: rows[a] for a in ALGOS},
        "blend_weights": lb["blend_weights"],
    }
    (DATA / "derived_stats.json").write_text(json.dumps(derived, indent=2))
    print(f"wrote 6 figures to {FIGS}")
    print(f"als|popularity overlap = {derived['overlap'].get('popularity|als')}")
    print(f"hybrid attribution pre  = {derived['hybrid_attribution_pre']}")
    print(f"hybrid attribution post = {derived['hybrid_attribution_post']}")


if __name__ == "__main__":
    main()

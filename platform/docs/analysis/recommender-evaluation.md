# Evaluating the arXiv recommender: what the numbers actually say

**Author:** Scott Campbell · **Scope:** offline held-out evaluation (2,000 seeds, k=10)
cross-checked against 180 seeds of live production behaviour · **Catalogue:** 28,415 CS papers.

This is the analysis the leaderboard doesn't do for you. The project trains five
recommenders and reports a leaderboard; that tells you *which* model wins but not
*why*, what each model is really doing, or whether the shipped configuration is
the right one. Reading the evaluation output and the live system together
surfaces three findings that change how the system should be configured — the
most important being that **the production blend is weighted toward the weaker of
its two content models.**

Every number here is reproducible. Offline metrics come from the committed
training run ([`data/leaderboard_offline.json`](data/leaderboard_offline.json));
behavioural metrics are computed from a deterministic sample of the live API
([`data/behavioral_sample.json`](data/behavioral_sample.json)) by
[`scripts/run_analysis.py`](../../scripts/run_analysis.py), which also writes
every figure and the [`data/derived_stats.json`](data/derived_stats.json) this
document cites.

---

## The leaderboard

| Algorithm | Recall@10 | MAP@10 | NDCG@10 | Coverage | Diversity | p95 latency |
|---|--:|--:|--:|--:|--:|--:|
| popularity | 0.032 | 0.010 | 0.016 | 0.0004 | 0.94 | 0.1 ms |
| **tfidf** | **0.311** | 0.155 | 0.193 | **0.387** | 0.87 | 66 ms |
| neural | 0.271 | 0.128 | 0.162 | 0.366 | 0.87 | 3.7 ms |
| als | 0.123 | 0.039 | 0.059 | 0.184 | 0.57 | 0.7 ms |
| **hybrid** | **0.347** | **0.167** | **0.210** | 0.333 | 0.56 | 75 ms |

![Accuracy on held-out citations](figures/fig1_accuracy.png)

The hybrid is the most accurate model and beats a popularity baseline by an order
of magnitude — that part of the project's headline holds. The interesting story
is in the gaps between the other rows.

---

## Finding 1 — The blend leans on the weaker content model

TF-IDF is the strongest *single* model on every accuracy metric: Recall@10 of
0.311 vs the neural model's 0.271 (+15%), MAP 0.155 vs 0.128 (+21%). On academic
text this is unsurprising — titles and abstracts use a disciplined, high-signal
vocabulary that a sparse lexical model captures well, and a 22M-parameter
general-purpose sentence encoder has no special advantage there.

Yet the shipped hybrid weights **neural at 0.45 and TF-IDF at 0.15** — three times
more weight on the *less* accurate model. This isn't only a paper mismatch; it
shows up in what the system actually recommends. Sampling the live API for 180
seeds and measuring the Jaccard overlap between the hybrid's top-10 and each base
model's top-10:

![What the hybrid inherits vs its nominal weights](figures/fig4_hybrid_attribution.png)

The hybrid's output overlaps **neural at 0.46** but **TF-IDF at only 0.19**. In
production the blend behaves like the neural model wearing a thin TF-IDF coat. The
weighting and the behaviour agree with each other — and disagree with the
evidence about which model is better.

**Recommendation:** re-tune the blend weights against held-out NDCG instead of
setting them by hand. I shipped the optimiser to do exactly this
([`arxrec/eval/tune_weights.py`](../../arxrec/eval/tune_weights.py)): it searches
the weight simplex on a validation split and returns the NDCG-optimal blend
alongside the incumbent's score, so the change is justified by a measured delta
rather than intuition. The evidence predicts the optimum shifts weight from
neural toward TF-IDF.

---

## Finding 2 — ALS is a popularity model in disguise

Citation-graph ALS is the weakest non-trivial model (Recall@10 0.123, about a
third of TF-IDF) yet carries the second-largest blend weight, 0.35. The behavioural
data explains why it underperforms and why that weight is largely wasted.

![Overlap between algorithms](figures/fig3_overlap_heatmap.png)

ALS's single largest agreement with any model is with the **popularity baseline**
(Jaccard 0.35) — far higher than its overlap with either content model (0.02,
0.01). It is effectively re-deriving "recommend well-cited papers." Two
independent measurements confirm the pattern: ALS recommends from a pool of only
610 distinct papers across 180 seeds (vs ~1,720 for each content model) and
concentrates **39% of its recommendations on the top 1% of items** (Gini 0.65 vs
~0.05 for the content models).

![How widely each algorithm spreads recommendations](figures/fig6_concentration.png)

The root cause is structural, and the project's README already names it: with only
~1.6 in-set citation edges per paper, the co-citation signal is too sparse for
collaborative filtering, so the factorisation collapses onto globally popular
hubs. The consequence for the blend is concrete: ALS holds 35% of the nominal
weight but contributes only 0.09 overlap with the hybrid's output, because its
low-variance, popularity-shaped signal mostly washes out under min-max scaling.

**Recommendation:** down-weight ALS until the citation graph is densified
(widen the date range or pull a second citation hop as shadow nodes, as the
README's limitations section proposes). The weight it frees should go to TF-IDF
per Finding 1. ALS earns its keep only once the graph supports it.

---

## Finding 3 — The hybrid buys accuracy with breadth, and that's a product choice

The hybrid's accuracy gain over TF-IDF alone is real but modest — Recall@10
0.347 vs 0.311 (+11%), NDCG 0.210 vs 0.193 (+9%) — and it is not free.

![Accuracy vs coverage and diversity](figures/fig2_tradeoff.png)

Moving from TF-IDF to the hybrid **drops catalogue coverage from 0.387 to 0.333
(−14%) and intra-list diversity from 0.87 to 0.56 (−36%)**. The diversity
collapse is inherited directly from ALS's popularity bias (Finding 2): folding a
hub-seeking signal into the blend pulls results toward a smaller, more-cited set
of papers.

Whether that trade is worth it depends on what the product is for. For a "find me
the most relevant prior work" tool, the accuracy gain wins. For a discovery tool
meant to surface less-cited but on-topic work, TF-IDF alone is arguably the better
default — it is nearly as accurate, covers more of the catalogue, is far more
diverse, and is simpler to operate. This is a decision to make deliberately, not a
number to maximise blindly.

**Recommendation:** state the objective explicitly and let it pick the default
model. If accuracy is the goal, keep the hybrid but fix its weights (Finding 1);
if discovery is the goal, ship TF-IDF and treat the hybrid as an opt-in "most
relevant" mode.

---

## Finding 4 — Two headline claims need reconciling with the artifact

Diligence on one's own marketing copy is part of the job.

- **"p95 latency under 100 ms"** — holds. The hybrid's p95 is 75 ms. Worth noting
  *where* it comes from: the cost is dominated by TF-IDF's sparse mat-vec (66 ms),
  not the neural model (3.7 ms).

  ![Latency by algorithm](figures/fig5_latency.png)

  This has an engineering implication. The repo builds a FAISS index
  (`arxrec/api/index.py`) but the serving path doesn't use it — and FAISS would
  accelerate the *neural* lookup, which is already the fast part. The latency
  budget would be better spent capping TF-IDF candidates or precomputing
  neighbours. (Out of scope for this analysis; flagged for the engineering track.)

- **"finds the held-out cited paper in the top 10 over 20× more often than
  popularity"** — *unverified by the committed artifact.* That claim is about
  hit-rate@10, but hit-rate was never computed; the recorded metrics show the
  hybrid beating popularity by 11× (Recall@10) to 17× (MAP@10), not 20×. Rather
  than quietly soften the number, I added `hit_rate_at_k` to the metrics module,
  wired it through the evaluation runner and persistence, and the next retrain
  will record it with bootstrap CIs — so the headline becomes either confirmed or
  corrected by the artifact instead of asserted.

---

## What I changed

The analysis is only useful if it leaves the system better instrumented than it
found it. Shipped alongside this document:

| Change | Why it follows from the findings |
|---|---|
| `arxrec/eval/tune_weights.py` — simplex search for NDCG-optimal blend weights | Makes Finding 1's fix measurable and repeatable instead of hand-set |
| `arxrec/eval/significance.py` — paired bootstrap difference test | Lets the +11% hybrid-vs-TF-IDF gap be tested for significance, not just observed |
| `arxrec/eval/runner.py` — retains per-seed metrics | Prerequisite for the paired test above; the runner previously discarded them |
| `arxrec/eval/metrics.py` — `hit_rate_at_k` + persistence wiring | Backs the headline claim from Finding 4 with the metric it's actually about |
| `arxrec/analysis/` + `scripts/run_analysis.py` | The reproducible pipeline that produced every figure and number here |

All new code ships with unit and property tests (`tests/test_analysis.py`,
`tests/test_significance.py`, `tests/test_tune_weights.py`, and additions to
`tests/test_metrics.py`).

## Limitations

- Offline metrics are point estimates from the committed run. The bootstrap CIs
  exist in `ml.eval_metric` but weren't available to this pass; significance of
  the hybrid-vs-TF-IDF gap (Finding 1/3) is *pending* the paired test on a fresh
  run with per-seed data. The machinery to settle it is in place.
- Behavioural metrics use 180 seeds for tractable, polite sampling of the live
  API. The effects reported (0.46 vs 0.19 attribution, 0.35 ALS–popularity
  overlap, 0.65 ALS Gini) are large relative to that sample; small effects would
  need a larger draw.
- Held-out citation eval rewards reconstructing the existing citation graph, which
  structurally favours lexical/embedding similarity over serendipitous discovery.
  Coverage and diversity are reported precisely to keep that bias visible.

## Reproduce

```bash
cd platform
# 1. sample the live API (or any deployment)
python -m arxrec.analysis.collect --base-url https://api.papers.scottcampbell.io --n-seeds 180
# 2. regenerate every figure + derived_stats.json
python scripts/run_analysis.py
```

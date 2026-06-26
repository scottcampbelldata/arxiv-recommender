# platform

Python half of the arXiv recommender. FastAPI service + training pipeline
+ Postgres schema + deploy artefacts. Built to run on a Linux VPS under
systemd, but the same code runs unchanged on Windows for local development
and screenshots.

See [`deploy/README.md`](deploy/README.md) for VPS install steps.

## Layout

```
platform/
  arxrec/         Library package
    algo/         Popularity, TF-IDF, MiniLM neural, citation-ALS, hybrid
    api/          FastAPI app + FAISS index
    data/         OpenAlex client + Postgres loader + Dataset builder
    db/           schema.sql (idempotent)
    eval/         Metrics + run_similar_items_eval harness with bootstrap CIs
    utils/        Logging, deterministic seeding
    config.py     Single Settings dataclass, env-driven
    train.py      End-to-end training entry point
  deploy/         systemd units, nginx config, bash DB bootstrap, README
  scripts/        screenshot.py for the dashboard
  tests/          pytest + hypothesis
  data/           Raw JSONL (gitignored), pickled models, leaderboard.json
  pyproject.toml
```

## Local install

```bash
python -m venv .venv
.venv/bin/pip install -e .[dev]
cp .env.example .env
```

## Pipeline

```bash
# Pull recent CS arXiv papers + their citation edges from OpenAlex.
.venv/bin/python -m arxrec.data.openalex
# Load into Postgres core.papers + core.citations.
.venv/bin/python -m arxrec.data.loader
# Train every model and write the leaderboard.
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m arxrec.train --max-eval-seeds 2000
# Run the API.
.venv/bin/python -m uvicorn arxrec.api.main:app --host 127.0.0.1 --port 8820
```

## Tests + lint

```bash
.venv/bin/pytest -q
.venv/bin/ruff check arxrec tests
```

-- arxiv_recs schema. Idempotent, re-run safely.

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS ml;
CREATE SCHEMA IF NOT EXISTS ops;

-- Papers: ~30-50k recent ML papers from OpenAlex.
CREATE TABLE IF NOT EXISTS core.papers (
    paper_id          INTEGER PRIMARY KEY,            -- contiguous internal id
    openalex_id       TEXT NOT NULL UNIQUE,           -- W2741809807
    arxiv_id          TEXT,                            -- 2107.03374
    doi               TEXT,
    title             TEXT NOT NULL,
    abstract          TEXT,
    authors           TEXT,                            -- comma-separated display names
    primary_topic     TEXT,                            -- e.g. Machine Learning
    publication_year  INTEGER,
    publication_date  DATE,
    cited_by_count    INTEGER NOT NULL DEFAULT 0,
    venue             TEXT,
    pdf_url           TEXT
);
CREATE INDEX IF NOT EXISTS papers_year_idx    ON core.papers (publication_year);
CREATE INDEX IF NOT EXISTS papers_arxiv_idx   ON core.papers (arxiv_id);
CREATE INDEX IF NOT EXISTS papers_title_trgm  ON core.papers USING gin (title gin_trgm_ops);

-- Citation edges: paper A cites paper B. Both ids reference core.papers; we
-- only keep edges where both endpoints are inside our subset (the rest are
-- dropped at ingestion time).
CREATE TABLE IF NOT EXISTS core.citations (
    citing_paper_id INTEGER NOT NULL REFERENCES core.papers(paper_id) ON DELETE CASCADE,
    cited_paper_id  INTEGER NOT NULL REFERENCES core.papers(paper_id) ON DELETE CASCADE,
    PRIMARY KEY (citing_paper_id, cited_paper_id)
);
CREATE INDEX IF NOT EXISTS citations_cited_idx ON core.citations (cited_paper_id);

-- ml.model_run and ml.eval_metric mirror the book-recommender schema so the
-- training entry point can reuse the same persistence helpers.
CREATE TABLE IF NOT EXISTS ml.model_run (
    run_id      SERIAL PRIMARY KEY,
    algorithm   TEXT NOT NULL,
    trained_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    params      JSONB NOT NULL DEFAULT '{}'::jsonb,
    artifact    TEXT,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS ml.eval_metric (
    run_id     INTEGER NOT NULL REFERENCES ml.model_run(run_id) ON DELETE CASCADE,
    metric     TEXT NOT NULL,
    k          INTEGER,
    value      DOUBLE PRECISION NOT NULL,
    ci_low     DOUBLE PRECISION,
    ci_high    DOUBLE PRECISION,
    segment    TEXT,
    PRIMARY KEY (run_id, metric, k, segment)
);

CREATE TABLE IF NOT EXISTS ml.embedding (
    paper_id    INTEGER NOT NULL REFERENCES core.papers(paper_id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,             -- 'minilm', 'tfidf_svd', 'als'
    dim         INTEGER NOT NULL,
    -- Stored on disk in data/models/<kind>.npy aligned to paper_id order; this
    -- table just records that the artefact exists and its checksum.
    artifact    TEXT NOT NULL,
    sha256      TEXT,
    built_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (paper_id, kind)
);

-- ops.request_log: serving-layer observability.
CREATE TABLE IF NOT EXISTS ops.request_log (
    request_id   BIGSERIAL PRIMARY KEY,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    endpoint     TEXT NOT NULL,
    seed_paper   INTEGER,
    algorithm    TEXT,
    k            INTEGER,
    latency_ms   REAL,
    status       INTEGER
);

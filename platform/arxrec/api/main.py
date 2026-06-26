"""FastAPI service for arxiv-recommender.

Endpoints:
    GET  /healthz                         liveness + list of loaded algorithms
    GET  /papers?q=&limit=                title or author substring search
    GET  /papers/{paper_id}               single paper detail
    GET  /similar/{paper_id}?k=&algo=     top-k similar papers by chosen algo

Algorithms: popularity, tfidf, neural, als, hybrid.
"""

from __future__ import annotations

import pickle
import time
from contextlib import asynccontextmanager
from typing import Annotated

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from arxrec.config import SETTINGS
from arxrec.utils.logging import configure_logging, get_logger

LOG = get_logger(__name__)
ALGOS = ("popularity", "tfidf", "neural", "als", "hybrid")


class PaperOut(BaseModel):
    paper_id: int
    arxiv_id: str | None = None
    title: str
    authors: str = ""
    abstract_preview: str = ""
    primary_topic: str | None = None
    publication_year: int | None = None
    cited_by_count: int = 0
    venue: str | None = None
    pdf_url: str | None = None


class RecItem(BaseModel):
    paper: PaperOut
    score: float
    reason: str = ""


class RecOut(BaseModel):
    algorithm: str
    seed_paper: int
    k: int
    latency_ms: float
    items: list[RecItem]


class HealthOut(BaseModel):
    status: str = "ok"
    algorithms_loaded: list[str] = Field(default_factory=list)
    n_papers: int = 0


class State:
    def __init__(self) -> None:
        self.models: dict[str, object] = {}
        self.papers: dict[int, PaperOut] = {}
        self.engine = create_engine(SETTINGS.sqlalchemy_url, pool_pre_ping=True)


STATE = State()


def _preview(abstract: str, max_chars: int = 280) -> str:
    if not abstract:
        return ""
    if len(abstract) <= max_chars:
        return abstract
    cut = abstract[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > max_chars - 80:
        cut = cut[:last_space]
    return cut.rstrip() + "..."


def _load_papers() -> dict[int, PaperOut]:
    with psycopg.connect(SETTINGS.dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT paper_id, arxiv_id, title, authors, abstract, primary_topic,"
            "       publication_year, cited_by_count, venue, pdf_url "
            "FROM core.papers ORDER BY paper_id"
        )
        rows = cur.fetchall()
    out: dict[int, PaperOut] = {}
    for r in rows:
        out[int(r[0])] = PaperOut(
            paper_id=int(r[0]),
            arxiv_id=r[1],
            title=r[2] or "",
            authors=r[3] or "",
            abstract_preview=_preview(r[4] or ""),
            primary_topic=r[5],
            publication_year=r[6],
            cited_by_count=int(r[7] or 0),
            venue=r[8],
            pdf_url=r[9],
        )
    return out


def _load_models() -> dict[str, object]:
    out: dict[str, object] = {}
    for algo in ALGOS:
        p = SETTINGS.data_models / f"{algo}.pkl"
        if p.exists():
            try:
                with open(p, "rb") as f:
                    out[algo] = pickle.load(f)
                LOG.info("model.loaded", algorithm=algo)
            except Exception as exc:
                LOG.warning("model.load_failed", algorithm=algo, error=str(exc))
    return out


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(SETTINGS.log_level)
    LOG.info("api.startup")
    STATE.papers = _load_papers()
    STATE.models = _load_models()
    LOG.info("api.ready", n_papers=len(STATE.papers), models=list(STATE.models.keys()))
    yield
    LOG.info("api.shutdown")


app = FastAPI(
    title="arXiv recommender API",
    version="0.1.0",
    description=(
        "Hybrid arXiv paper recommender. Returns top-K papers similar to a "
        "seed paper using popularity / TF-IDF / sentence-transformer / "
        "citation-graph ALS / hybrid blend algorithms."
    ),
    lifespan=lifespan,
)

_origins = [o.strip() for o in (SETTINGS.cors_origins or "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,
)


def _log_request(endpoint: str, *, seed_paper: int | None, algorithm: str, k: int,
                  latency_ms: float, status: int) -> None:
    try:
        with psycopg.connect(SETTINGS.dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ops.request_log (endpoint, seed_paper, algorithm, k, latency_ms, status) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (endpoint, seed_paper, algorithm, k, latency_ms, status),
            )
    except Exception:
        pass


@app.get("/healthz", response_model=HealthOut)
def healthz() -> HealthOut:
    return HealthOut(
        status="ok",
        algorithms_loaded=list(STATE.models.keys()),
        n_papers=len(STATE.papers),
    )


@app.get("/papers", response_model=list[PaperOut])
def search_papers(q: Annotated[str, Query(min_length=1, max_length=200)],
                   limit: Annotated[int, Query(ge=1, le=30)] = 12) -> list[PaperOut]:
    pattern = f"%{q.lower()}%"
    with STATE.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT paper_id FROM core.papers "
                "WHERE lower(title) LIKE :p OR lower(authors) LIKE :p "
                "ORDER BY cited_by_count DESC LIMIT :lim"
            ),
            {"p": pattern, "lim": limit},
        ).fetchall()
    return [STATE.papers[int(r[0])] for r in rows if int(r[0]) in STATE.papers]


@app.get("/papers/{paper_id}", response_model=PaperOut)
def get_paper(paper_id: int) -> PaperOut:
    p = STATE.papers.get(paper_id)
    if p is None:
        raise HTTPException(404, "paper not found")
    return p


@app.get("/similar/{paper_id}", response_model=RecOut)
def similar(paper_id: int,
             k: Annotated[int, Query(ge=1, le=50)] = 10,
             algo: Annotated[str, Query(pattern="^(popularity|tfidf|neural|als|hybrid)$")] = "hybrid"
             ) -> RecOut:
    if paper_id not in STATE.papers:
        raise HTTPException(404, "paper not found")
    model = STATE.models.get(algo)
    if model is None:
        raise HTTPException(400, f"algorithm '{algo}' not loaded")
    # paper_id is the row index by construction (1-based -> 0-based conversion).
    seed_idx = paper_id - 1
    t0 = time.perf_counter()
    try:
        r = model.similar_items(seed_idx, k)  # type: ignore[attr-defined]
    except IndexError:
        # Model artefact is stale relative to the catalogue (was trained on a
        # smaller subset). Surface a clean 503 instead of a 500 traceback.
        raise HTTPException(503, "model artefact out of sync with catalogue, retrain pending") from None
    items: list[RecItem] = []
    for idx, score, reason in zip(r.item_ids, r.scores, r.reasons or [""] * len(r.item_ids), strict=False):
        pid = int(idx) + 1
        bk = STATE.papers.get(pid)
        if bk is None:
            continue
        items.append(RecItem(paper=bk, score=float(score), reason=reason))
    latency = (time.perf_counter() - t0) * 1000.0
    _log_request("/similar", seed_paper=paper_id, algorithm=algo, k=k, latency_ms=latency, status=200)
    return RecOut(algorithm=algo, seed_paper=paper_id, k=k, latency_ms=latency, items=items[:k])

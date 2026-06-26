"""Parse the OpenAlex JSONL dump into Postgres core.papers + core.citations.

Two passes:
  1. Read everything once, build the openalex_id -> paper_id mapping for
     papers we are keeping (those that survive a tiny quality filter).
  2. Read again, write rows for core.papers and core.citations.

The second pass keeps a citation edge only when BOTH endpoints are inside the
kept set, so the citation graph is a closed subgraph of our subset.
"""

from __future__ import annotations

import gzip
import io
import json
import sys
from pathlib import Path

import psycopg

from arxrec.config import SETTINGS
from arxrec.data.openalex import extract_arxiv_id, reconstruct_abstract
from arxrec.utils.logging import configure_logging, get_logger

LOG = get_logger(__name__)


def _connect() -> psycopg.Connection:
    return psycopg.connect(SETTINGS.dsn)


def _keep(work: dict) -> bool:
    if not work.get("title"):
        return False
    if not work.get("abstract_inverted_index"):
        return False
    return (work.get("cited_by_count") or 0) >= 0


def _author_string(work: dict) -> str:
    auths = work.get("authorships") or []
    names: list[str] = []
    for a in auths:
        ad = (a or {}).get("author") or {}
        n = ad.get("display_name")
        if n:
            names.append(n.replace(",", " "))  # commas confuse the CSV writer below
        if len(names) >= 15:
            break
    return ", ".join(names)


def build_paper_id_map(jsonl_path: Path) -> dict[str, int]:
    id_map: dict[str, int] = {}
    next_id = 1
    with gzip.open(jsonl_path, "rt", encoding="utf-8") as f:
        for line in f:
            w = json.loads(line)
            if not _keep(w):
                continue
            oa_id = w.get("id")
            if not oa_id:
                continue
            if oa_id not in id_map:
                id_map[oa_id] = next_id
                next_id += 1
    return id_map


def _copy_rows(conn: psycopg.Connection, sql_copy: str, rows: list[tuple]) -> int:
    if not rows:
        return 0
    buf = io.StringIO()
    for row in rows:
        # Quote any field containing newline / tab; we use \t as the separator.
        out: list[str] = []
        for v in row:
            if v is None:
                out.append(r"\N")
            else:
                s = str(v).replace("\\", "\\\\").replace("\t", " ").replace("\n", " ").replace("\r", " ")
                out.append(s)
        buf.write("\t".join(out))
        buf.write("\n")
    buf.seek(0)
    with conn.cursor() as cur, cur.copy(sql_copy) as cp:
        cp.write(buf.read())
    return len(rows)


def load(jsonl_path: Path) -> tuple[int, int]:
    LOG.info("loader.pass1.start", path=str(jsonl_path))
    id_map = build_paper_id_map(jsonl_path)
    LOG.info("loader.pass1.done", n=len(id_map))

    paper_rows: list[tuple] = []
    citation_rows: list[tuple] = []
    seen_edges: set[tuple[int, int]] = set()
    with gzip.open(jsonl_path, "rt", encoding="utf-8") as f:
        for line in f:
            w = json.loads(line)
            if not _keep(w):
                continue
            oa_id = w.get("id")
            pid = id_map.get(oa_id)
            if pid is None:
                continue
            paper_rows.append((
                pid,
                oa_id,
                extract_arxiv_id(w),
                w.get("doi"),
                w.get("title") or "",
                reconstruct_abstract(w.get("abstract_inverted_index")),
                _author_string(w),
                ((w.get("primary_topic") or {}).get("display_name")) or None,
                w.get("publication_year"),
                w.get("publication_date"),
                int(w.get("cited_by_count") or 0),
                ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                ((w.get("primary_location") or {}).get("pdf_url")) or None,
            ))
            for cited in (w.get("referenced_works") or []):
                cited_pid = id_map.get(cited)
                if cited_pid is None or cited_pid == pid:
                    continue
                key = (pid, cited_pid)
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                citation_rows.append(key)

    LOG.info("loader.parse.done", papers=len(paper_rows), edges=len(citation_rows))

    cols_p = (
        "paper_id, openalex_id, arxiv_id, doi, title, abstract, authors, "
        "primary_topic, publication_year, publication_date, cited_by_count, venue, pdf_url"
    )
    cols_c = "citing_paper_id, cited_paper_id"
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE core.papers, core.citations CASCADE")
        n_p = _copy_rows(
            conn,
            f"COPY core.papers ({cols_p}) FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '\\N')",
            paper_rows,
        )
        n_c = _copy_rows(
            conn,
            f"COPY core.citations ({cols_c}) FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '\\N')",
            citation_rows,
        )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("ANALYZE core.papers, core.citations")
    LOG.info("loader.copy.done", papers=n_p, citations=n_c)
    return n_p, n_c


def main() -> int:
    configure_logging(SETTINGS.log_level)
    path = SETTINGS.data_raw / "openalex_works.jsonl.gz"
    if not path.exists():
        print(f"missing {path}, run `python -m arxrec.data.openalex` first")
        return 1
    n_p, n_c = load(path)
    print(f"loaded {n_p} papers, {n_c} citation edges")
    return 0


if __name__ == "__main__":
    sys.exit(main())

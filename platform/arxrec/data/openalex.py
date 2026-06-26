"""OpenAlex ingestion.

OpenAlex is a free, no-auth scholarly graph. We use it as the single source
of truth for both paper metadata and citation edges.

Polite pool rules: include ``mailto`` in the User-Agent and you get 10 req/s
with a comfortable burst budget instead of the anonymous 5 req/s.

Filter strategy:
    primary_topic.id    one ML/AI/NLP/CV topic at a time
    locations.source.id S4306400194 (the OpenAlex id for arXiv)
    from_publication_date  recent papers only
    per-page = 200 (OpenAlex maximum), cursor pagination avoids the 10k offset cap

Abstracts come back as an inverted index (positions per token, a publisher
workaround). We reconstruct them client-side.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx

from arxrec.config import SETTINGS
from arxrec.utils.logging import configure_logging, get_logger

LOG = get_logger(__name__)

API = "https://api.openalex.org/works"
ARXIV_SOURCE_ID = "S4306400194"

# OpenAlex topic-field 17 is Computer Science. Pulling at the field level
# gives us the full ML/AI/CV/NLP/Systems mix on arXiv without listing every
# sub-topic by hand and avoids the cliff where a paper falls outside our
# whitelist by one numeric topic id.
FIELD_COMPUTER_SCIENCE = "fields/17"

SELECT_FIELDS = (
    "id,doi,title,abstract_inverted_index,authorships,publication_year,"
    "publication_date,cited_by_count,primary_topic,primary_location,locations,referenced_works"
)


def _ua() -> dict[str, str]:
    mailto = SETTINGS.openalex_mailto or "anonymous@example.com"
    return {"User-Agent": f"arxiv-recommender/0.1 (mailto:{mailto})"}


def reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str:
    if not inverted:
        return ""
    pairs: list[tuple[int, str]] = []
    for tok, positions in inverted.items():
        for p in positions:
            pairs.append((p, tok))
    pairs.sort()
    return " ".join(tok for _, tok in pairs)


_ARXIV_RE = re.compile(r"(?:abs|pdf)/(\d{4}\.\d{4,6}|[a-z\-]+/\d{7})")


def extract_arxiv_id(work: dict[str, Any]) -> str | None:
    locs = work.get("locations") or []
    for loc in locs:
        src = (loc or {}).get("source") or {}
        if "arxiv" in (src.get("display_name") or "").lower():
            url = (loc.get("landing_page_url") or "") or (loc.get("pdf_url") or "")
            if url:
                m = _ARXIV_RE.search(url)
                if m:
                    return m.group(1)
    ids = work.get("ids") or {}
    if "arxiv" in ids:
        return ids["arxiv"].rsplit("/", 1)[-1]
    return None


def fetch_page(
    client: httpx.Client,
    cursor: str,
    since: str,
    field: str = FIELD_COMPUTER_SCIENCE,
    min_cited_by: int = 0,
    max_per_page: int = 200,
) -> dict[str, Any]:
    filter_parts = [
        f"primary_topic.field.id:{field}",
        f"locations.source.id:{ARXIV_SOURCE_ID}",
        "type:article",
        f"from_publication_date:{since}",
    ]
    if min_cited_by > 0:
        filter_parts.append(f"cited_by_count:>{min_cited_by - 1}")
    params = {
        "filter": ",".join(filter_parts),
        "per-page": str(max_per_page),
        "cursor": cursor,
        "select": SELECT_FIELDS,
    }
    r = client.get(API, params=params, headers=_ua(), timeout=60.0)
    r.raise_for_status()
    return r.json()


def stream_works(
    *,
    since: str = "2019-01-01",
    cap: int = 50_000,
    min_cited_by: int = 3,
) -> Iterator[dict[str, Any]]:
    """Pull arXiv-hosted Computer Science articles published since ``since``.

    ``min_cited_by`` keeps the citation graph dense enough to be useful: papers
    with zero citations are noise for collaborative filtering, and any seed
    paper a user picks will likely have at least one citation.
    """
    with httpx.Client() as client:
        cursor = "*"
        pulled = 0
        t0 = time.perf_counter()
        consecutive_errors = 0
        last_logged = 0
        while cursor:
            try:
                data = fetch_page(client, cursor, since, min_cited_by=min_cited_by)
                consecutive_errors = 0
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code if exc.response else 0
                LOG.warning("openalex.http_error", code=code, error=str(exc)[:120])
                if 400 <= code < 500:
                    break
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    LOG.warning("openalex.too_many_errors")
                    break
                time.sleep(2.0 * consecutive_errors)
                continue
            except httpx.HTTPError as exc:
                LOG.warning("openalex.transport_error", error=str(exc)[:120])
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    break
                time.sleep(2.0 * consecutive_errors)
                continue
            results = data.get("results") or []
            yield from results
            pulled += len(results)
            meta = data.get("meta") or {}
            cursor = meta.get("next_cursor") or ""
            if pulled - last_logged >= 1000:
                LOG.info(
                    "openalex.progress",
                    pulled=pulled,
                    seconds=round(time.perf_counter() - t0, 1),
                )
                last_logged = pulled
            if pulled >= cap or not results:
                break
        LOG.info(
            "openalex.fetch.done",
            pulled=pulled,
            seconds=round(time.perf_counter() - t0, 1),
        )


def dump_to_jsonl(out_path: Path, **stream_kwargs: Any) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    seen_ids: set[str] = set()
    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        for w in stream_works(**stream_kwargs):
            wid = w.get("id")
            if not wid or wid in seen_ids:
                continue
            seen_ids.add(wid)
            f.write(json.dumps(w, ensure_ascii=False))
            f.write("\n")
            written += 1
            if written % 5000 == 0:
                LOG.info("openalex.dump.progress", written=written)
    LOG.info("openalex.dump.done", written=written, path=str(out_path))
    return written


def main() -> int:
    configure_logging(SETTINGS.log_level)
    out = SETTINGS.data_raw / "openalex_works.jsonl.gz"
    n = dump_to_jsonl(out)
    print(f"wrote {n} unique works to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

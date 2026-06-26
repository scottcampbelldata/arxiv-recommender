"""Tests for the OpenAlex abstract reconstruction + arXiv id extraction.

These run without any network calls or Postgres.
"""

from __future__ import annotations

from arxrec.data.openalex import extract_arxiv_id, reconstruct_abstract


def test_reconstruct_abstract_orders_by_position():
    # "hello world hello" stored as inverted index.
    inv = {"hello": [0, 2], "world": [1]}
    assert reconstruct_abstract(inv) == "hello world hello"


def test_reconstruct_abstract_empty():
    assert reconstruct_abstract(None) == ""
    assert reconstruct_abstract({}) == ""


def test_extract_arxiv_id_from_landing_page():
    work = {
        "locations": [{
            "source": {"display_name": "arXiv (Cornell University)"},
            "landing_page_url": "https://arxiv.org/abs/2107.03374",
        }]
    }
    assert extract_arxiv_id(work) == "2107.03374"


def test_extract_arxiv_id_from_pdf_url():
    work = {
        "locations": [{
            "source": {"display_name": "arXiv (Cornell University)"},
            "pdf_url": "https://arxiv.org/pdf/2403.05530.pdf",
        }]
    }
    assert extract_arxiv_id(work) == "2403.05530"


def test_extract_arxiv_id_none_when_no_arxiv_location():
    work = {"locations": [{"source": {"display_name": "ICML"}}]}
    assert extract_arxiv_id(work) is None

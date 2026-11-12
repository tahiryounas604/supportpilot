"""FTS5 retrieval relevance: the right document must win."""
from pathlib import Path

from supportpilot.ingest import ingest_path
from supportpilot.store import fts_match_query

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_ingest_all_fixture_types(store):
    result = ingest_path(store, FIXTURES)
    assert result["files_count"] == 3
    assert result["chunks"] >= 3
    status = store.status()
    assert status["documents"] == 3
    assert status["chunks"] == result["chunks"]


def test_password_question_ranks_password_doc_first(loaded_store):
    hits = loaded_store.search("How do I reset my password?")
    assert hits, "expected at least one hit"
    assert hits[0]["source"].endswith("password.md")
    assert "reset" in hits[0]["content"].lower()


def test_refund_question_ranks_refund_doc_first(loaded_store):
    hits = loaded_store.search("What is the refund policy for paid plans?")
    assert hits
    assert hits[0]["source"].endswith("refunds.txt")
    assert "30-day" in hits[0]["content"]


def test_shipping_question_ranks_html_doc_first(loaded_store):
    hits = loaded_store.search("How long does shipping delivery take?")
    assert hits
    assert hits[0]["source"].endswith("shipping.html")
    assert "Rotterdam" in hits[0]["content"]


def test_unrelated_question_returns_nothing(loaded_store):
    assert loaded_store.search("quantum chromodynamics lattice gauge") == []


def test_reingest_replaces_not_duplicates(store):
    ingest_path(store, FIXTURES)
    first = store.status()["chunks"]
    ingest_path(store, FIXTURES)
    assert store.status()["chunks"] == first
    assert store.status()["documents"] == 3


def test_match_query_quotes_terms_and_drops_stopwords():
    q = fts_match_query('How do I reset my "password"?')
    assert '"password"' in q
    assert '"how"' not in q.lower()

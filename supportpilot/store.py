"""SQLite FTS5 (BM25) store for document chunks."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    source TEXT PRIMARY KEY,
    title  TEXT NOT NULL,
    chunks INTEGER NOT NULL DEFAULT 0
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    source, title, content
);
"""

_STOPWORDS = {
    "a", "an", "the", "is", "are", "how", "do", "does", "i", "you", "we",
    "what", "when", "where", "why", "can", "to", "of", "for", "in", "on",
    "and", "or", "my", "me", "it", "this", "that", "with", "please",
}


def _terms(query: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9_]+", query.lower())
    terms = [w for w in words if w not in _STOPWORDS and len(w) > 1]
    return terms or words


def fts_match_query(query: str) -> str:
    """Build a safe FTS5 MATCH expression (quoted terms joined with OR)."""
    terms = _terms(query)
    if not terms:
        return '""'
    return " OR ".join(f'"{t}"' for t in dict.fromkeys(terms))


class Store:
    def __init__(self, db_path: str | Path = "supportpilot.db"):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def add_document(self, source: str, title: str, chunks: list[str]) -> int:
        """Replace any existing chunks for *source*; returns chunk count."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM chunks_fts WHERE source = ?", (source,))
        cur.execute(
            "INSERT OR REPLACE INTO documents(source, title, chunks) VALUES (?,?,?)",
            (source, title, len(chunks)),
        )
        cur.executemany(
            "INSERT INTO chunks_fts(source, title, content) VALUES (?,?,?)",
            [(source, title, c) for c in chunks],
        )
        self.conn.commit()
        return len(chunks)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """BM25 search. FTS5 bm25() returns lower = more relevant."""
        match = fts_match_query(query)
        if match == '""':
            return []
        rows = self.conn.execute(
            "SELECT source, title, content, bm25(chunks_fts) AS score "
            "FROM chunks_fts WHERE chunks_fts MATCH ? "
            "ORDER BY score ASC LIMIT ?",
            (match, int(limit)),
        ).fetchall()
        return [
            {
                "source": r["source"],
                "title": r["title"],
                "content": r["content"],
                "score": float(r["score"]),
            }
            for r in rows
        ]

    def status(self) -> dict:
        docs = self.conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
        chunks = self.conn.execute("SELECT COUNT(*) AS n FROM chunks_fts").fetchone()["n"]
        sources = [
            {"source": r["source"], "title": r["title"], "chunks": r["chunks"]}
            for r in self.conn.execute(
                "SELECT source, title, chunks FROM documents ORDER BY source"
            ).fetchall()
        ]
        return {"documents": docs, "chunks": chunks, "sources": sources}

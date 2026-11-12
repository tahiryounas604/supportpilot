"""Ingest .md / .txt / .html files or directories into the store."""
from __future__ import annotations

from pathlib import Path

from .chunker import chunk_text, extract_text
from .store import Store

SUPPORTED = {".md", ".markdown", ".txt", ".html", ".htm"}


def _title_for(text: str, path: Path) -> str:
    for line in text.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:120]
    return path.stem.replace("-", " ").replace("_", " ").title()


def ingest_text(store: Store, source: str, raw: str, suffix: str = ".txt",
                max_chars: int = 600) -> int:
    text = extract_text(raw, suffix)
    if not text:
        return 0
    chunks = chunk_text(text, max_chars=max_chars)
    title = _title_for(text, Path(source))
    return store.add_document(source, title, chunks)


def ingest_file(store: Store, path: Path, max_chars: int = 600) -> int:
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED:
        return 0
    raw = path.read_text(encoding="utf-8", errors="replace")
    return ingest_text(store, str(path), raw, path.suffix, max_chars=max_chars)


def ingest_path(store: Store, target: str | Path, max_chars: int = 600) -> dict:
    """Ingest a file or a directory (recursively). Returns a summary dict."""
    target = Path(target)
    files: list[Path] = []
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(
            p for p in target.rglob("*")
            if p.is_file() and p.suffix.lower() in SUPPORTED
        )
    else:
        raise FileNotFoundError(f"no such file or directory: {target}")
    total_chunks = 0
    ingested = []
    for f in files:
        n = ingest_file(store, f, max_chars=max_chars)
        if n:
            ingested.append(str(f))
            total_chunks += n
    return {"files": ingested, "files_count": len(ingested), "chunks": total_chunks}

"""Text extraction and chunking for .md / .txt / .html documents."""
from __future__ import annotations

import re
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    """Minimal HTML -> text extractor (skips script/style)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"):
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def extract_text(raw: str, suffix: str) -> str:
    """Return plain text for a document based on its file suffix."""
    suffix = suffix.lower()
    if suffix in (".html", ".htm"):
        parser = _TextExtractor()
        parser.feed(raw)
        text = parser.text()
    elif suffix in (".md", ".markdown"):
        text = raw
        # Strip markdown artefacts but keep the words.
        text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"[*_`>]+", "", text)
    else:  # .txt and anything else: treat as plain text
        text = raw
    # Normalise whitespace: collapse 3+ newlines, trim trailing spaces.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def chunk_text(text: str, max_chars: int = 600, overlap: int = 80) -> list[str]:
    """Split *text* into overlapping chunks on paragraph/sentence boundaries.

    Paragraphs are kept whole when possible; very long paragraphs are split
    on sentence boundaries, then hard-split if a single sentence is huge.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be >= 0 and < max_chars")
    text = text.strip()
    if not text:
        return []

    # Build units: paragraphs -> sentences if a paragraph is too long.
    units: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_chars:
            units.append(para)
        else:
            for sent in re.split(r"(?<=[.!?])\s+", para):
                sent = sent.strip()
                if not sent:
                    continue
                if len(sent) <= max_chars:
                    units.append(sent)
                else:
                    for i in range(0, len(sent), max_chars):
                        units.append(sent[i : i + max_chars])

    chunks: list[str] = []
    current = ""
    for unit in units:
        if not current:
            current = unit
        elif len(current) + 1 + len(unit) <= max_chars:
            current = current + "\n" + unit
        else:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = (tail + "\n" + unit).strip() if tail else unit
            # If overlap + unit still exceeds the limit, hard-trim the tail.
            if len(current) > max_chars:
                current = unit[:max_chars]
    if current:
        chunks.append(current)
    return [c for c in (c.strip() for c in chunks) if c]

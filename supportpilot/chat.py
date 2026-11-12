"""Chat: retrieve top passages and build an answer with sources.

Extractive mode (default, $0, no API key): the answer is composed from the
best-matching sentences of the retrieved passages — it never invents text.
If a Synthesiser is configured and enabled, its output is used instead,
with the same sources attached.
"""
from __future__ import annotations

import re

from .store import Store, _terms
from .synthesis import Synthesiser

_NO_ANSWER = (
    "I could not find anything about that in the documentation I have access to. "
    "Please try rephrasing, or contact support."
)


def _best_sentences(question: str, content: str, max_sentences: int = 3) -> str:
    terms = set(_terms(question))
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content.replace("\n", " ")) if s.strip()]
    if not sentences:
        return content.strip()[:500]

    def score(sent: str) -> int:
        words = set(re.findall(r"[A-Za-z0-9_]+", sent.lower()))
        return len(terms & words)

    ranked = sorted(range(len(sentences)), key=lambda i: (-score(sentences[i]), i))
    chosen = sorted(ranked[:max_sentences])
    return " ".join(sentences[i] for i in chosen)


def answer_question(store: Store, question: str, top_k: int = 4,
                    synthesiser: Synthesiser | None = None) -> dict:
    question = (question or "").strip()
    if not question:
        return {"answer": "Please ask a question.", "sources": [], "mode": "extractive"}
    passages = store.search(question, limit=top_k)
    if not passages:
        return {"answer": _NO_ANSWER, "sources": [], "mode": "extractive"}

    sources = [
        {"source": p["source"], "title": p["title"], "excerpt": p["content"][:300]}
        for p in passages
    ]
    if synthesiser is not None and synthesiser.enabled:
        text = synthesiser.synthesise(question, passages)
        if text:
            return {"answer": text, "sources": sources, "mode": "llm"}

    extract = _best_sentences(question, passages[0]["content"])
    return {"answer": extract, "sources": sources, "mode": "extractive"}

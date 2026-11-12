"""Optional LLM synthesis via an OpenAI-compatible chat-completions API.

Disabled by default. Enabled only when an API key is configured — the
$0 core of SupportPilot is the extractive retriever in chat.py, which
needs no key and makes no network calls.
"""
from __future__ import annotations

import json
import os
import urllib.request


class Synthesiser:
    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 model: str | None = None, timeout: float = 20.0):
        self.api_key = api_key if api_key is not None else os.environ.get(
            "SUPPORTPILOT_LLM_API_KEY", "")
        self.base_url = (base_url or os.environ.get(
            "SUPPORTPILOT_LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.environ.get("SUPPORTPILOT_LLM_MODEL", "gpt-4o-mini")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def synthesise(self, question: str, passages: list[dict]) -> str | None:
        """Return a synthesised answer, or None if disabled / on failure."""
        if not self.enabled or not passages:
            return None
        context = "\n\n".join(
            f"[{i + 1}] ({p['source']}) {p['content']}" for i, p in enumerate(passages)
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system",
                 "content": "Answer only from the provided context. Cite sources as [n]. "
                            "If the context does not contain the answer, say so."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
            ],
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return None  # caller falls back to the extractive answer

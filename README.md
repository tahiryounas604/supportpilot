# SupportPilot

Self-hosted, open-source support chatbot — a Chatbase-style alternative you run
on your own machine. Point it at your help docs, and it answers visitor
questions **from those docs, with sources**.

The core is **$0 and needs no API key**: questions are matched against your
documents with SQLite FTS5 full-text search (BM25 ranking), and the answer is
*extracted* from the best-matching passages — so it can only say what your
docs actually say. If you want more fluent answers, you can optionally plug
in your own OpenAI-compatible LLM key for synthesis on top of the same
retrieved passages.

**Zero third-party runtime dependencies** — Python standard library only
(`http.server` + `sqlite3`).

## Features

- **Ingest** `.md`, `.txt` and `.html` docs (files or whole directories,
  recursively) → automatic chunking → SQLite FTS5 (BM25) index
- **Chat API** — `POST /chat` returns an answer plus its sources
  (document name, title and excerpt for every passage used)
- **Extractive mode by default** — no API key, no network calls, answers are
  verbatim-grounded in your documents
- **Optional LLM synthesis** — set your own OpenAI-compatible key and answers
  are synthesised from the retrieved passages instead (falls back to
  extractive mode automatically if the call fails)
- **Embeddable widget** — a dependency-free vanilla-JS chat bubble you drop
  onto any site with one `<script>` tag; a demo page is served by the app
- **Admin** — CLI for ingest/status/ask, plus a token-protected HTTP ingest
  endpoint (`Authorization: Bearer …`)
- **Tests** — chunking, retrieval relevance, chat API end-to-end over real
  HTTP, auth rejection, widget/demo serving, and mocked synthesis

## Install

Requires Python 3.11 or 3.12. No packages to install for the core:

```bash
git clone <your fork URL> supportpilot
cd supportpilot
python3 -m supportpilot --help
```

(Or `pip install .` to get the `supportpilot` command. Tests need `pytest`:
`pip install pytest`.)

## Usage

### 1. Ingest your docs

```bash
python -m supportpilot --db support.db ingest examples/docs
python -m supportpilot --db support.db status
```

### 2. Ask from the terminal

```bash
python -m supportpilot --db support.db ask "How do I reset my password?"
```

### 3. Run the server

```bash
SUPPORTPILOT_ADMIN_TOKEN=choose-a-secret \
  python -m supportpilot --db support.db serve --port 8765
```

- Demo page: <http://127.0.0.1:8765/>
- Health: `GET /health` · Status: `GET /status`

```bash
curl -s -X POST http://127.0.0.1:8765/chat \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is the refund policy?"}'
```

```json
{
  "answer": "We offer a 30-day money-back guarantee on all paid plans. …",
  "sources": [{"source": "…/refunds.txt", "title": "Refund policy", "excerpt": "…"}],
  "mode": "extractive"
}
```

Ingest over HTTP (admin token required):

```bash
curl -s -X POST http://127.0.0.1:8765/ingest \
  -H 'Authorization: Bearer choose-a-secret' \
  -H 'Content-Type: application/json' \
  -d '{"source": "warranty.md", "content": "# Warranty\n\nTwo year warranty …"}'
```

Without a valid token the endpoint returns `401`, and if
`SUPPORTPILOT_ADMIN_TOKEN` is not set at all, HTTP ingest stays disabled.

### 4. Embed the widget on your site

```html
<script src="http://localhost:8765/widget.js"
        data-api="http://localhost:8765"></script>
```

That is the whole integration: a chat bubble appears in the bottom-right
corner and talks to your server's `/chat` endpoint. `data-api` can be
omitted when the widget is served from the same origin as the API.

### 5. Optional: LLM synthesis with your own key

```bash
export SUPPORTPILOT_LLM_API_KEY=sk-…            # your key, never committed
export SUPPORTPILOT_LLM_BASE_URL=https://api.openai.com/v1   # any OpenAI-compatible API
export SUPPORTPILOT_LLM_MODEL=gpt-4o-mini
python -m supportpilot --db support.db serve --port 8765
```

Responses then carry `"mode": "llm"`. With no key set, nothing changes —
extractive mode answers everything locally.

## Architecture

```
docs (.md/.txt/.html)
        │  ingest.py     extract text (HTML stripped via html.parser,
        ▼                markdown syntax removed), chunk ~600 chars w/ overlap
   chunker.py
        │  store.py      SQLite FTS5 virtual table, BM25 ranking
        ▼
  SQLite FTS5 index ──────► chat.py ──► extractive answer (best sentences
        ▲                        │       of the top passage) + sources
        │                        └────► synthesis.py (optional, your key):
        │                                OpenAI-compatible /chat/completions
   server.py (http.server, ThreadingHTTPServer)
        ├── GET  /           demo page        ├── POST /chat
        ├── GET  /widget.js  embeddable JS    └── POST /ingest (Bearer token)
        └── GET  /health, /status
   cli.py — ingest / status / ask / serve   (python -m supportpilot)
```

## Tests

```bash
python -m pytest -q
```

The suite is fully offline: the LLM test mocks the HTTP transport, and the
HTTP tests run a real server on an ephemeral localhost port.

## Honest limits

- **Extractive mode is not a generative LLM.** It quotes and recombines
  sentences from your own documents. Answers are only as good — and only as
  current — as the docs you ingest, and phrasing can be less fluent than a
  generated answer. That is the trade-off for $0, offline, and no hallucinated
  text.
- **Synthesis needs your own key** and a network connection to an
  OpenAI-compatible API; it costs whatever that provider charges. SupportPilot
  itself ships no key and makes no network calls unless you configure one.
- **Retrieval is keyword/BM25-based**, not semantic/vector search: a question
  phrased with completely different words than your docs may miss. Rephrasing
  or adding an FAQ-style doc usually fixes it.
- **Simple token auth, not a full admin system.** One shared bearer token
  protects HTTP ingest; there are no user accounts, roles, or rate limiting.
  Put it behind your own reverse proxy / firewall for internet-facing use,
  and bind to `127.0.0.1` (the default) when in doubt.
- **Single-file SQLite storage** suits small-to-medium doc sets and modest
  traffic; it is not a clustered/high-scale deployment.
- Claims in this README match what the test suite and a manual smoke test
  actually exercise: ingest of the three formats, BM25 relevance on fixture
  docs, `/chat` end-to-end, auth rejection, and widget/demo serving.

## License

GPL-3.0 — see [LICENSE](LICENSE).

## Author

Tahir Younas — Tytechlabs — https://www.linkedin.com/in/tahiryounas604

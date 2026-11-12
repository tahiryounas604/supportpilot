"""HTTP server (stdlib http.server only).

Routes:
  GET  /            demo page
  GET  /widget.js   embeddable widget
  GET  /health      {"status": "ok"}
  GET  /status      index status (document / chunk counts)
  POST /chat        {"question": "...", "top_k": 4} -> answer + sources
  POST /ingest      admin-token protected; {"source": "x.md", "content": "..."}
                    or {"path": "/server/local/path"} to ingest from disk
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .chat import answer_question
from .ingest import ingest_path, ingest_text
from .store import Store
from .synthesis import Synthesiser

_STATIC = Path(__file__).parent / "static"


def make_handler(store: Store, admin_token: str | None = None,
                 synthesiser: Synthesiser | None = None):
    token = admin_token if admin_token is not None else os.environ.get(
        "SUPPORTPILOT_ADMIN_TOKEN", "")
    synth = synthesiser if synthesiser is not None else Synthesiser()

    class Handler(BaseHTTPRequestHandler):
        server_version = "SupportPilot/0.1"

        def log_message(self, *args):  # keep test output clean
            pass

        def _send(self, code: int, body: bytes, content_type: str):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj: dict):
            self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return {}

        def _authorised(self) -> bool:
            if not token:
                return False  # ingest is disabled until a token is configured
            auth = self.headers.get("Authorization", "")
            return auth == f"Bearer {token}"

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()

        def do_GET(self):
            if self.path in ("/", "/demo", "/demo.html"):
                self._send(200, (_STATIC / "demo.html").read_bytes(),
                           "text/html; charset=utf-8")
            elif self.path == "/widget.js":
                self._send(200, (_STATIC / "widget.js").read_bytes(),
                           "application/javascript; charset=utf-8")
            elif self.path == "/health":
                self._json(200, {"status": "ok"})
            elif self.path == "/status":
                self._json(200, store.status())
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if self.path == "/chat":
                data = self._read_json()
                question = data.get("question") or data.get("message") or ""
                if not str(question).strip():
                    self._json(400, {"error": "question is required"})
                    return
                top_k = data.get("top_k", 4)
                try:
                    top_k = max(1, min(int(top_k), 20))
                except (TypeError, ValueError):
                    top_k = 4
                self._json(200, answer_question(store, str(question), top_k=top_k,
                                                synthesiser=synth))
            elif self.path == "/ingest":
                if not self._authorised():
                    self._json(401, {"error": "unauthorized: admin token required"})
                    return
                data = self._read_json()
                try:
                    if data.get("path"):
                        result = ingest_path(store, data["path"])
                        self._json(200, result)
                    elif data.get("content") is not None:
                        source = str(data.get("source") or "uploaded.txt")
                        suffix = Path(source).suffix or ".txt"
                        n = ingest_text(store, source, str(data["content"]), suffix)
                        self._json(200, {"files": [source], "files_count": 1, "chunks": n})
                    else:
                        self._json(400, {"error": "provide 'path' or 'source'+'content'"})
                except FileNotFoundError as exc:
                    self._json(404, {"error": str(exc)})
            else:
                self._json(404, {"error": "not found"})

    return Handler


def serve(db_path: str = "supportpilot.db", host: str = "127.0.0.1",
          port: int = 8765, admin_token: str | None = None) -> ThreadingHTTPServer:
    store = Store(db_path)
    httpd = ThreadingHTTPServer((host, port), make_handler(store, admin_token))
    httpd.store = store  # type: ignore[attr-defined]
    return httpd


def main(argv=None) -> int:  # pragma: no cover - thin wrapper, exercised via CLI
    import argparse
    p = argparse.ArgumentParser(prog="supportpilot-serve")
    p.add_argument("--db", default="supportpilot.db")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)
    httpd = serve(args.db, args.host, args.port)
    print(f"SupportPilot serving on http://{args.host}:{args.port} (db: {args.db})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

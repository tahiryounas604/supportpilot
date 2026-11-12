"""Command-line interface: ingest, status, serve, ask."""
from __future__ import annotations

import argparse
import json
import sys

from .chat import answer_question
from .ingest import ingest_path
from .server import serve
from .store import Store


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="supportpilot",
                                     description="Self-hosted extractive support chatbot")
    parser.add_argument("--db", default="supportpilot.db", help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingest .md/.txt/.html files or a directory")
    p_ingest.add_argument("path", help="File or directory to ingest")

    sub.add_parser("status", help="Show index status")

    p_ask = sub.add_parser("ask", help="Ask one question from the terminal")
    p_ask.add_argument("question")

    p_serve = sub.add_parser("serve", help="Run the HTTP server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)

    args = parser.parse_args(argv)

    if args.command == "serve":
        httpd = serve(args.db, args.host, args.port)
        print(f"SupportPilot serving on http://{args.host}:{args.port} (db: {args.db})")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0

    store = Store(args.db)
    try:
        if args.command == "ingest":
            try:
                result = ingest_path(store, args.path)
            except FileNotFoundError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "status":
            print(json.dumps(store.status(), indent=2))
            return 0
        if args.command == "ask":
            print(json.dumps(answer_question(store, args.question), indent=2))
            return 0
    finally:
        store.close()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

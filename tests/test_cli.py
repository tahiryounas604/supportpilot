import json
from pathlib import Path

from supportpilot.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_cli_ingest_status_ask(tmp_path, capsys):
    db = str(tmp_path / "cli.db")
    assert main(["--db", db, "ingest", str(FIXTURES)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["files_count"] == 3

    assert main(["--db", db, "status"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["documents"] == 3

    assert main(["--db", db, "ask", "How do I reset my password?"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["sources"][0]["source"].endswith("password.md")


def test_cli_ingest_missing_path(tmp_path, capsys):
    db = str(tmp_path / "cli.db")
    assert main(["--db", db, "ingest", str(tmp_path / "nope")]) == 2

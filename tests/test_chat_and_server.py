"""Chat API end-to-end over real HTTP on a test port, plus auth checks."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from supportpilot.chat import answer_question
from supportpilot.server import make_handler

TOKEN = "test-admin-token"


@pytest.fixture()
def base_url(loaded_store):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(loaded_store, admin_token=TOKEN))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _request(url, method="GET", payload=None, headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _post(url, payload, headers=None):
    status, body = _request(url, "POST", payload, headers)
    return status, json.loads(body)


# ---- chat logic (in-process) ----

def test_extractive_answer_has_sources(loaded_store):
    result = answer_question(loaded_store, "How do I reset my password?")
    assert result["mode"] == "extractive"
    assert "password" in result["answer"].lower()
    assert result["sources"]
    assert result["sources"][0]["source"].endswith("password.md")


def test_no_match_gives_honest_no_answer(loaded_store):
    result = answer_question(loaded_store, "quantum chromodynamics lattice")
    assert result["sources"] == []
    assert "could not find" in result["answer"].lower()


def test_empty_question(loaded_store):
    result = answer_question(loaded_store, "   ")
    assert result["sources"] == []


# ---- HTTP end-to-end ----

def test_chat_endpoint_end_to_end(base_url):
    status, data = _post(base_url + "/chat", {"question": "What is the refund policy?"})
    assert status == 200
    assert data["mode"] == "extractive"
    assert "refund" in data["answer"].lower()
    assert data["sources"][0]["source"].endswith("refunds.txt")


def test_chat_endpoint_requires_question(base_url):
    status, _ = _post(base_url + "/chat", {"question": "  "})
    assert status == 400


def test_health_and_status(base_url):
    status, body = _request(base_url + "/health")
    assert status == 200 and json.loads(body)["status"] == "ok"
    status, body = _request(base_url + "/status")
    data = json.loads(body)
    assert status == 200 and data["documents"] == 3 and data["chunks"] >= 3


def test_demo_page_serves_200(base_url):
    status, body = _request(base_url + "/")
    assert status == 200
    assert "SupportPilot Demo" in body
    assert "/widget.js" in body


def test_widget_js_serves_200(base_url):
    status, body = _request(base_url + "/widget.js")
    assert status == 200
    assert "sp-bubble" in body
    assert "/chat" in body


def test_unknown_route_404(base_url):
    status, _ = _request(base_url + "/nope")
    assert status == 404


# ---- ingest auth ----

def test_ingest_rejected_without_token(base_url):
    status, _ = _post(base_url + "/ingest",
                      {"source": "x.txt", "content": "secret doors and keys"})
    assert status == 401


def test_ingest_rejected_with_wrong_token(base_url):
    status, _ = _post(base_url + "/ingest",
                      {"source": "x.txt", "content": "secret doors and keys"},
                      headers={"Authorization": "Bearer wrong"})
    assert status == 401


def test_ingest_accepted_with_token_then_chat_finds_it(base_url):
    status, data = _post(
        base_url + "/ingest",
        {"source": "warranty.md",
         "content": "# Warranty\n\nEvery device includes a two year warranty "
                    "covering parts and labour for manufacturing defects."},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert status == 200
    assert data["chunks"] >= 1
    status, data = _post(base_url + "/chat", {"question": "How long is the warranty?"})
    assert status == 200
    assert data["sources"][0]["source"] == "warranty.md"

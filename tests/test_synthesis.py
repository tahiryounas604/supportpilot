"""Optional LLM synthesis: mocked transport, no network."""
import io
import json

import supportpilot.synthesis as synthesis_mod
from supportpilot.chat import answer_question
from supportpilot.synthesis import Synthesiser


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _fake_urlopen_factory(reply_text):
    def fake_urlopen(req, timeout=None):
        body = json.loads(req.data.decode())
        assert body["model"] == "test-model"
        assert "Context:" in body["messages"][1]["content"]
        payload = {"choices": [{"message": {"content": reply_text}}]}
        return _FakeResponse(json.dumps(payload).encode())
    return fake_urlopen


def test_disabled_without_key(loaded_store, monkeypatch):
    monkeypatch.delenv("SUPPORTPILOT_LLM_API_KEY", raising=False)
    synth = Synthesiser(api_key="")
    assert not synth.enabled
    result = answer_question(loaded_store, "How do I reset my password?", synthesiser=synth)
    assert result["mode"] == "extractive"


def test_synthesis_used_when_key_configured(loaded_store, monkeypatch):
    monkeypatch.setattr(synthesis_mod.urllib.request, "urlopen",
                        _fake_urlopen_factory("Use the reset link [1]."))
    synth = Synthesiser(api_key="sk-test", model="test-model")
    assert synth.enabled
    result = answer_question(loaded_store, "How do I reset my password?", synthesiser=synth)
    assert result["mode"] == "llm"
    assert result["answer"] == "Use the reset link [1]."
    assert result["sources"][0]["source"].endswith("password.md")


def test_synthesis_failure_falls_back_to_extractive(loaded_store, monkeypatch):
    def boom(req, timeout=None):
        raise OSError("network down")
    monkeypatch.setattr(synthesis_mod.urllib.request, "urlopen", boom)
    synth = Synthesiser(api_key="sk-test", model="test-model")
    result = answer_question(loaded_store, "How do I reset my password?", synthesiser=synth)
    assert result["mode"] == "extractive"
    assert "password" in result["answer"].lower()

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app import llm
from app.main import app

client = TestClient(app)


@pytest.fixture
def azure_env(monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")


def test_index_served():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "mic" in resp.text


def test_speech_token_returns_token_not_key(azure_env):
    def handler(request):
        assert request.headers["Ocp-Apim-Subscription-Key"] == "speech-key"
        assert request.url.host == "eastus.api.cognitive.microsoft.com"
        return httpx.Response(200, text="short-lived-token")

    real_client = httpx.AsyncClient
    with patch("app.main.httpx.AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler))):
        resp = client.get("/api/speech-token")
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"] == "short-lived-token"
    assert body["region"] == "eastus"
    assert "speech-key" not in resp.text


def test_speech_token_missing_key(monkeypatch):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    resp = client.get("/api/speech-token")
    assert resp.status_code == 500
    assert "AZURE_SPEECH_KEY" in resp.json()["detail"]


def test_ask_uses_knowledge_and_history(azure_env, monkeypatch):
    monkeypatch.setattr(llm, "load_knowledge", lambda: "We open at 9am.")
    fake = MagicMock()
    fake.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content=" We open at 9am. "))]
    with patch.object(llm, "_client", return_value=fake):
        resp = client.post(
            "/api/ask",
            json={"question": "When do you open?", "history": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Hello!"}]},
        )
    assert resp.status_code == 200
    assert resp.json() == {"answer": "We open at 9am."}
    kwargs = fake.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    assert "We open at 9am." in kwargs["messages"][0]["content"]
    assert [m["role"] for m in kwargs["messages"]] == ["system", "user", "assistant", "user"]


def test_ask_missing_config(monkeypatch):
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    resp = client.post("/api/ask", json={"question": "hi"})
    assert resp.status_code == 500
    assert "AZURE_OPENAI_DEPLOYMENT" in resp.json()["detail"]


def test_ask_rejects_bad_role():
    resp = client.post("/api/ask", json={"question": "hi", "history": [{"role": "system", "content": "x"}]})
    assert resp.status_code == 422

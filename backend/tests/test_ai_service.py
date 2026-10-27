"""AI Mentor service regression tests.

Covers the bugs fixed in the mentor repair:
- SecretStr keys unwrapped in Authorization headers (str(SecretStr) is masked)
- Gemini key sent via header, never in the request URL
- OpenAI insufficient_quota fails over instead of leaking billing text to students
- provider failover chain reaches Gemini when OpenAI is down
- all-providers-down path serves the offline fallback without raising
  (the old code passed an invalid kwarg to logger.warning -> TypeError)
- chat() reports the provider that actually served the reply

All provider calls are scripted — no network access, no live keys.
"""

import httpx
import pytest
from pydantic import SecretStr

from app.api.v1.endpoints import ai as ai_endpoint
from app.core.config import settings
from app.services.ai_service import AIService, _unwrap_secret

# asyncio_mode = "auto" (pyproject) marks the async tests automatically.


MESSAGES = [{"role": "user", "content": "Explain port scanning."}]


@pytest.fixture(autouse=True)
def _isolate_provider_settings(monkeypatch):
    """Every test controls the provider keys explicitly (never the real .env)."""
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    yield


@pytest.fixture(autouse=True)
def _clear_chat_rate_limit():
    ai_endpoint._chat_buckets.clear()
    yield
    ai_endpoint._chat_buckets.clear()


def _install_script(monkeypatch, script, calls):
    """Replace httpx.AsyncClient with a scripted stand-in.

    script: list of (status_code, json_body) popped one per POST.
    calls:  list that records {url, headers, json} of every POST.
    """

    class ScriptedClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None, **kwargs):
            calls.append({"url": url, "headers": headers or {}, "json": json})
            status, body = script.pop(0)
            request = httpx.Request("POST", url)
            return httpx.Response(status, json=body, request=request)

    monkeypatch.setattr(httpx, "AsyncClient", ScriptedClient)


# --- SecretStr handling ------------------------------------------------------


def test_unwrap_secret_passes_plain_values_through():
    assert _unwrap_secret(None) is None
    assert _unwrap_secret("plain") == "plain"


def test_unwrap_secret_extracts_masked_value():
    assert _unwrap_secret(SecretStr("sk-real-key")) == "sk-real-key"


def test_auth_header_contains_raw_key_not_mask(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", SecretStr("sk-test-123"))
    service = AIService()
    header = service._headers["Authorization"]
    assert header == "Bearer sk-test-123"
    assert "****" not in header


# --- OpenAI quota handling ---------------------------------------------------


async def test_openai_insufficient_quota_raises_instead_of_replying(monkeypatch):
    """A 429 quota error must raise so the chain fails over — it must never be
    returned as a student-facing chat reply."""
    monkeypatch.setattr(settings, "OPENAI_API_KEY", SecretStr("sk-broke"))
    calls = []
    _install_script(
        monkeypatch,
        [(429, {"error": {"type": "insufficient_quota", "message": "You exceeded your current quota."}})],
        calls,
    )

    service = AIService()
    with pytest.raises(httpx.HTTPStatusError):
        await service._openai_chat(MESSAGES, 0.7, 500, None)


async def test_quota_error_never_surfaces_billing_text_to_students(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", SecretStr("sk-broke"))
    calls = []
    _install_script(
        monkeypatch,
        [(429, {"error": {"type": "insufficient_quota", "message": "quota exceeded"}})],
        calls,
    )

    reply = await AIService()._chat(MESSAGES)
    assert isinstance(reply, str)
    assert "SYSTEM ALERT" not in reply
    assert "credits" not in reply.lower()
    assert "platform.openai.com" not in reply


# --- Provider failover -------------------------------------------------------


async def test_failover_openai_down_gemini_serves(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", SecretStr("sk-broke"))
    monkeypatch.setattr(settings, "GEMINI_API_KEY", SecretStr("AIza-test-key"))
    calls = []
    _install_script(
        monkeypatch,
        [
            (500, {"error": {"message": "internal error"}}),
            (200, {"candidates": [{"content": {"parts": [{"text": "gemini reply"}]}}]}),
        ],
        calls,
    )

    service = AIService()
    reply = await service._chat(MESSAGES)
    assert reply == "gemini reply"
    assert service.served_by == "gemini"
    # Two provider calls happened: OpenAI first, Gemini second.
    assert len(calls) == 2
    assert "api.openai.com" in calls[0]["url"]
    assert "generativelanguage.googleapis.com" in calls[1]["url"]


async def test_gemini_key_sent_in_header_not_url(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", SecretStr("AIza-super-secret"))
    calls = []
    _install_script(
        monkeypatch,
        [(200, {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})],
        calls,
    )

    reply = await AIService()._chat(MESSAGES)
    assert reply == "ok"

    call = calls[0]
    assert "AIza-super-secret" not in call["url"]  # key never in the URL
    assert call["headers"].get("x-goog-api-key") == "AIza-super-secret"


async def test_all_providers_down_serves_offline_fallback(monkeypatch):
    """Regression: logger.warning('...', error=...) raised TypeError on this
    path and turned the fallback into a 503."""
    monkeypatch.setattr(settings, "OPENAI_API_KEY", SecretStr("sk-down"))
    monkeypatch.setattr(settings, "GEMINI_API_KEY", SecretStr("AIza-down"))
    calls = []
    _install_script(
        monkeypatch,
        [
            (500, {"error": {"message": "boom"}}),
            (503, {"error": {"message": "unavailable"}}),
        ],
        calls,
    )

    reply = await AIService()._chat(MESSAGES)
    assert isinstance(reply, str)
    assert reply.startswith("CyberVerse Mentor:")
    assert "OPENAI_API_KEY" not in reply  # student-facing text stays clean


async def test_no_provider_configured_serves_fallback_without_network(monkeypatch):
    calls = []
    _install_script(monkeypatch, [], calls)

    reply = await AIService()._chat(MESSAGES)
    assert isinstance(reply, str)
    assert reply.startswith("CyberVerse Mentor:")
    assert calls == []  # nothing to call without keys


# --- chat() response contract ------------------------------------------------


async def test_chat_reports_provider_that_actually_served_reply(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", SecretStr("sk-down"))
    monkeypatch.setattr(settings, "GEMINI_API_KEY", SecretStr("AIza-live"))
    calls = []
    _install_script(
        monkeypatch,
        [
            (500, {"error": {"message": "down"}}),
            (200, {"candidates": [{"content": {"parts": [{"text": "hello student"}]}}]}),
        ],
        calls,
    )

    result = await AIService().chat([{"role": "user", "content": "hi"}])
    assert result["reply"] == "hello student"
    assert result["model"] == settings.GEMINI_MODEL  # honest label, not gpt-4o-mini


async def test_chat_fallback_model_label(monkeypatch):
    calls = []
    _install_script(monkeypatch, [], calls)

    result = await AIService().chat([{"role": "user", "content": "hi"}])
    assert result["model"] == "offline-fallback"
    assert result["reply"].startswith("CyberVerse Mentor:")


async def test_openrouter_model_id_not_forwarded_to_openai(monkeypatch):
    """An OpenRouter model id would 404 on api.openai.com during failover."""
    monkeypatch.setattr(settings, "OPENAI_API_KEY", SecretStr("sk-live"))
    calls = []
    _install_script(
        monkeypatch,
        [(200, {"choices": [{"message": {"content": "openai reply"}}]})],
        calls,
    )

    reply = await AIService()._chat(MESSAGES, model="openrouter/auto")
    assert reply == "openai reply"
    sent_model = calls[0]["json"]["model"]
    assert not sent_model.startswith("openrouter/")


# --- Endpoint wiring ---------------------------------------------------------


class _FakeAIService:
    async def chat(self, history, context=""):
        assert isinstance(history, list) and history
        return {"reply": "mentor reply", "model": "test-model"}


async def test_chat_endpoint_returns_reply_for_guest(client, monkeypatch):
    monkeypatch.setattr(ai_endpoint, "AIService", _FakeAIService)

    r = await client.post(
        "/api/v1/ai/chat",
        json={"messages": [{"role": "user", "content": "What is a firewall?"}]},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["reply"] == "mentor reply"
    assert data["model"] == "test-model"


async def test_chat_endpoint_rate_limit(client, monkeypatch):
    monkeypatch.setattr(ai_endpoint, "AIService", _FakeAIService)

    payload = {"messages": [{"role": "user", "content": "hello"}]}
    limit = settings.AI_CHAT_RATE_LIMIT_PER_MINUTE
    for _ in range(limit):
        r = await client.post("/api/v1/ai/chat", json=payload)
        assert r.status_code == 200, r.text

    r = await client.post("/api/v1/ai/chat", json=payload)
    assert r.status_code == 429


async def test_chat_endpoint_rejects_empty_history(client, monkeypatch):
    monkeypatch.setattr(ai_endpoint, "AIService", _FakeAIService)

    r = await client.post("/api/v1/ai/chat", json={"messages": []})
    assert r.status_code == 422

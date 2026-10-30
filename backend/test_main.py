"""Offline tests; no provider credentials or network calls needed."""
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


import pytest


@pytest.fixture(autouse=True)
def isolated_test_state(monkeypatch):
    """Tests must not inherit local preview or production configuration."""
    monkeypatch.setattr(main, "PUBLIC_DEPLOYMENT", False)
    monkeypatch.setattr(main, "TURNSTILE_EXPECTED_HOSTNAME", "taibfaiu-creator.github.io")
    main.request_times.clear()
    main.daily_requests.clear()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_input_validation():
    response = client.post("/api/chat", json={"message": "", "history": []})
    assert response.status_code == 422


def test_gemini_success(monkeypatch):
    async def primary(message, history):
        return "Profile answer"

    async def must_not_call(message, history):
        raise AssertionError("Fallback should not be used")

    monkeypatch.setattr(main, "gemini_answer", primary)
    monkeypatch.setattr(main, "groq_answer", must_not_call)
    result = client.post("/api/chat", json={"message": "Who is Al-Tayeb?"})
    assert result.status_code == 200
    assert result.json()["source"] == "gemini"
    assert result.json()["fallback_used"] is False


def test_groq_fallback(monkeypatch):
    async def primary_failure(message, history):
        raise main.ProviderUnavailable("quota reached")

    async def secondary(message, history):
        return "Fallback answer"

    monkeypatch.setattr(main, "gemini_answer", primary_failure)
    monkeypatch.setattr(main, "groq_answer", secondary)
    result = client.post("/api/chat", json={"message": "Tell me about his projects"})
    assert result.status_code == 200
    assert result.json()["source"] == "groq"
    assert result.json()["answer"] == "Fallback answer"


def test_static_last_resort(monkeypatch):
    async def failed(message, history):
        raise main.ProviderUnavailable("unavailable")

    monkeypatch.setattr(main, "gemini_answer", failed)
    monkeypatch.setattr(main, "groq_answer", failed)
    result = client.post("/api/chat", json={"message": "مرحبا"})
    assert result.status_code == 200
    assert result.json()["source"] == "static"
    assert "غير متاح" in result.json()["answer"]


def test_oversized_request_rejected():
    result = client.post("/api/chat", json={"message": "x" * 17000})
    assert result.status_code == 413


def test_public_mode_without_secret_fails_closed(monkeypatch):
    monkeypatch.setattr(main, "PUBLIC_DEPLOYMENT", True)
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    result = client.post("/api/chat", json={"message": "Hello"})
    assert result.status_code == 503


def test_public_mode_requires_turnstile_token(monkeypatch):
    monkeypatch.setattr(main, "PUBLIC_DEPLOYMENT", True)
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "fake-test-secret")
    result = client.post("/api/chat", json={"message": "Hello"})
    assert result.status_code == 403


def test_daily_provider_budget_blocks_after_limit(monkeypatch):
    import asyncio
    from collections import deque
    from fastapi import HTTPException

    monkeypatch.setattr(main, "daily_requests", deque())

    async def use_budget():
        for _ in range(main.MAX_DAILY_REQUESTS_PER_PROCESS):
            await main.check_daily_provider_budget()
        try:
            await main.check_daily_provider_budget()
        except HTTPException as exc:
            assert exc.status_code == 429
        else:
            raise AssertionError("Daily limit did not reject excess request")

    asyncio.run(use_budget())


def test_busy_provider_does_not_call_model(monkeypatch):
    import asyncio

    monkeypatch.setattr(main, "provider_slots", asyncio.Semaphore(0))
    response = client.post("/api/chat", json={"message": "Tell me about his work"})
    assert response.status_code == 429
    assert "busy" in response.json()["detail"].lower()


def test_turnstile_verification_accepts_valid_domain(monkeypatch):
    import httpx

    monkeypatch.setattr(main, "PUBLIC_DEPLOYMENT", True)
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "test-only-secret")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"success": True, "hostname": "taibfaiu-creator.github.io"}
        )
    )
    original_client = httpx.AsyncClient
    monkeypatch.setattr(main.httpx, "AsyncClient",
                        lambda **kwargs: original_client(transport=transport, **kwargs))

    async def provider(message, history):
        return "Verified answer"

    monkeypatch.setattr(main, "gemini_answer", provider)
    response = client.post("/api/chat", json={"message": "About Al-Tayeb", "turnstile_token": "test-token"})
    assert response.status_code == 200
    assert response.json()["source"] == "gemini"


def test_turnstile_rejects_invalid_expired_and_wrong_domain(monkeypatch):
    import httpx

    monkeypatch.setattr(main, "PUBLIC_DEPLOYMENT", True)
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "test-only-secret")
    original_client = httpx.AsyncClient
    provider_called = []

    async def forbidden_provider(message, history):
        provider_called.append(True)
        raise AssertionError("Provider must never run after verification failure")

    monkeypatch.setattr(main, "gemini_answer", forbidden_provider)
    monkeypatch.setattr(main, "groq_answer", forbidden_provider)

    cases = [
        {"success": False, "error-codes": ["invalid-input-response"]},
        {"success": False, "error-codes": ["timeout-or-duplicate"]},
        {"success": True, "hostname": "untrusted.example"},
    ]
    for verification in cases:
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=verification))
        monkeypatch.setattr(main.httpx, "AsyncClient",
                            lambda **kwargs: original_client(transport=transport, **kwargs))
        response = client.post("/api/chat", json={"message": "Hello", "turnstile_token": "test-token"})
        assert response.status_code == 403
    assert not provider_called


def test_system_prompt_uses_latest_question_language():
    english = main.system_prompt("What is his experience?")
    arabic = main.system_prompt("ما هي خبراته المهنية؟")
    assert "Answer entirely in English" in english
    assert "Answer entirely in Arabic" in arabic
    assert "plain text only" in english
    assert "Do not switch languages because of older conversation history" in arabic

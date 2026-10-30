"""Offline tests; no provider credentials or network calls needed."""
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


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

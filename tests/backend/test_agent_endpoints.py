from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.streaming import format_sse


def _client() -> TestClient:
    app = create_app()
    app.state.config = object()
    app.state.embedder = object()
    return TestClient(app)


async def _fake_prompted_events(config, deps, prompt, kind):
    yield format_sse("status", {"phase": "thinking"})
    yield format_sse("tool", {"query": "vat"})
    yield format_sse("token", {"text": "answer"})
    yield format_sse("done", {})


def test_ask_streams_sse():
    client = _client()
    with patch("backend.routes.prompted_sse_events", _fake_prompted_events):
        response = client.post("/api/ask", json={"question": "hi"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: token" in body
    assert '"text": "answer"' in body
    assert "event: done" in body


def test_check_streams_sse():
    client = _client()
    with patch("backend.routes.prompted_sse_events", _fake_prompted_events):
        response = client.post("/api/check", json={"document": "policy text"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: done" in response.text

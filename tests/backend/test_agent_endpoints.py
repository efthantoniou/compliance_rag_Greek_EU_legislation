from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.streaming import format_sse


def _client() -> TestClient:
    app = create_app()
    app.state.config = object()
    app.state.embedder = object()
    app.state.ask_agent = object()
    app.state.check_agent = object()
    return TestClient(app)


async def _fake_events(agent, prompt, deps):
    yield format_sse("status", {"phase": "thinking"})
    yield format_sse("token", {"text": "answer"})
    yield format_sse("done", {})


def test_ask_streams_sse():
    client = _client()
    with patch("backend.routes.agent_sse_events", _fake_events):
        response = client.post("/api/ask", json={"question": "hi"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: token" in body
    assert '"text": "answer"' in body
    assert "event: done" in body


def test_check_streams_sse():
    client = _client()
    with patch("backend.routes.agent_sse_events", _fake_events):
        response = client.post("/api/check", json={"document": "policy text"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: done" in response.text

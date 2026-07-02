from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app
from models import Chunk


def _client() -> TestClient:
    app = create_app()
    app.state.config = object()
    app.state.embedder = object()
    return TestClient(app)


def test_search_returns_mapped_results():
    client = _client()
    chunks = [
        Chunk(text="alpha", celex_id="A1", labels=["100149"]),
        Chunk(text="beta", celex_id="A2", labels=["100160"]),
    ]
    with patch("backend.routes.search", return_value=chunks) as mock_search:
        response = client.post("/api/search", json={"query": "tax", "top_k": 2})

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {"celex_id": "A1", "labels": ["100149"], "text": "alpha"},
            {"celex_id": "A2", "labels": ["100160"], "text": "beta"},
        ]
    }
    # config, embedder come from app state; query/top_k/label from the request
    args, kwargs = mock_search.call_args
    assert args[2] == "tax"
    assert kwargs == {"top_k": 2, "label_filter": None}


def test_search_defaults_top_k_to_5():
    client = _client()
    with patch("backend.routes.search", return_value=[]) as mock_search:
        response = client.post("/api/search", json={"query": "x"})

    assert response.status_code == 200
    assert response.json() == {"results": []}
    _, kwargs = mock_search.call_args
    assert kwargs == {"top_k": 5, "label_filter": None}

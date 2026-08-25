from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app
from models import Chunk


def _client() -> TestClient:
    app = create_app()
    app.state.config = SimpleNamespace(
        retrieval_min_score=0.10,
        retrieval_weak_score=0.50,
    )
    app.state.embedder = object()
    return TestClient(app)


def test_search_returns_mapped_results():
    client = _client()
    scored = [
        (Chunk(text="alpha", celex_id="A1", labels=["100149"]), 0.91),
        (Chunk(text="beta", celex_id="A2", labels=["100160"]), 0.77),
    ]
    with patch("backend.routes.search_scored", return_value=scored) as mock_search:
        response = client.post("/api/search", json={"query": "tax", "top_k": 2})

    assert response.status_code == 200
    assert response.json() == {
        "status": "grounded",
        "top_score": 0.91,
        "results": [
            {
                "celex_id": "A1",
                "labels": [
                    {"id": "100149", "el": "κοινωνικα θεματα", "en": "social questions"}
                ],
                "subtopics": [],
                "topics": [],
                "text": "alpha",
                "score": 0.91,
            },
            {
                "celex_id": "A2",
                "labels": [
                    {"id": "100160", "el": "βιομηχανια", "en": "industry"}
                ],
                "subtopics": [],
                "topics": [],
                "text": "beta",
                "score": 0.77,
            },
        ],
    }
    # config, embedder come from app state; query/top_k/label from the request
    args, kwargs = mock_search.call_args
    assert args[2] == "tax"
    assert kwargs == {"top_k": 2, "label_filter": None}


def test_labels_endpoint_returns_21_sorted_domains():
    client = _client()
    response = client.get("/api/labels")
    assert response.status_code == 200
    labels = response.json()["labels"]
    assert len(labels) == 21
    # every entry is a resolved concept, sorted by Greek descriptor
    assert all({"id", "el", "en"} <= set(c) for c in labels)
    assert [c["el"] for c in labels] == sorted(c["el"] for c in labels)


def test_search_defaults_top_k_to_5():
    client = _client()
    with patch("backend.routes.search_scored", return_value=[]) as mock_search:
        response = client.post("/api/search", json={"query": "x"})

    assert response.status_code == 200
    _, kwargs = mock_search.call_args
    assert kwargs == {"top_k": 5, "label_filter": None}


def test_search_drops_results_below_min_score():
    """Vector search always returns top_k, so the padding has to be filtered."""
    client = _client()
    scored = [
        (Chunk(text="good", celex_id="A1", labels=[]), 0.88),
        (Chunk(text="junk", celex_id="A2", labels=[]), 0.02),
    ]
    with patch("backend.routes.search_scored", return_value=scored):
        body = client.post("/api/search", json={"query": "x"}).json()

    assert [r["celex_id"] for r in body["results"]] == ["A1"]
    assert body["status"] == "grounded"


def test_search_refuses_when_everything_is_below_min_score():
    client = _client()
    scored = [
        (Chunk(text="junk", celex_id="A1", labels=[]), 0.05),
        (Chunk(text="junk", celex_id="A2", labels=[]), 0.01),
    ]
    with patch("backend.routes.search_scored", return_value=scored):
        body = client.post("/api/search", json={"query": "μουσακάς"}).json()

    assert body["results"] == []
    assert body["status"] == "refused"
    assert body["top_score"] == 0.05


def test_search_marks_weak_when_best_hit_is_mediocre():
    client = _client()
    scored = [(Chunk(text="maybe", celex_id="A1", labels=[]), 0.31)]
    with patch("backend.routes.search_scored", return_value=scored):
        body = client.post("/api/search", json={"query": "x"}).json()

    assert body["status"] == "weak"
    assert len(body["results"]) == 1


def test_search_keeps_everything_when_reranking_is_off():
    """Scores are None without a cross-encoder pass; that is not a score of 0."""
    client = _client()
    scored = [(Chunk(text="a", celex_id="A1", labels=[]), None)]
    with patch("backend.routes.search_scored", return_value=scored):
        body = client.post("/api/search", json={"query": "x"}).json()

    assert body["status"] == "grounded"
    assert body["top_score"] is None
    assert len(body["results"]) == 1

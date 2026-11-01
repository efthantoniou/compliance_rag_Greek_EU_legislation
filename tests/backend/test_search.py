from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app
from models import Chunk


def _client() -> TestClient:
    app = create_app()
    app.state.config = SimpleNamespace(retrieval_min_score=0.55, search_pool=50)
    app.state.embedder = object()
    return TestClient(app)


def _scored(*scores):
    return [(Chunk(text=f"t{i}", celex_id=f"A{i}", labels=[]), s) for i, s in enumerate(scores)]


def test_search_returns_mapped_results_with_page_info():
    client = _client()
    scored = [
        (Chunk(text="alpha", celex_id="A1", labels=["100149"]), 0.91),
        (Chunk(text="beta", celex_id="A2", labels=["100160"]), 0.77),
    ]
    with patch("backend.routes.rank_pool", return_value=scored) as mock_rank:
        response = client.post("/api/search", json={"query": "tax"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "grounded",
        "top_score": 0.91,
        "total": 2,
        "page": 1,
        "page_size": 10,
        "results": [
            {
                "celex_id": "A1",
                "labels": [
                    {"id": "100149", "el": "κοινωνικά θέματα", "en": "social questions"}
                ],
                "subtopics": [],
                "topics": [],
                "text": "alpha",
                "score": 0.91,
                "matches": 1,
            },
            {
                "celex_id": "A2",
                "labels": [
                    {"id": "100160", "el": "βιομηχανία", "en": "industry"}
                ],
                "subtopics": [],
                "topics": [],
                "text": "beta",
                "score": 0.77,
                "matches": 1,
            },
        ],
    }
    # config, embedder come from app state; the pool size from config
    args, kwargs = mock_rank.call_args
    assert args[2] == "tax"
    assert kwargs == {"pool": 50, "label_filter": None}


def test_labels_endpoint_returns_21_sorted_domains():
    client = _client()
    response = client.get("/api/labels")
    assert response.status_code == 200
    labels = response.json()["labels"]
    assert len(labels) == 21
    # every entry is a resolved concept, sorted alphabetically ignoring accents/case
    assert all({"id", "el", "en"} <= set(c) for c in labels)
    assert labels[0]["el"] == "απασχόληση και συνθήκες εργασίας"
    assert labels[-1]["el"] == "πολιτική"


def test_search_keeps_only_results_at_or_above_min_score():
    client = _client()
    with patch("backend.routes.rank_pool", return_value=_scored(0.91, 0.55, 0.54, 0.02)):
        body = client.post("/api/search", json={"query": "x"}).json()

    assert [r["score"] for r in body["results"]] == [0.91, 0.55]
    assert body["total"] == 2
    assert body["status"] == "grounded"


def test_search_returns_the_requested_page_of_the_ranked_pool():
    client = _client()
    scores = [round(0.99 - i * 0.01, 2) for i in range(25)]  # 25 results, all >= 0.55
    with patch("backend.routes.rank_pool", return_value=_scored(*scores)):
        body = client.post("/api/search", json={"query": "x", "page": 3, "page_size": 10}).json()

    assert body["total"] == 25
    assert (body["page"], body["page_size"]) == (3, 10)
    assert [r["celex_id"] for r in body["results"]] == [f"A{i}" for i in range(20, 25)]


def test_search_page_past_the_end_is_empty_but_keeps_the_total():
    client = _client()
    with patch("backend.routes.rank_pool", return_value=_scored(0.9, 0.8)):
        body = client.post("/api/search", json={"query": "x", "page": 2}).json()

    assert body["results"] == []
    assert body["total"] == 2
    assert body["status"] == "grounded"


def test_search_refuses_when_nothing_reaches_min_score():
    client = _client()
    with patch("backend.routes.rank_pool", return_value=_scored(0.31, 0.05)):
        body = client.post("/api/search", json={"query": "μουσακάς"}).json()

    assert body["results"] == []
    assert body["total"] == 0
    assert body["status"] == "refused"
    assert body["top_score"] == 0.31


def test_search_refuses_an_empty_pool():
    client = _client()
    with patch("backend.routes.rank_pool", return_value=[]):
        body = client.post("/api/search", json={"query": "x"}).json()

    assert body["status"] == "refused"
    assert body["top_score"] is None


def test_search_rejects_out_of_range_paging():
    client = _client()
    with patch("backend.routes.rank_pool", return_value=[]):
        for bad in ({"page": 0}, {"page_size": 0}, {"page_size": 51}):
            response = client.post("/api/search", json={"query": "x", **bad})
            assert response.status_code == 422, bad


def test_search_shows_each_document_once_with_its_best_passage():
    client = _client()
    scored = [
        (Chunk(text="a-best", celex_id="A1", labels=[]), 0.95),
        (Chunk(text="a-second", celex_id="A1", labels=[]), 0.90),
        (Chunk(text="b-only", celex_id="B2", labels=[]), 0.80),
        (Chunk(text="a-third", celex_id="A1", labels=[]), 0.60),
        (Chunk(text="b-junk", celex_id="B2", labels=[]), 0.30),  # below the bar: not a match
    ]
    with patch("backend.routes.rank_pool", return_value=scored):
        body = client.post("/api/search", json={"query": "x"}).json()

    assert [(r["celex_id"], r["text"], r["score"], r["matches"]) for r in body["results"]] == [
        ("A1", "a-best", 0.95, 3),
        ("B2", "b-only", 0.80, 1),
    ]
    assert body["total"] == 2  # documents, not passages


def test_search_pages_count_documents_not_passages():
    client = _client()
    # 12 documents, each matched by two passages
    scored = sorted(
        [(Chunk(text=f"{d}-{k}", celex_id=f"D{d:02}", labels=[]), 0.99 - d * 0.01 - k * 0.001)
         for d in range(12) for k in range(2)],
        key=lambda pair: pair[1],
        reverse=True,
    )
    with patch("backend.routes.rank_pool", return_value=scored):
        body = client.post("/api/search", json={"query": "x", "page": 2}).json()

    assert body["total"] == 12
    assert [r["celex_id"] for r in body["results"]] == ["D10", "D11"]

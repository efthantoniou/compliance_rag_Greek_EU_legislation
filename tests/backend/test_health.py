from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app


def _client() -> TestClient:
    # Not used as a context manager, so the lifespan (which would load a real
    # embedder) does not run; set the app-state singletons manually instead.
    app = create_app()
    app.state.config = object()
    app.state.embedder = object()
    return TestClient(app)


def test_health_reports_both_services_up():
    client = _client()
    with patch("backend.routes.check_surrealdb", return_value=True), \
         patch("backend.routes.check_llamacpp", return_value=True):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"surrealdb": True, "llamacpp": True}


def test_health_reports_llamacpp_down():
    client = _client()
    with patch("backend.routes.check_surrealdb", return_value=True), \
         patch("backend.routes.check_llamacpp", return_value=False):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"surrealdb": True, "llamacpp": False}


def test_health_result_is_cached_within_ttl():
    client = _client()
    with patch("backend.routes.check_surrealdb", return_value=True) as mock_db, \
         patch("backend.routes.check_llamacpp", return_value=True) as mock_llm:
        first = client.get("/api/health")
        second = client.get("/api/health")

    assert first.json() == second.json() == {"surrealdb": True, "llamacpp": True}
    # Second request within the TTL is served from cache, so the probes run once.
    assert mock_db.call_count == 1
    assert mock_llm.call_count == 1

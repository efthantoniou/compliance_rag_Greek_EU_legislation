import json
from unittest.mock import patch

import httpx
import pytest

from mcp_server import server


def _mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=server.BACKEND_URL,
        timeout=server._TIMEOUT,
        transport=httpx.MockTransport(handler),
    )


def _sse_body(*frames: tuple[str, dict]) -> bytes:
    return "".join(
        f"event: {event}\ndata: {json.dumps(data)}\n\n" for event, data in frames
    ).encode()


@pytest.mark.anyio
async def test_search_legislation_formats_results():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/search"
        assert json.loads(request.content) == {"query": "tax", "top_k": 5, "label": None}
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "celex_id": "A1",
                        "labels": [{"id": "1", "el": "φορολογία", "en": "taxation"}],
                        "subtopics": [],
                        "topics": [],
                        "text": "alpha",
                    }
                ]
            },
        )

    with patch("mcp_server.server._client", lambda: _mock_client(handler)):
        result = await server.search_legislation("tax")

    assert "celex_id=A1" in result
    assert "φορολογία" in result
    assert "alpha" in result


@pytest.mark.anyio
async def test_search_legislation_handles_no_results():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []})

    with patch("mcp_server.server._client", lambda: _mock_client(handler)):
        result = await server.search_legislation("nothing")

    assert result == "No relevant passages found."


@pytest.mark.anyio
async def test_ask_legislation_collects_token_frames():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/ask"
        assert json.loads(request.content) == {"question": "what?"}
        body = _sse_body(
            ("status", {"phase": "thinking"}),
            ("tool", {"query": "foo"}),
            ("token", {"text": "Hello "}),
            ("token", {"text": "world"}),
            ("done", {}),
        )
        return httpx.Response(200, content=body)

    with patch("mcp_server.server._client", lambda: _mock_client(handler)):
        result = await server.ask_legislation("what?")

    assert result == "Hello world"


@pytest.mark.anyio
async def test_ask_legislation_raises_on_error_frame():
    def handler(request: httpx.Request) -> httpx.Response:
        body = _sse_body(("error", {"message": "boom"}))
        return httpx.Response(200, content=body)

    with patch("mcp_server.server._client", lambda: _mock_client(handler)):
        with pytest.raises(RuntimeError, match="boom"):
            await server.ask_legislation("what?")


@pytest.mark.anyio
async def test_list_legislation_labels_formats_ids():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/labels"
        return httpx.Response(
            200,
            json={"labels": [{"id": "1", "el": "φορολογία", "en": "taxation"}]},
        )

    with patch("mcp_server.server._client", lambda: _mock_client(handler)):
        result = await server.list_legislation_labels()

    assert result == "1: φορολογία / taxation"


@pytest.mark.anyio
async def test_check_service_health_returns_json():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/health"
        return httpx.Response(200, json={"surrealdb": True, "llamacpp": False})

    with patch("mcp_server.server._client", lambda: _mock_client(handler)):
        result = await server.check_service_health()

    assert json.loads(result) == {"surrealdb": True, "llamacpp": False}


@pytest.fixture
def anyio_backend():
    return "asyncio"

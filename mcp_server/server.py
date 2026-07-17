"""MCP server exposing the Compliance RAG backend as tools.

A thin HTTP client of the already-running FastAPI backend (see
`backend/routes.py`) — no model or database loading happens in this process,
so it starts instantly and requires the backend (and its SurrealDB/llama.cpp
dependencies) to already be up. Point it at a non-default backend with the
`COMPLIANCE_RAG_BACKEND_URL` environment variable.

Run directly (stdio transport, for Claude Desktop / Claude Code):
    uv run python -m mcp_server.server
"""

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

BACKEND_URL = os.environ.get("COMPLIANCE_RAG_BACKEND_URL", "http://localhost:9000")

# `ask`/`check` stream an answer through a local LLM and can take a while,
# especially on first use (reranker model download/load); search/labels/health
# are quick but share the same client for simplicity.
_TIMEOUT = httpx.Timeout(10.0, read=180.0)

mcp = FastMCP("compliance-rag")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BACKEND_URL, timeout=_TIMEOUT)


async def _get(path: str, params: dict | None = None) -> dict:
    async with _client() as client:
        resp = await client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()


async def _post(path: str, payload: dict) -> dict:
    async with _client() as client:
        resp = await client.post(path, json=payload)
        resp.raise_for_status()
        return resp.json()


async def _stream_answer(path: str, payload: dict) -> str:
    """POST to an SSE endpoint (`/api/ask` or `/api/check`) and collect the
    streamed `token` frames into one string, raising on an `error` frame."""
    parts: list[str] = []
    error: str | None = None
    event_type = "message"
    data_lines: list[str] = []

    def flush() -> None:
        nonlocal event_type, data_lines, error
        if not data_lines:
            return
        data = json.loads("\n".join(data_lines))
        if event_type == "token":
            parts.append(data["text"])
        elif event_type == "error":
            error = data["message"]
        event_type, data_lines = "message", []

    async with _client() as client:
        async with client.stream("POST", path, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line == "":
                    flush()
                elif line.startswith("event:"):
                    event_type = line[len("event:") :].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[len("data:") :].strip())
            flush()

    if error:
        raise RuntimeError(f"Backend error: {error}")
    return "".join(parts)


@mcp.tool()
async def search_legislation(query: str, top_k: int = 5, label: str | None = None) -> str:
    """Hybrid (vector + BM25 + cross-encoder rerank) search over the Greek/EU
    legislation corpus. No LLM is involved — fast, raw retrieval for inspecting
    what the index returns. Returns the top passages with their CELEX ids and
    EUROVOC domain labels.

    Args:
        query: Search query. Greek queries work best since the corpus is Greek
            EU-legislation text, but the embedding model is multilingual.
        top_k: Number of passages to return.
        label: Optional EUROVOC level_1 domain id to restrict results to (see
            `list_legislation_labels`).
    """
    data = await _post("/api/search", {"query": query, "top_k": top_k, "label": label})
    results = data["results"]
    if not results:
        return "No relevant passages found."
    blocks = []
    for i, r in enumerate(results, start=1):
        domains = ", ".join(c["el"] for c in r["labels"]) or "none"
        blocks.append(f"[{i}] celex_id={r['celex_id']} domains=[{domains}]\n{r['text']}")
    return "\n\n".join(blocks)


@mcp.tool()
async def ask_legislation(question: str) -> str:
    """Ask a natural-language question about Greek/EU legislation. A
    search-and-answer agent retrieves relevant passages and writes an answer
    with `[celex_id]` citations. If nothing relevant is found, it says so
    rather than guessing. Single-turn (no conversation memory). Runs a local
    LLM, so it is much slower than `search_legislation`.

    Args:
        question: The question, e.g. in Greek or English.
    """
    return await _stream_answer("/api/ask", {"question": question})


@mcp.tool()
async def check_document(document: str) -> str:
    """Paste a policy document's text; an agent extracts its topics and
    surfaces the closest-matching Greek/EU regulation(s) for each. It only
    surfaces relevant law — it never declares the document compliant or
    non-compliant. Runs a local LLM, so it is much slower than
    `search_legislation`.

    Args:
        document: The full text of the policy document to check.
    """
    return await _stream_answer("/api/check", {"document": document})


@mcp.tool()
async def list_legislation_labels() -> str:
    """List the 21 EUROVOC level_1 domains (broad legal subject areas) that
    can be passed as the `label` filter to `search_legislation`."""
    data = await _get("/api/labels")
    return "\n".join(f"{c['id']}: {c['el']} / {c['en']}" for c in data["labels"])


@mcp.tool()
async def check_service_health() -> str:
    """Check whether the Compliance RAG backend's dependencies (SurrealDB and
    the local llama.cpp server) are reachable."""
    data = await _get("/api/health")
    return json.dumps(data)


if __name__ == "__main__":
    mcp.run()

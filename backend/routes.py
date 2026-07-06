import asyncio
import time
import urllib.error
import urllib.request

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from backend.deps import repo_root_on_path

repo_root_on_path()

from agent import AgentDeps  # noqa: E402
from agent.retrieval import search  # noqa: E402
from config import Config  # noqa: E402  (import after path bootstrap)
from agent.storage.surreal import _connect  # noqa: E402

from backend.schemas import (  # noqa: E402
    AskRequest,
    CheckRequest,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from backend.streaming import agent_sse_events  # noqa: E402

router = APIRouter(prefix="/api")


def check_llamacpp(config: Config) -> bool:
    try:
        urllib.request.urlopen(f"{config.llamacpp_url}/models", timeout=3)
        return True
    except (urllib.error.URLError, OSError):
        return False


def check_surrealdb(config: Config) -> bool:
    try:
        db = _connect(config)
        db.close()
        return True
    except Exception:
        return False


_HEALTH_TTL_SECONDS = 5.0


@router.get("/health")
async def health(request: Request) -> dict:
    # Cache the result per app for a few seconds so rapid polls (or several
    # browser tabs) don't repeatedly probe SurrealDB and llama.cpp.
    cache = getattr(request.app.state, "health_cache", None)
    now = time.monotonic()
    if cache is not None and now - cache["ts"] < _HEALTH_TTL_SECONDS:
        return cache["value"]

    config = request.app.state.config
    surrealdb_ok, llamacpp_ok = await asyncio.gather(
        run_in_threadpool(check_surrealdb, config),
        run_in_threadpool(check_llamacpp, config),
    )
    value = {"surrealdb": surrealdb_ok, "llamacpp": llamacpp_ok}
    request.app.state.health_cache = {"ts": now, "value": value}
    return value


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(payload: SearchRequest, request: Request) -> SearchResponse:
    config = request.app.state.config
    embedder = request.app.state.embedder
    chunks = await run_in_threadpool(
        search,
        config,
        embedder,
        payload.query,
        top_k=payload.top_k,
        label_filter=payload.label,
    )
    return SearchResponse(
        results=[
            SearchResult(celex_id=c.celex_id, labels=c.labels, text=c.text)
            for c in chunks
        ]
    )


def _sse_response(agent, prompt, deps) -> StreamingResponse:
    return StreamingResponse(
        agent_sse_events(agent, prompt, deps),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Disable proxy buffering (nginx and Next's dev proxy) so tokens
            # flush to the client as they stream instead of in one batch.
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ask")
async def ask_endpoint(payload: AskRequest, request: Request) -> StreamingResponse:
    config = request.app.state.config
    embedder = request.app.state.embedder
    agent = request.app.state.ask_agent
    deps = AgentDeps(config=config, embedder=embedder)
    return _sse_response(agent, payload.question, deps)


@router.post("/check")
async def check_endpoint(payload: CheckRequest, request: Request) -> StreamingResponse:
    config = request.app.state.config
    embedder = request.app.state.embedder
    agent = request.app.state.check_agent
    deps = AgentDeps(config=config, embedder=embedder)
    return _sse_response(agent, payload.document, deps)

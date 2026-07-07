# Krikri Prompted-Output Tool Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a config-selected second agent path that supports Krikri-8B by driving tool-calling through pydantic-ai `PromptedOutput` (client-side parsing) instead of llama.cpp's server-side native tool parser.

**Architecture:** A `tool_mode` config flag selects between the existing native function-tool path (Qwen, untouched) and a new "prompted" path. The prompted path is a two-phase loop: Phase 1 a planner agent (`output_type=PromptedOutput([SearchAction, Done])`) that we run in a loop, executing `search_regulations` ourselves on each `SearchAction`; Phase 2 a plain writer agent that streams the final answer token-by-token. The same SSE frames (`status`/`tool`/`token`/`done`/`error`) are emitted, so routes/schemas/frontend are unchanged.

**Tech Stack:** Python 3.11, pydantic-ai (>=2.2.0), pydantic, FastAPI (SSE), click, pytest.

## Global Constraints

- **No-auto-git (standing user rule):** do NOT run `git add`/`commit`/`push` without the user's explicit approval. The "Checkpoint" steps below mark logical commit points — pause and ask before committing; the shown `git` command is what to run *once approved*.
- **Native path is frozen:** `build_ask_agent`/`build_check_agent` native behavior and the existing `agent_sse_events` must remain unchanged; existing tests in `tests/test_agent.py` must stay green.
- **Default `TOOL_MODE=native`** — the prompted path is opt-in; Qwen deployments behave exactly as today.
- **No DB/schema/frontend changes, no re-ingest.**
- Unit tests must run without a live model or SurrealDB (inject/momck agents and the search function).
- Run tests with `uv run pytest` (integration deselected by default).

---

### Task 1: Config flags `tool_mode` and `max_search_iters`

**Files:**
- Modify: `config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Config.tool_mode: Literal["native","prompted"]` (default `"native"`), `Config.max_search_iters: int` (default `5`); env overrides `TOOL_MODE`, `MAX_SEARCH_ITERS`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py  (add these tests)
import os
from config import load_config


def test_tool_mode_defaults_to_native(monkeypatch):
    monkeypatch.setenv("LLAMACPP_MODEL", "test-model")
    monkeypatch.delenv("TOOL_MODE", raising=False)
    cfg = load_config()
    assert cfg.tool_mode == "native"
    assert cfg.max_search_iters == 5


def test_tool_mode_and_iters_from_env(monkeypatch):
    monkeypatch.setenv("LLAMACPP_MODEL", "test-model")
    monkeypatch.setenv("TOOL_MODE", "prompted")
    monkeypatch.setenv("MAX_SEARCH_ITERS", "8")
    cfg = load_config()
    assert cfg.tool_mode == "prompted"
    assert cfg.max_search_iters == 8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -k tool_mode -v`
Expected: FAIL (`Config` has no attribute `tool_mode`).

- [ ] **Step 3: Implement**

In `config.py`, add to the imports and the `Config` dataclass + `load_config`:

```python
from typing import Literal
```

Add fields to `Config` (after `reranker_device`):

```python
    tool_mode: Literal["native", "prompted"] = "native"
    max_search_iters: int = 5
```

Add to the `Config(...)` construction in `load_config`:

```python
        tool_mode=os.environ.get("TOOL_MODE", "native"),  # type: ignore[arg-type]
        max_search_iters=int(os.environ.get("MAX_SEARCH_ITERS", "5")),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (all config tests).

- [ ] **Step 5: Checkpoint** (commit once user approves)

```bash
git add config.py tests/test_config.py
git commit -m "feat(config): add tool_mode and max_search_iters"
```

---

### Task 2: Action schemas `SearchAction` and `Done`

**Files:**
- Create: `agent/core/actions.py`
- Test: `tests/test_prompted_loop.py`

**Interfaces:**
- Produces: `SearchAction(query: str, top_k: int = 5)`, `Done()` — pydantic `BaseModel`s used as the planner's `PromptedOutput` union.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompted_loop.py  (new file)
from agent.core.actions import SearchAction, Done


def test_search_action_defaults():
    a = SearchAction(query="φορολογία")
    assert a.query == "φορολογία"
    assert a.top_k == 5


def test_done_is_constructable():
    assert Done() is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_prompted_loop.py -v`
Expected: FAIL (module `agent.core.actions` not found).

- [ ] **Step 3: Implement**

```python
# agent/core/actions.py
"""Discriminated-union actions for the prompted-output tool loop.

The planner agent returns exactly one of these per turn: a SearchAction to
retrieve more passages, or Done when it has enough context to answer.
"""

from pydantic import BaseModel, Field


class SearchAction(BaseModel):
    """Retrieve passages from the legislation corpus for `query`."""

    query: str = Field(description="A search query, in Greek, for the legislation corpus.")
    top_k: int = 5


class Done(BaseModel):
    """Signals that enough context has been gathered to write the answer."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_prompted_loop.py -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** (commit once user approves)

```bash
git add agent/core/actions.py tests/test_prompted_loop.py
git commit -m "feat(agent): add SearchAction/Done schemas for prompted loop"
```

---

### Task 3: Prompt variants for planner and writer

**Files:**
- Modify: `agent/core/prompts.py`
- Test: `tests/test_prompted_loop.py`

**Interfaces:**
- Produces: string constants `PLANNER_ASK`, `PLANNER_CHECK`, `WRITER_ASK`, `WRITER_CHECK`. Existing `ASK_INSTRUCTIONS`/`CHECK_INSTRUCTIONS` remain untouched (native path uses them).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompted_loop.py  (add)
from agent.core import prompts


def test_prompt_variants_exist_and_mention_protocol():
    assert "SearchAction" in prompts.PLANNER_ASK
    assert "Done" in prompts.PLANNER_ASK
    assert "SearchAction" in prompts.PLANNER_CHECK
    # writer prompts keep the citation / no-compliance guidance
    assert "celex_id" in prompts.WRITER_ASK
    assert "compliant" in prompts.WRITER_CHECK
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_prompted_loop.py -k prompt_variants -v`
Expected: FAIL (`AttributeError: PLANNER_ASK`).

- [ ] **Step 3: Implement**

Append to `agent/core/prompts.py`:

```python
PLANNER_ASK = (
    "You are a legal research assistant planning how to answer a question about "
    "Greek and EU legislation. Each turn, return ONE action: a SearchAction with a "
    "Greek search query when you need more passages, or Done when the passages "
    "gathered so far are enough to answer. Do NOT write the answer yet — only plan "
    "searches. Prefer one focused SearchAction at a time."
)

PLANNER_CHECK = (
    "You are a compliance research assistant planning how to analyse a policy "
    "document against Greek and EU legislation. Identify the document's key topics "
    "and obligations. Each turn, return ONE action: a SearchAction (one per topic, "
    "with a Greek query) when a topic still needs matching law, or Done when every "
    "topic has been searched. Do NOT write the report yet — only plan searches."
)

WRITER_ASK = (
    "You are a legal research assistant answering a question about Greek and EU "
    "legislation using only the retrieved passages provided in the prompt. Cite the "
    "celex_id of every document you rely on. If the passages contain nothing "
    "relevant, say so explicitly instead of guessing."
)

WRITER_CHECK = (
    "You are a compliance research assistant. Using only the retrieved passages "
    "provided in the prompt, produce a report listing the closest matching "
    "regulation(s) for each topic in the document, or an explicit 'no relevant "
    "regulation found' note. Cite celex_ids. This report surfaces relevant law "
    "only — never state that the document is or is not compliant."
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_prompted_loop.py -k prompt_variants -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** (commit once user approves)

```bash
git add agent/core/prompts.py tests/test_prompted_loop.py
git commit -m "feat(agent): add planner/writer prompt variants"
```

---

### Task 4: Factory builders for planner and writer agents

**Files:**
- Modify: `agent/core/factory.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: `SearchAction`, `Done` (Task 2); `Config`.
- Produces: `build_planner_agent(config: Config, instructions: str) -> Agent` (with `output_type=PromptedOutput([SearchAction, Done])`, no tools, no `deps_type`); `build_writer_agent(config: Config, instructions: str) -> Agent` (plain text, no tools). Existing `build_ask_agent`/`build_check_agent` unchanged in behavior (refactored to share `_build_model`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent.py  (add)
from types import SimpleNamespace

from agent.core.factory import build_planner_agent, build_writer_agent


def _cfg():
    return SimpleNamespace(
        llamacpp_model="m", llamacpp_url="http://x/v1",
    )


def test_build_planner_and_writer_agents():
    planner = build_planner_agent(_cfg(), "plan instructions")
    writer = build_writer_agent(_cfg(), "write instructions")
    # both are pydantic-ai Agents; construction must not raise
    assert planner is not None
    assert writer is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agent.py -k planner_and_writer -v`
Expected: FAIL (`ImportError: build_planner_agent`).

- [ ] **Step 3: Implement**

Rewrite `agent/core/factory.py` to add a shared `_build_model` and the two new builders (keep the existing public functions and their behavior):

```python
import logfire
from pydantic_ai import Agent, PromptedOutput
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from agent.core.actions import Done, SearchAction
from agent.core.deps import AgentDeps, _search_regulations_tool
from agent.core.prompts import ASK_INSTRUCTIONS, CHECK_INSTRUCTIONS
from config import Config

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()


def _build_model(config: Config) -> OpenAIChatModel:
    return OpenAIChatModel(
        config.llamacpp_model,
        provider=OpenAIProvider(base_url=config.llamacpp_url, api_key="not-needed"),
    )


def _build_agent(config: Config, instructions: str) -> Agent:
    agent = Agent(_build_model(config), deps_type=AgentDeps, instructions=instructions)
    agent.tool(_search_regulations_tool)
    return agent


def build_ask_agent(config: Config) -> Agent:
    return _build_agent(config, ASK_INSTRUCTIONS)


def build_check_agent(config: Config) -> Agent:
    return _build_agent(config, CHECK_INSTRUCTIONS)


def build_planner_agent(config: Config, instructions: str) -> Agent:
    """Prompted-path planner: returns a SearchAction or Done per turn, no tools."""
    return Agent(
        _build_model(config),
        output_type=PromptedOutput([SearchAction, Done]),
        instructions=instructions,
    )


def build_writer_agent(config: Config, instructions: str) -> Agent:
    """Prompted-path writer: plain streamed text answer, no tools."""
    return Agent(_build_model(config), instructions=instructions)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_agent.py -v`
Expected: PASS (new test + existing native-agent tests).

- [ ] **Step 5: Checkpoint** (commit once user approves)

```bash
git add agent/core/factory.py tests/test_agent.py
git commit -m "feat(agent): add planner/writer builders, share _build_model"
```

---

### Task 5: The prompted loop core (`run_prompted`)

**Files:**
- Create: `agent/core/loop.py`
- Test: `tests/test_prompted_loop.py`

**Interfaces:**
- Consumes: `SearchAction`, `Done` (Task 2). Takes injected `planner`, `writer` (duck-typed pydantic-ai Agents) and a `search_fn(query: str, top_k: int) -> list` so it is testable without a model or DB.
- Produces:
  - `ToolCall(query: str)` and `Token(text: str)` dataclasses.
  - `format_writer_prompt(user_prompt: str, chunks: list) -> str`
  - `async def run_prompted(planner, writer, search_fn, user_prompt: str, max_search_iters: int) -> AsyncIterator[ToolCall | Token]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompted_loop.py  (add)
import pytest

from agent.core.actions import SearchAction, Done
from agent.core.loop import ToolCall, Token, run_prompted, format_writer_prompt


class _Chunk:
    def __init__(self, celex_id, text):
        self.celex_id = celex_id
        self.text = text


class _Result:
    def __init__(self, output):
        self.output = output

    def all_messages(self):
        return []


class _FakePlanner:
    """Returns queued outputs; records the prompts it was called with."""

    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.prompts = []

    async def run(self, prompt, message_history=None):
        self.prompts.append(prompt)
        return _Result(self._outputs.pop(0))


class _FakeStream:
    def __init__(self, tokens):
        self._tokens = tokens

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def stream_text(self, delta=True):
        for t in self._tokens:
            yield t


class _FakeWriter:
    def __init__(self, tokens):
        self._tokens = tokens
        self.prompt = None

    def run_stream(self, prompt, message_history=None):
        self.prompt = prompt
        return _FakeStream(self._tokens)


async def _drain(agen):
    return [ev async for ev in agen]


@pytest.mark.anyio
async def test_loop_searches_then_streams():
    planner = _FakePlanner([SearchAction(query="q1", top_k=3), Done()])
    writer = _FakeWriter(["Hel", "lo"])
    searched = []

    def search_fn(q, k):
        searched.append((q, k))
        return [_Chunk("CELEX1", "text one")]

    events = await _drain(
        run_prompted(planner, writer, search_fn, "user question", max_search_iters=5)
    )
    assert searched == [("q1", 3)]
    assert ToolCall(query="q1") in events
    assert [e.text for e in events if isinstance(e, Token)] == ["Hel", "lo"]
    # writer prompt carried the retrieved passage
    assert "CELEX1" in writer.prompt


@pytest.mark.anyio
async def test_loop_respects_max_iters():
    # planner always wants to search; cap must stop it and still stream
    planner = _FakePlanner([SearchAction(query=f"q{i}") for i in range(10)])
    writer = _FakeWriter(["done"])

    def search_fn(q, k):
        return []

    events = await _drain(
        run_prompted(planner, writer, search_fn, "u", max_search_iters=2)
    )
    tool_calls = [e for e in events if isinstance(e, ToolCall)]
    assert len(tool_calls) == 2  # capped
    assert [e.text for e in events if isinstance(e, Token)] == ["done"]


@pytest.mark.anyio
async def test_loop_zero_search_answers_directly():
    planner = _FakePlanner([Done()])
    writer = _FakeWriter(["ans"])
    events = await _drain(
        run_prompted(planner, writer, lambda q, k: [], "u", max_search_iters=5)
    )
    assert not [e for e in events if isinstance(e, ToolCall)]
    assert [e.text for e in events if isinstance(e, Token)] == ["ans"]


def test_format_writer_prompt_with_and_without_chunks():
    with_chunks = format_writer_prompt("Q", [_Chunk("CX", "body")])
    assert "Q" in with_chunks and "CX" in with_chunks and "body" in with_chunks
    empty = format_writer_prompt("Q", [])
    assert "Q" in empty
```

Note: `@pytest.mark.anyio` — the repo already depends on `anyio` (dev group). If the anyio fixture backend is not configured, add at the top of the test file:

```python
import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_prompted_loop.py -k loop -v`
Expected: FAIL (module `agent.core.loop` not found).

- [ ] **Step 3: Implement**

```python
# agent/core/loop.py
"""Prompted-output tool loop: the model path for models (e.g. Krikri) whose
tool-call output llama.cpp's native parser rejects.

Phase 1 (planner): a PromptedOutput agent returns a SearchAction or Done per
turn; we run search ourselves and feed results back. Phase 2 (writer): a plain
agent streams the final answer token-by-token. Pure and injectable — no model
or DB is imported here, so it is unit-testable with fakes.
"""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from agent.core.actions import Done, SearchAction


@dataclass
class ToolCall:
    query: str


@dataclass
class Token:
    text: str


def _planner_feedback(query: str, chunks: list) -> str:
    if not chunks:
        return f"Search for '{query}' returned no results."
    lines = "\n".join(f"[{c.celex_id}] {c.text[:200]}" for c in chunks)
    return f"Results for '{query}':\n{lines}\n\nDecide the next action."


def format_writer_prompt(user_prompt: str, chunks: list) -> str:
    if chunks:
        context = "\n\n".join(f"[{c.celex_id}] {c.text}" for c in chunks)
    else:
        context = "(no relevant passages were retrieved)"
    return f"Question/Document:\n{user_prompt}\n\nRetrieved passages:\n{context}"


async def run_prompted(
    planner,
    writer,
    search_fn: Callable[[str, int], list],
    user_prompt: str,
    max_search_iters: int,
) -> AsyncIterator[ToolCall | Token]:
    history: list = []
    collected: list = []
    next_input = user_prompt

    for _ in range(max_search_iters):
        result = await planner.run(next_input, message_history=history)
        history = result.all_messages()
        action = result.output
        if isinstance(action, Done):
            break
        # SearchAction
        yield ToolCall(query=action.query)
        chunks = search_fn(action.query, action.top_k)
        collected.extend(chunks)
        next_input = _planner_feedback(action.query, chunks)

    writer_prompt = format_writer_prompt(user_prompt, collected)
    async with writer.run_stream(writer_prompt) as stream:
        async for delta in stream.stream_text(delta=True):
            yield Token(text=delta)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_prompted_loop.py -v`
Expected: PASS (all loop tests).

- [ ] **Step 5: Checkpoint** (commit once user approves)

```bash
git add agent/core/loop.py tests/test_prompted_loop.py
git commit -m "feat(agent): implement prompted-output tool loop core"
```

---

### Task 6: Prompted runner wrapper (`prompted_events`)

**Files:**
- Modify: `agent/core/loop.py`
- Test: `tests/test_prompted_loop.py`

**Interfaces:**
- Consumes: `build_planner_agent`/`build_writer_agent` (Task 4); `PLANNER_ASK/PLANNER_CHECK/WRITER_ASK/WRITER_CHECK` (Task 3); `search_regulations` (existing in `agent/core/deps.py`); `Config`, `AgentDeps`.
- Produces: `async def prompted_events(config: Config, deps: AgentDeps, user_prompt: str, kind: Literal["ask","check"]) -> AsyncIterator[ToolCall | Token]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompted_loop.py  (add)
import agent.core.loop as loop_mod
from types import SimpleNamespace


@pytest.mark.anyio
async def test_prompted_events_wires_agents_and_search(monkeypatch):
    calls = {}

    def fake_planner(config, instructions):
        calls["planner_instructions"] = instructions
        return _FakePlanner([Done()])

    def fake_writer(config, instructions):
        calls["writer_instructions"] = instructions
        return _FakeWriter(["ok"])

    monkeypatch.setattr(loop_mod, "build_planner_agent", fake_planner)
    monkeypatch.setattr(loop_mod, "build_writer_agent", fake_writer)
    monkeypatch.setattr(loop_mod, "search_regulations", lambda deps, q, k: [])

    config = SimpleNamespace(max_search_iters=5)
    events = [
        ev
        async for ev in loop_mod.prompted_events(config, deps=object(), user_prompt="u", kind="ask")
    ]
    assert [e.text for e in events if isinstance(e, Token)] == ["ok"]
    assert "SearchAction" in calls["planner_instructions"]  # PLANNER_ASK selected
    assert "celex_id" in calls["writer_instructions"]       # WRITER_ASK selected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_prompted_loop.py -k prompted_events -v`
Expected: FAIL (`prompted_events` not defined).

- [ ] **Step 3: Implement**

Add imports at the top of `agent/core/loop.py` (below the existing imports):

```python
from typing import Literal

from agent.core.deps import search_regulations
from agent.core.factory import build_planner_agent, build_writer_agent
from agent.core.prompts import (
    PLANNER_ASK,
    PLANNER_CHECK,
    WRITER_ASK,
    WRITER_CHECK,
)
```

Append to `agent/core/loop.py`:

```python
_PLANNER = {"ask": PLANNER_ASK, "check": PLANNER_CHECK}
_WRITER = {"ask": WRITER_ASK, "check": WRITER_CHECK}


async def prompted_events(
    config,
    deps,
    user_prompt: str,
    kind: Literal["ask", "check"],
) -> AsyncIterator[ToolCall | Token]:
    planner = build_planner_agent(config, _PLANNER[kind])
    writer = build_writer_agent(config, _WRITER[kind])

    def search_fn(query: str, top_k: int) -> list:
        return search_regulations(deps, query, top_k)

    async for event in run_prompted(
        planner, writer, search_fn, user_prompt, config.max_search_iters
    ):
        yield event
```

Note: `search_regulations`, `build_planner_agent`, `build_writer_agent` are referenced as module globals so the test's `monkeypatch.setattr(loop_mod, ...)` works. Do not import them into other modules and call them there.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_prompted_loop.py -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** (commit once user approves)

```bash
git add agent/core/loop.py tests/test_prompted_loop.py
git commit -m "feat(agent): add prompted_events runner wiring agents+search"
```

---

### Task 7: Backend SSE for the prompted path + dispatch + error sanitizing

**Files:**
- Modify: `backend/streaming.py`
- Modify: `backend/routes.py`
- Test: `tests/test_prompted_loop.py`

**Interfaces:**
- Consumes: `prompted_events` (Task 6); `Config`, `AgentDeps`; existing `format_sse`, `agent_sse_events`.
- Produces: `async def prompted_sse_events(config, deps, prompt, kind) -> AsyncIterator[str]`; routes select the generator by `config.tool_mode`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompted_loop.py  (add)
import backend.streaming as streaming_mod


@pytest.mark.anyio
async def test_prompted_sse_frames(monkeypatch):
    async def fake_events(config, deps, user_prompt, kind):
        from agent.core.loop import ToolCall, Token
        yield ToolCall(query="q")
        yield Token(text="A")

    monkeypatch.setattr(streaming_mod, "prompted_events", fake_events)

    frames = [
        f
        async for f in streaming_mod.prompted_sse_events(
            config=object(), deps=object(), prompt="u", kind="ask"
        )
    ]
    joined = "".join(frames)
    assert "event: status" in joined
    assert 'event: tool' in joined and '"query": "q"' in joined
    assert 'event: token' in joined and '"text": "A"' in joined
    assert "event: done" in joined


@pytest.mark.anyio
async def test_prompted_sse_sanitizes_errors(monkeypatch):
    async def boom(config, deps, user_prompt, kind):
        raise RuntimeError("secret internals")
        yield  # pragma: no cover

    monkeypatch.setattr(streaming_mod, "prompted_events", boom)
    frames = [
        f
        async for f in streaming_mod.prompted_sse_events(
            config=object(), deps=object(), prompt="u", kind="ask"
        )
    ]
    joined = "".join(frames)
    assert "event: error" in joined
    assert "secret internals" not in joined
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_prompted_loop.py -k prompted_sse -v`
Expected: FAIL (`prompted_sse_events` not defined).

- [ ] **Step 3: Implement**

Add to `backend/streaming.py` (new imports + function). Keep the existing `agent_sse_events` unchanged.

```python
import logging

from agent.core.loop import ToolCall, Token, prompted_events

logger = logging.getLogger(__name__)

_GENERIC_ERROR = "Something went wrong while generating the answer. Please try again."


async def prompted_sse_events(config, deps, prompt, kind) -> AsyncIterator[str]:
    yield format_sse("status", {"phase": "thinking"})
    try:
        async for event in prompted_events(config, deps, prompt, kind):
            if isinstance(event, ToolCall):
                yield format_sse("tool", {"query": event.query})
            elif isinstance(event, Token):
                yield format_sse("token", {"text": event.text})
        yield format_sse("done", {})
    except Exception:
        logger.exception("prompted_sse_events failed")
        yield format_sse("error", {"message": _GENERIC_ERROR})
```

Then update `backend/routes.py` to dispatch by `tool_mode`. Replace `_sse_response` and its call sites:

```python
from backend.streaming import agent_sse_events, prompted_sse_events  # noqa: E402


def _sse_response(config, deps, prompt, kind, native_agent) -> StreamingResponse:
    if config.tool_mode == "prompted":
        generator = prompted_sse_events(config, deps, prompt, kind)
    else:
        generator = agent_sse_events(native_agent, prompt, deps)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

Update the two endpoints to pass the new args:

```python
@router.post("/ask")
async def ask_endpoint(payload: AskRequest, request: Request) -> StreamingResponse:
    config = request.app.state.config
    embedder = request.app.state.embedder
    deps = AgentDeps(config=config, embedder=embedder)
    return _sse_response(config, deps, payload.question, "ask", request.app.state.ask_agent)


@router.post("/check")
async def check_endpoint(payload: CheckRequest, request: Request) -> StreamingResponse:
    config = request.app.state.config
    embedder = request.app.state.embedder
    deps = AgentDeps(config=config, embedder=embedder)
    return _sse_response(config, deps, payload.document, "check", request.app.state.check_agent)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_prompted_loop.py -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** (commit once user approves)

```bash
git add backend/streaming.py backend/routes.py tests/test_prompted_loop.py
git commit -m "feat(backend): prompted SSE path + tool_mode dispatch + error sanitizing"
```

---

### Task 8: CLI dispatch for `ask` and `check`

**Files:**
- Modify: `main.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `prompted_events` (Task 6); `Config.tool_mode`.
- Produces: `_collect_prompted_answer(config, deps, prompt, kind) -> str` (module-level in `main.py`); `ask`/`check` dispatch native vs prompted.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py  (add)
import asyncio
import main as main_mod


def test_collect_prompted_answer(monkeypatch):
    async def fake_events(config, deps, user_prompt, kind):
        from agent.core.loop import ToolCall, Token
        yield ToolCall(query="q")
        yield Token(text="Hel")
        yield Token(text="lo")

    monkeypatch.setattr(main_mod, "prompted_events", fake_events)
    answer = asyncio.run(
        main_mod._collect_prompted_answer(config=object(), deps=object(), prompt="u", kind="ask")
    )
    assert answer == "Hello"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -k collect_prompted -v`
Expected: FAIL (`_collect_prompted_answer` not defined).

- [ ] **Step 3: Implement**

In `main.py`, add imports near the top:

```python
import asyncio

from agent.core.loop import Token, prompted_events
```

Add the helper (module level):

```python
async def _collect_prompted_answer(config, deps, prompt, kind) -> str:
    parts: list[str] = []
    async for event in prompted_events(config, deps, prompt, kind):
        if isinstance(event, Token):
            parts.append(event.text)
    return "".join(parts)
```

Update `ask` command body (replace the `agent.run_sync` block):

```python
    deps = AgentDeps(config=config, embedder=embedder)
    if config.tool_mode == "prompted":
        answer = asyncio.run(_collect_prompted_answer(config, deps, question, "ask"))
        click.echo(answer)
    else:
        agent = build_ask_agent(config)
        result = agent.run_sync(question, deps=deps)
        click.echo(result.output)
```

Update `check` command body similarly (replace its `agent.run_sync` block):

```python
    deps = AgentDeps(config=config, embedder=embedder)
    if config.tool_mode == "prompted":
        answer = asyncio.run(_collect_prompted_answer(config, deps, document_text, "check"))
        click.echo(answer)
    else:
        agent = build_check_agent(config)
        result = agent.run_sync(document_text, deps=deps)
        click.echo(result.output)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** (commit once user approves)

```bash
git add main.py tests/test_cli.py
git commit -m "feat(cli): dispatch ask/check between native and prompted paths"
```

---

### Task 9: Full suite, ops config, and live verification

**Files:**
- Modify: `.env.docker` (ops, not code)
- Modify: `docs_internal/ideas.md` (mark the chosen path as implemented)

- [ ] **Step 1: Run the full unit suite**

Run: `uv run pytest -q`
Expected: PASS, no regressions (native `tests/test_agent.py` green).

- [ ] **Step 2: Enable the prompted path for Krikri**

In `.env.docker` set:

```
TOOL_MODE=prompted
```

(Confirm `LLAMACPP_MODEL_FILE=llama-krikri-8b-instruct-q8_0.gguf` is already set.)

- [ ] **Step 3: Restart backend and llama, verify health**

```bash
docker compose --env-file .env.docker up -d llama backend
curl -s localhost:9000/api/health   # {"surrealdb": true, "llamacpp": true}
```

- [ ] **Step 4: Live smoke test — CLI ask (Greek)**

```bash
docker compose --env-file .env.docker exec -T backend \
  python main.py ask "Ποιες είναι οι βασικές υποχρεώσεις σχετικά με την προστασία δεδομένων;"
```
Expected: a Greek answer with `[celex_id]` citations, **no** `peg-native` 500.

- [ ] **Step 5: Live smoke test — SSE ask endpoint**

```bash
curl -N -s -X POST localhost:9000/api/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Ποιες είναι οι υποχρεώσεις;"}'
```
Expected: `event: status` → one or more `event: tool` → streamed `event: token` frames → `event: done`.

- [ ] **Step 6: Update ideas.md status**

In `docs_internal/ideas.md`, under "Chosen: Approach A", change the trailing "(Design spec in ...)" note to record that it is implemented and behind `TOOL_MODE=prompted`, and remove the "not usable" caveat wording in the model-swap assessment now that the path exists.

- [ ] **Step 7: Checkpoint** (commit once user approves)

```bash
git add .env.docker docs_internal/ideas.md
git commit -m "chore: enable prompted path for Krikri; mark Approach A implemented"
```

---

## Self-Review

**Spec coverage:**
- §1 config switch → Task 1 (flags) + Task 7 (routes dispatch) + Task 8 (CLI dispatch). ✓
- §2 two-phase loop + `SearchAction`/`Done` → Task 2 (schemas) + Task 5 (loop) + Task 6 (wiring). ✓
- §prompts planner+writer variants → Task 3. ✓
- §3 SSE frames unchanged, routes/CLI integration → Task 7 + Task 8. ✓
- §4 error handling & bounds (`max_search_iters`, sanitized errors, zero-search) → Task 1 (iters), Task 5 (cap + zero-search tests), Task 7 (sanitized errors). ✓
- §5 testing (mock planner scripted, cap, zero-search, frame sequence, native green) → Tasks 5/6/7/8 tests + Task 9 full suite. ✓
- Files-touched table → every listed file has a task (`deps.py` reused unchanged, as the spec predicted). ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code; every command shows expected output. ✓

**Type consistency:** `SearchAction(query, top_k=5)`/`Done()` used identically in Tasks 2/4/5/6. `ToolCall(query)`/`Token(text)` defined in Task 5 and consumed unchanged in Tasks 6/7/8. `run_prompted(planner, writer, search_fn, user_prompt, max_search_iters)` and `prompted_events(config, deps, user_prompt, kind)` signatures match across tasks. `prompted_sse_events(config, deps, prompt, kind)` matches its route call site. ✓

**Risk note (carry into execution):** `PromptedOutput` reliability on an 8B is the open risk (spec "Follow-ups"). If Task 9 live tests show the planner emitting malformed actions or never returning `Done`, that is a prompt-tuning/eval issue, not a plan defect — capture it as an eval follow-up rather than reworking the loop.

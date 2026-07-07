# Design: Prompted-Output tool loop for Krikri (config-switched dual path)

**Date:** 2026-07-07
**Status:** Approved design, pending spec review
**Scope:** `config.py`, `agent/core/{factory,deps,prompts,actions,loop}.py`, `backend/streaming.py`, `main.py`. No schema/DB/frontend changes. No re-ingest.

## Problem

Krikri-8B (the Greek-specialized model we want) generates excellent Greek and
correctly decides to call the `search_regulations` tool, but its tool-call output
is the **nested OpenAI shape** `{"type":"function","function":{"name":…,
"parameters":…}}`, sometimes wrapped in code fences and prose. llama.cpp's
server-side "peg-native" parser expects the **flat** Llama-3.1 shape
`{"name":…,"parameters":…}` and returns HTTP 500
(*"model produced output that does not match the expected peg-native format"*).
Because `ask`/`check` depend on tool-calling, both flows fail end-to-end.

The output format is baked into Krikri's fine-tuned weights (confirmed: overriding
the chat template via `--chat-template-file` did not change it), so no llama.cpp
template/config or GGUF requant fixes it, and switching Python frameworks
(LangChain/LangGraph) hits the same server-side 500. Full analysis and the
rejected alternatives (incl. Approach B — switch to vLLM) are logged in
`docs_internal/ideas.md` under "Krikri tool-calling incompatibility".

## Chosen approach

Bypass llama.cpp's server-side tool parser by not sending a `tools=[…]` param.
Instead use pydantic-ai's **`PromptedOutput`** mode — the documented *"sole option
for models without native tool calling"* — which injects a JSON schema into the
prompt, takes the model's plain text, and parses/validates it client-side (with
retries). The app drives an explicit retrieval loop.

This is added as a **second, config-selected path**. The existing native
function-tool path (used by Qwen and any model with working native tool-calling)
is left untouched.

### Goals

- `ask` and `check` work with Krikri via the prompted path.
- Native path (Qwen) unchanged and still passing its tests.
- SSE contract and frontend unchanged.
- Token-by-token streaming of the final answer preserved.
- No DB/schema/frontend changes; no re-ingest.

### Non-goals

- Making the prompted path the default or removing the native path.
- vLLM/Ollama (Approach B/C) — documented in `ideas.md`, not built here.
- Multi-turn chat, citation validation, or other `ideas.md` items.
- Measuring answer quality (a follow-up eval task; see "Follow-ups").

## §1 — Config switch & dispatch

- Add `tool_mode: Literal["native", "prompted"]` to `Config` (frozen dataclass),
  env override `TOOL_MODE`, **default `"native"`**.
- Krikri is run with `TOOL_MODE=prompted` (set in `.env.docker`).
- Dispatch happens at exactly one place per entry point (factory + SSE entry +
  CLI). No branching deeper than that; the two paths do not share loop code.

## §2 — Prompted path: two-phase loop

New module `agent/core/actions.py`:

```python
from pydantic import BaseModel

class SearchAction(BaseModel):
    query: str
    top_k: int = 5

class Done(BaseModel):
    """Signals the planner has gathered enough to answer."""
```

**Phase 1 — retrieval planner** (`agent/core/loop.py`):

- A pydantic-ai `Agent` built with
  `output_type=PromptedOutput([SearchAction, Done])`, no function tool registered,
  instructions describing the loop protocol (see §prompts).
- Loop:
  1. Run the planner (`await agent.run(..., message_history=history)`).
  2. `result.output` is `SearchAction` or `Done`.
  3. On `SearchAction`: call `search_regulations(deps, action.query, action.top_k)`
     (the existing plain function in `deps.py`, reused as-is), append the retrieved
     chunks to `history` as a user/tool message, continue.
  4. On `Done`, or when `max_search_iters` is reached: exit Phase 1.
- `history = result.all_messages()` threads the conversation across iterations.

**Phase 2 — answer writer**:

- A plain streamed completion (no `PromptedOutput`, no tools) over the accumulated
  `history`, instructed to write the final answer with `[celex_id]` citations.
- Streams tokens, surfaced as SSE `token` frames.

**Rationale for two phases (judgment call, approved):** keeps token-by-token
streaming. If the answer were returned as a `PromptedOutput` field, it would be
trapped inside JSON and the UI would receive the whole answer as one lump — a
regression from today's streaming UX. Two-phase costs one extra model call.

## §prompts

- `agent/core/prompts.py` gains prompted-path variants (kept separate from the
  existing `ASK_INSTRUCTIONS`/`CHECK_INSTRUCTIONS`, which the native path still
  uses):
  - **Planner instructions** (ask + check): explain that each turn the model must
    return either a `SearchAction` (to retrieve) or `Done` (when it has enough);
    for `check`, instruct one `SearchAction` per identified topic/obligation.
  - **Writer instructions**: the current ask/check guidance (cite `celex_id`, say
    so when nothing relevant was found; check = surface relevant law only, never
    declare compliance).

## §3 — Streaming & integration (SSE frames unchanged)

- `backend/streaming.py` gains `prompted_sse_events(config, prompt, deps, kind)`
  alongside the existing `agent_sse_events`. It emits the **same** frames:
  - `status` `{"phase":"thinking"}` at start and between phases,
  - `tool` `{"query": …}` once per `SearchAction`,
  - `token` `{"text": …}` for each Phase-2 token,
  - `done` `{}` at the end,
  - `error` `{"message": <generic>}` on failure.
- `backend/routes.py` `_sse_response` selects the generator by
  `config.tool_mode`. `AskRequest`/`CheckRequest`/`SearchResponse` schemas and the
  frontend are unchanged.
- `main.py` `ask`/`check`: native → current `agent.run_sync`; prompted → run the
  loop synchronously and echo the assembled answer.

## §4 — Error handling & bounds

- `max_search_iters: int` in `Config` (env `MAX_SEARCH_ITERS`, default `5`) caps
  Phase 1; on cap, proceed to Phase 2 with whatever was retrieved.
- `PromptedOutput` validation failures are retried by pydantic-ai; if it still
  fails to parse, fall back to Phase 2 (answer directly) rather than 500.
- Planner returning `Done` with zero searches is valid → answer directly (matches
  "say so if nothing relevant is found").
- SSE `error` frames emit a **generic** client message; the real exception is
  logged server-side. This also closes the `str(exc)` info-leak noted in
  `ideas.md`.

## §5 — Testing

- `tests/test_agent.py` (or a new `tests/test_prompted_loop.py`):
  - Loop with a mock planner scripted `SearchAction → SearchAction → Done`:
    assert `search_regulations` fires per action and `history` threads.
  - `max_search_iters` cap forces Phase 2.
  - Zero-search `Done` path answers directly.
  - `prompted_sse_events` yields the expected frame sequence
    (`status`→`tool`→…→`token`→`done`).
- Existing native-path tests remain unchanged and green — the regression net for
  the dual-path choice.
- All unit tests stay runnable without a live model/DB (mock the agent + search).

## Files touched

| File | Change |
|------|--------|
| `config.py` | add `tool_mode`, `max_search_iters` (+ env overrides) |
| `agent/core/actions.py` | **new** — `SearchAction`, `Done` |
| `agent/core/loop.py` | **new** — planner loop + writer, `run_prompted(...)` |
| `agent/core/factory.py` | branch native vs prompted agent construction |
| `agent/core/prompts.py` | add planner + writer instruction variants |
| `agent/core/deps.py` | reuse `search_regulations`; no behavior change expected |
| `backend/streaming.py` | add `prompted_sse_events`; sanitize error frames |
| `backend/routes.py` | select generator by `tool_mode` (thin dispatch) |
| `main.py` | `ask`/`check` dispatch native vs prompted |
| `.env.docker` | `TOOL_MODE=prompted` for Krikri (ops, not code) |
| tests | new prompted-loop tests; native tests unchanged |

## Follow-ups (not in this spec)

- Eval the prompted path on Krikri (retrieval hit rate + judged quality), ideally
  via GreekBarBench — reliability of `PromptedOutput` on an 8B is the open risk.
- If reliability/throughput is insufficient, revisit Approach B (vLLM) per
  `ideas.md`.

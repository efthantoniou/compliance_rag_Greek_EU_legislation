"""Prompted-output tool loop: the model path for models (e.g. Krikri) whose
tool-call output llama.cpp's native parser rejects.

Phase 1 (planner): a PromptedOutput agent returns a SearchAction or Done per
turn; we run search ourselves and feed results back. Phase 2 (writer): a plain
agent streams the final answer token-by-token. Pure and injectable — no model
or DB is imported by ``run_prompted``, so it is unit-testable with fakes.
"""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Literal

from pydantic_ai.exceptions import UnexpectedModelBehavior

from agent.core.actions import Done
from agent.core.deps import search_regulations
from agent.core.factory import build_planner_agent, build_writer_agent
from agent.core.prompts import (
    PLANNER_ASK,
    PLANNER_CHECK,
    WRITER_ASK,
    WRITER_CHECK,
)


# Per-document preview text sent to the UI with each search; the full chunk
# only goes to the writer.
SNIPPET_CHARS = 280


@dataclass
class ToolCall:
    query: str
    celex_ids: list[str] = field(default_factory=list)
    snippets: dict[str, str] = field(default_factory=dict)  # celex_id -> best chunk preview


def _snippets(chunks: list) -> dict[str, str]:
    snippets: dict[str, str] = {}
    for c in chunks:  # ranked best-first, so the first chunk per document wins
        if c.celex_id not in snippets:
            text = c.text.strip()
            snippets[c.celex_id] = text if len(text) <= SNIPPET_CHARS else text[:SNIPPET_CHARS] + "…"
    return snippets


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
) -> AsyncIterator["ToolCall | Token"]:
    history: list = []
    collected: list = []
    next_input = user_prompt

    for _ in range(max_search_iters):
        try:
            result = await planner.run(next_input, message_history=history)
        except UnexpectedModelBehavior:
            # The planner could not produce a parseable SearchAction/Done even
            # after retries. Stop planning and answer with what we have (spec §4).
            break
        history = result.all_messages()
        action = result.output
        if isinstance(action, Done):
            break
        # SearchAction
        chunks = search_fn(action.query, action.top_k)
        collected.extend(chunks)
        yield ToolCall(
            query=action.query,
            celex_ids=[c.celex_id for c in chunks],
            snippets=_snippets(chunks),
        )
        next_input = _planner_feedback(action.query, chunks)

    writer_prompt = format_writer_prompt(user_prompt, collected)
    async with writer.run_stream(writer_prompt) as stream:
        async for delta in stream.stream_text(delta=True):
            yield Token(text=delta)


_PLANNER = {"ask": PLANNER_ASK, "check": PLANNER_CHECK}
_WRITER = {"ask": WRITER_ASK, "check": WRITER_CHECK}


async def prompted_events(
    config,
    deps,
    user_prompt: str,
    kind: Literal["ask", "check"],
) -> AsyncIterator["ToolCall | Token"]:
    planner = build_planner_agent(config, _PLANNER[kind])
    writer = build_writer_agent(config, _WRITER[kind])

    def search_fn(query: str, top_k: int) -> list:
        return search_regulations(deps, query, top_k)

    async for event in run_prompted(
        planner, writer, search_fn, user_prompt, config.max_search_iters
    ):
        yield event

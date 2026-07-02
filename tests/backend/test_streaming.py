import json

import pytest
from pydantic_ai import (
    AgentRunResultEvent,
    FunctionToolCallEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)
from pydantic_ai.messages import TextPart, ToolCallPart
from pydantic_ai.run import AgentRunResult

from backend.streaming import agent_sse_events, format_sse


def test_format_sse_frames_event_and_json_data():
    frame = format_sse("token", {"text": "hi"})
    assert frame == 'event: token\ndata: {"text": "hi"}\n\n'


def _tool_event() -> FunctionToolCallEvent:
    return FunctionToolCallEvent(
        part=ToolCallPart(tool_name="_search_regulations_tool", args={"query": "vat"})
    )


def _start_text_event(content: str) -> PartStartEvent:
    return PartStartEvent(index=0, part=TextPart(content=content))


def _delta_event() -> PartDeltaEvent:
    return PartDeltaEvent(index=0, delta=TextPartDelta(content_delta="Hello"))


def _result_event() -> AgentRunResultEvent:
    return AgentRunResultEvent(result=AgentRunResult(output="Hello world"))


class _FakeEventStream:
    """Mimics `async with agent.run_stream_events(...) as events`."""

    def __init__(self, events):
        self._events = events

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        async def gen():
            for e in self._events:
                yield e
        return gen()


class _FakeAgent:
    def __init__(self, events):
        self._events = events

    def run_stream_events(self, prompt, deps=None):
        return _FakeEventStream(self._events)


@pytest.mark.anyio
async def test_agent_sse_events_translates_event_types():
    agent = _FakeAgent([
        _tool_event(),
        _delta_event(),
        _result_event(),
    ])
    frames = []
    async for frame in agent_sse_events(agent, "q", deps=None):
        frames.append(frame)

    # First a status frame, then tool, token, done
    assert frames[0] == format_sse("status", {"phase": "thinking"})
    assert format_sse("tool", {"query": "vat"}) in frames
    assert format_sse("token", {"text": "Hello"}) in frames
    assert frames[-1] == format_sse("done", {})


@pytest.mark.anyio
async def test_agent_sse_events_emits_first_text_chunk_from_part_start():
    # pydantic-ai delivers the first chunk of a text response as a
    # PartStartEvent(TextPart(...)); only the rest arrive as PartDeltaEvent.
    # The first chunk must not be dropped, or the answer loses its first letter.
    agent = _FakeAgent([
        _start_text_event("Η"),
        PartDeltaEvent(index=0, delta=TextPartDelta(content_delta=" Επιτροπή")),
        _result_event(),
    ])
    frames = []
    async for frame in agent_sse_events(agent, "q", deps=None):
        frames.append(frame)

    token_frames = [f for f in frames if f.startswith("event: token")]
    assert token_frames[0] == format_sse("token", {"text": "Η"})
    assert format_sse("token", {"text": " Επιτροπή"}) in frames


@pytest.mark.anyio
async def test_agent_sse_events_emits_error_frame_on_exception():
    class _BoomAgent:
        def run_stream_events(self, prompt, deps=None):
            raise RuntimeError("boom")

    frames = []
    async for frame in agent_sse_events(_BoomAgent(), "q", deps=None):
        frames.append(frame)

    assert any(frame.startswith("event: error") for frame in frames)
    error_frame = [f for f in frames if f.startswith("event: error")][0]
    payload = json.loads(error_frame.split("data: ", 1)[1].strip())
    assert "boom" in payload["message"]

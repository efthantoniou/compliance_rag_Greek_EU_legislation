import json
from collections.abc import AsyncIterator

from pydantic_ai import (
    AgentRunResultEvent,
    FunctionToolCallEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)
from pydantic_ai.messages import TextPart

TOOL_NAME = "_search_regulations_tool"


def format_sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _tool_query(args) -> str:
    if isinstance(args, dict):
        return str(args.get("query", ""))
    try:
        return str(json.loads(args).get("query", ""))
    except (ValueError, TypeError):
        return ""


async def agent_sse_events(agent, prompt, deps) -> AsyncIterator[str]:
    yield format_sse("status", {"phase": "thinking"})
    try:
        async with agent.run_stream_events(prompt, deps=deps) as events:
            async for event in events:
                if isinstance(event, FunctionToolCallEvent):
                    if event.part.tool_name == TOOL_NAME:
                        yield format_sse("tool", {"query": _tool_query(event.part.args)})
                elif isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
                    # pydantic-ai delivers the first chunk of a text response as a
                    # PartStartEvent; without this the answer loses its first token.
                    if event.part.content:
                        yield format_sse("token", {"text": event.part.content})
                elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                    yield format_sse("token", {"text": event.delta.content_delta})
                elif isinstance(event, AgentRunResultEvent):
                    yield format_sse("done", {})
    except Exception as exc:  # surface any failure as a clean SSE error frame
        yield format_sse("error", {"message": str(exc)})

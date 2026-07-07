import json
import logging
from collections.abc import AsyncIterator

from agent.core.loop import ToolCall, Token, prompted_events

logger = logging.getLogger(__name__)

_GENERIC_ERROR = "Something went wrong while generating the answer. Please try again."


def format_sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def prompted_sse_events(config, deps, prompt, kind) -> AsyncIterator[str]:
    """SSE frames for the prompted (NativeOutput) tool loop: emits
    status / tool / token / done / error frames."""
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

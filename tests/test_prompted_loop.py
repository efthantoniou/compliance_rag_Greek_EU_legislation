import pytest

from agent.core.actions import SearchAction, Done


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_search_action_defaults():
    a = SearchAction(query="φορολογία")
    assert a.query == "φορολογία"
    assert a.top_k == 5


def test_done_is_constructable():
    assert Done() is not None


def test_prompt_variants_exist_and_mention_protocol():
    from agent.core import prompts

    assert "SearchAction" in prompts.PLANNER_ASK
    assert "Done" in prompts.PLANNER_ASK
    assert "SearchAction" in prompts.PLANNER_CHECK
    # writer prompts keep the citation / no-compliance guidance
    assert "celex_id" in prompts.WRITER_ASK
    assert "compliant" in prompts.WRITER_CHECK


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
    from agent.core.loop import ToolCall, Token, run_prompted

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
    tool_calls = [e for e in events if isinstance(e, ToolCall)]
    assert len(tool_calls) == 1
    assert tool_calls[0].query == "q1"
    assert tool_calls[0].celex_ids == ["CELEX1"]
    assert [e.text for e in events if isinstance(e, Token)] == ["Hel", "lo"]
    assert "CELEX1" in writer.prompt


@pytest.mark.anyio
async def test_loop_respects_max_iters():
    from agent.core.loop import ToolCall, Token, run_prompted

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
async def test_loop_falls_back_to_writer_on_planner_parse_failure():
    from pydantic_ai.exceptions import UnexpectedModelBehavior

    from agent.core.loop import ToolCall, Token, run_prompted

    class _FailingPlanner:
        async def run(self, prompt, message_history=None):
            raise UnexpectedModelBehavior("could not parse output")

    writer = _FakeWriter(["fallback answer"])
    events = await _drain(
        run_prompted(_FailingPlanner(), writer, lambda q, k: [], "u", max_search_iters=5)
    )
    # no tool calls happened, but the writer still produced an answer
    assert not [e for e in events if isinstance(e, ToolCall)]
    assert [e.text for e in events if isinstance(e, Token)] == ["fallback answer"]


@pytest.mark.anyio
async def test_loop_zero_search_answers_directly():
    from agent.core.loop import ToolCall, Token, run_prompted

    planner = _FakePlanner([Done()])
    writer = _FakeWriter(["ans"])
    events = await _drain(
        run_prompted(planner, writer, lambda q, k: [], "u", max_search_iters=5)
    )
    assert not [e for e in events if isinstance(e, ToolCall)]
    assert [e.text for e in events if isinstance(e, Token)] == ["ans"]


def test_format_writer_prompt_with_and_without_chunks():
    from agent.core.loop import format_writer_prompt

    with_chunks = format_writer_prompt("Q", [_Chunk("CX", "body")])
    assert "Q" in with_chunks and "CX" in with_chunks and "body" in with_chunks
    empty = format_writer_prompt("Q", [])
    assert "Q" in empty


@pytest.mark.anyio
async def test_prompted_events_wires_agents_and_search(monkeypatch):
    from types import SimpleNamespace

    import agent.core.loop as loop_mod
    from agent.core.loop import Token

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
        async for ev in loop_mod.prompted_events(
            config, deps=object(), user_prompt="u", kind="ask"
        )
    ]
    assert [e.text for e in events if isinstance(e, Token)] == ["ok"]
    assert "SearchAction" in calls["planner_instructions"]  # PLANNER_ASK selected
    assert "celex_id" in calls["writer_instructions"]  # WRITER_ASK selected


@pytest.mark.anyio
async def test_prompted_sse_frames(monkeypatch):
    import backend.streaming as streaming_mod

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
    assert "event: tool" in joined and '"query": "q"' in joined
    assert "event: token" in joined and '"text": "A"' in joined
    assert "event: done" in joined


@pytest.mark.anyio
async def test_prompted_sse_sanitizes_errors(monkeypatch):
    import backend.streaming as streaming_mod

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

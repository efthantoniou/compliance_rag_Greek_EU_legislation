import json
from unittest.mock import MagicMock, patch

from pydantic_ai.messages import ToolReturnPart

from config import Config
from evals.judge import JudgeResult, JudgeScores
from evals.runner import _retrieved_celex_ids, run_eval
from models import Chunk


def _fake_config() -> Config:
    return Config(
        surrealdb_url="ws://localhost:8000/rpc",
        surrealdb_user="root",
        surrealdb_pass="root",
        surrealdb_ns="compliance",
        surrealdb_db="compliance",
        llamacpp_url="http://localhost:8080/v1",
        llamacpp_model="test-model",
        ingest_limit=2,
    )


def _tool_message(chunks):
    message = MagicMock()
    message.parts = [
        ToolReturnPart(
            tool_name="_search_regulations_tool",
            content=chunks,
            tool_call_id="tc-1",
        )
    ]
    return message


def test_retrieved_celex_ids_dedupes_across_messages():
    messages = [
        _tool_message([Chunk(text="a", celex_id="A1", labels=[])]),
        _tool_message([
            Chunk(text="b", celex_id="A1", labels=[]),
            Chunk(text="c", celex_id="B2", labels=[]),
        ]),
    ]

    assert _retrieved_celex_ids(messages) == ["A1", "B2"]


def test_run_eval_writes_results_with_retrieval_hit(tmp_path):
    gt = tmp_path / "gt.jsonl"
    gt.write_text(
        json.dumps({
            "id": "A1-1", "celex_id": "A1",
            "question": "Q?", "expected_answer": "A.", "difficulty": "easy",
        }) + "\n",
        encoding="utf-8",
    )
    fake_run = MagicMock()
    fake_run.output = "the answer"
    fake_run.all_messages.return_value = [
        _tool_message([Chunk(text="a", celex_id="A1", labels=[])])
    ]
    fake_agent = MagicMock()
    fake_agent.run_sync.return_value = fake_run
    judgement = JudgeResult(
        scores=JudgeScores(
            factual_correctness=1.0, completeness=0.8,
            citation_quality=0.5, no_hedging=1.0,
        ),
        verdict="correct",
        notes="ok",
    )
    out = tmp_path / "results.jsonl"

    with patch("evals.runner.build_ask_agent", return_value=fake_agent), \
         patch("evals.runner.judge_answer", return_value=judgement):
        result_path = run_eval(
            _fake_config(), embedder=object(), ground_truth_path=gt, output_path=out
        )

    records = [json.loads(l) for l in result_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["retrieval_hit"] is True
    assert records[0]["verdict"] == "correct"
    assert records[0]["rag_sources"] == ["A1"]

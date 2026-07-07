import json
from unittest.mock import patch

from config import Config
from evals.judge import JudgeResult, JudgeScores
from evals.runner import run_eval


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


def test_run_eval_writes_results_with_retrieval_hit(tmp_path):
    gt = tmp_path / "gt.jsonl"
    gt.write_text(
        json.dumps({
            "id": "A1-1", "celex_id": "A1",
            "question": "Q?", "expected_answer": "A.", "difficulty": "easy",
        }) + "\n",
        encoding="utf-8",
    )

    async def fake_collect(config, deps, question, kind):
        return "the answer", ["A1"]

    judgement = JudgeResult(
        scores=JudgeScores(
            factual_correctness=1.0, completeness=0.8,
            citation_quality=0.5, no_hedging=1.0,
        ),
        verdict="correct",
        notes="ok",
    )
    out = tmp_path / "results.jsonl"

    with patch("evals.runner.collect_answer_and_sources", fake_collect), \
         patch("evals.runner.judge_answer", return_value=judgement):
        result_path = run_eval(
            _fake_config(), embedder=object(), ground_truth_path=gt, output_path=out
        )

    records = [json.loads(l) for l in result_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["retrieval_hit"] is True
    assert records[0]["verdict"] == "correct"
    assert records[0]["rag_sources"] == ["A1"]
    assert records[0]["rag_answer"] == "the answer"

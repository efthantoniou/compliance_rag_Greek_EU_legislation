import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, patch

from config import Config
from evals.judge import JudgeResult, JudgeScores, judge_answer


def _fake_config() -> Config:
    return Config(
        surrealdb_url="ws://localhost:8000/rpc",
        surrealdb_user="root",
        surrealdb_pass="root",
        surrealdb_ns="compliance",
        surrealdb_db="compliance",
        llamacpp_url="http://localhost:8080/v1",
        llamacpp_model="rag-model",
        ingest_limit=2,
    )


def _judge_agent() -> MagicMock:
    agent = MagicMock()
    agent.run = AsyncMock()
    agent.run.return_value.output = JudgeResult(
        scores=JudgeScores(
            factual_correctness=1.0, completeness=1.0,
            citation_quality=1.0, no_hedging=1.0,
        ),
        verdict="correct",
        notes="ok",
    )
    return agent


def test_judge_uses_rag_endpoint_when_no_judge_endpoint_configured():
    with patch("evals.judge.build_structured_agent", return_value=_judge_agent()) as build:
        asyncio.run(judge_answer(_fake_config(), "Q", "A", "answer", ["A1"]))

    assert build.call_args.kwargs["base_url"] == "http://localhost:8080/v1"
    assert build.call_args.kwargs["model_name"] == "rag-model"


def test_judge_uses_its_own_endpoint_when_configured():
    # Pinning the judge keeps scores comparable across RAG model swaps
    # (e.g. Q8_0 vs Q6_K); otherwise the answerer and the grader change together.
    config = replace(
        _fake_config(),
        judge_llamacpp_url="http://judge:8081/v1",
        judge_llamacpp_model="judge-model",
    )
    with patch("evals.judge.build_structured_agent", return_value=_judge_agent()) as build:
        asyncio.run(judge_answer(config, "Q", "A", "answer", ["A1"]))

    assert build.call_args.kwargs["base_url"] == "http://judge:8081/v1"
    assert build.call_args.kwargs["model_name"] == "judge-model"

from unittest.mock import patch

import pytest
from pydantic_evals import Case

from config import Config
from evals.dataset import GroundTruthMeta, RagOutput, new_ground_truth_dataset
from evals.evaluators import GreekQueries, RagJudge, RetrievalRank, is_greek_query
from evals.judge import JudgeResult, JudgeScores


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


def _evaluate(evaluator, output: RagOutput, celex_id: str = "A1"):
    dataset = new_ground_truth_dataset([
        Case(
            name="A1-1",
            inputs="Q?",
            expected_output="A.",
            metadata=GroundTruthMeta(celex_id=celex_id, difficulty="easy"),
        )
    ])
    dataset.add_evaluator(evaluator)

    async def task(question: str) -> RagOutput:
        return output

    report = dataset.evaluate_sync(task, progress=False)
    assert not report.failures
    case = report.cases[0]
    assert not case.evaluator_failures, case.evaluator_failures
    return case


def _output(sources: list[str], queries: list[str] | None = None) -> RagOutput:
    return RagOutput(answer="answer", sources=sources, queries=queries or ["φόροι"])


@pytest.mark.parametrize(
    ("sources", "hit", "hit_at_1", "reciprocal_rank"),
    [
        (["A1", "B2"], True, True, 1.0),
        (["B2", "C3", "A1"], True, False, 1 / 3),
        (["B2"], False, False, 0.0),
        ([], False, False, 0.0),
    ],
)
def test_retrieval_rank_scores_position_of_ground_truth_document(
    sources, hit, hit_at_1, reciprocal_rank
):
    case = _evaluate(RetrievalRank(), _output(sources))

    assert case.assertions["retrieval_hit"].value is hit
    assert case.assertions["hit@1"].value is hit_at_1
    assert case.scores["reciprocal_rank"].value == pytest.approx(reciprocal_rank)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("προστασία δεδομένων", True),
        ("κανονισμός GDPR πρόστιμα", True),  # conventional Latin names are allowed
        ("data protection", False),
        ("prostasia dedomenon", False),  # transliterated Greek is still Latin script
        ("GDPR", False),
    ],
)
def test_is_greek_query(query, expected):
    assert is_greek_query(query) is expected


def test_greek_queries_fails_and_names_the_offending_query():
    case = _evaluate(GreekQueries(), _output(["A1"], ["φορολογία", "tax rules"]))

    result = case.assertions["greek_queries"]
    assert result.value is False
    assert "tax rules" in result.reason


def test_greek_queries_passes_when_every_query_is_greek():
    case = _evaluate(GreekQueries(), _output(["A1"], ["φορολογία", "ΦΠΑ"]))

    assert case.assertions["greek_queries"].value is True


def test_rag_judge_reports_judge_scores_and_verdict():
    judgement = JudgeResult(
        scores=JudgeScores(
            factual_correctness=1.0, completeness=0.8,
            citation_quality=0.5, no_hedging=1.0,
        ),
        verdict="partially_correct",
        notes="misses the deadline",
    )
    with patch("evals.evaluators.judge_answer", return_value=judgement) as judge:
        case = _evaluate(RagJudge(_fake_config()), _output(["A1"]))

    judge.assert_called_once_with(_fake_config(), "Q?", "A.", "answer", ["A1"])
    assert case.scores["factual_correctness"].value == 1.0
    assert case.scores["completeness"].value == 0.8
    assert case.scores["citation_quality"].value == 0.5
    assert case.scores["no_hedging"].value == 1.0
    assert case.labels["verdict"].value == "partially_correct"
    assert case.labels["verdict"].reason == "misses the deadline"


def test_rag_judge_runs_a_real_agent_inside_the_eval_event_loop():
    # pydantic-evals awaits evaluators inside its own event loop; a judge that
    # used Agent.run_sync there would fail every case with a loop error.
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    agent = Agent(TestModel(), output_type=JudgeResult)
    with patch("evals.judge.build_structured_agent", return_value=agent):
        case = _evaluate(RagJudge(_fake_config()), _output(["A1"]))

    assert case.labels["verdict"].value in {"correct", "partially_correct", "incorrect"}

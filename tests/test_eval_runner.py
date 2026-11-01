from dataclasses import replace
from unittest.mock import AsyncMock, patch

from pydantic_evals import Case

from agent.core.loop import Token, ToolCall
from config import Config
from evals.dataset import GroundTruthMeta, new_ground_truth_dataset
from evals.judge import JudgeResult, JudgeScores
from evals.runner import load_report, print_comparison, run_eval


def _fake_config() -> Config:
    return Config(
        surrealdb_url="ws://localhost:8000/rpc",
        surrealdb_user="root",
        surrealdb_pass="root",
        surrealdb_ns="compliance",
        surrealdb_db="compliance",
        llamacpp_url="http://localhost:8080/v1",
        llamacpp_model="/models/llama-krikri-8b-instruct-q6_k.gguf",
        ingest_limit=2,
    )


_JUDGEMENT = JudgeResult(
    scores=JudgeScores(
        factual_correctness=1.0, completeness=0.8,
        citation_quality=0.5, no_hedging=1.0,
    ),
    verdict="correct",
    notes="ok",
)


def _write_ground_truth(tmp_path, n: int = 1):
    path = tmp_path / "gt.yaml"
    new_ground_truth_dataset([
        Case(
            name=f"A1-{i}",
            inputs=f"Q{i}?",
            expected_output="A.",
            metadata=GroundTruthMeta(celex_id="A1", difficulty="easy"),
        )
        for i in range(1, n + 1)
    ]).to_file(path)
    return path


async def _fake_events(config, deps, question, kind):
    yield ToolCall(query="φόροι", celex_ids=["A1", "B2"])
    yield ToolCall(query="ΦΠΑ", celex_ids=["A1", "C3"])
    yield Token(text="the ")
    yield Token(text="answer")


def _run(tmp_path, config=None, events=_fake_events, **kwargs):
    with patch("evals.runner.prompted_events", events), \
         patch("evals.evaluators.judge_answer", AsyncMock(return_value=_JUDGEMENT)):
        return run_eval(
            config or _fake_config(),
            embedder=object(),
            ground_truth_path=kwargs.pop("ground_truth_path", None) or _write_ground_truth(tmp_path),
            report_dir=tmp_path / "reports",
            **kwargs,
        )


def test_run_eval_collects_answer_sources_queries_and_search_count(tmp_path):
    report = load_report(_run(tmp_path, name="run-a"))

    case = report.cases[0]
    assert case.output["answer"] == "the answer"
    assert case.output["sources"] == ["A1", "B2", "C3"]  # deduped, retrieval order
    assert case.output["queries"] == ["φόροι", "ΦΠΑ"]
    assert case.metrics["searches"] == 2
    assert case.assertions["retrieval_hit"].value is True
    assert case.assertions["greek_queries"].value is True
    assert case.labels["verdict"].value == "correct"


def test_run_eval_saves_named_report_with_run_settings(tmp_path):
    path = _run(tmp_path, name="run-a", rerank=False)

    assert path == tmp_path / "reports" / "run-a.json"
    metadata = load_report(path).experiment_metadata
    assert metadata["rag_model"] == "llama-krikri-8b-instruct-q6_k.gguf"
    assert metadata["judge_model"] == "llama-krikri-8b-instruct-q6_k.gguf"
    assert metadata["rerank"] is False


def test_run_eval_default_name_identifies_model_and_rerank_mode(tmp_path):
    path = _run(tmp_path)

    assert path.name.startswith("llama-krikri-8b-instruct-q6_k-rerank-")


def test_run_eval_limit_evaluates_only_first_cases(tmp_path):
    path = _run(tmp_path, ground_truth_path=_write_ground_truth(tmp_path, n=3), limit=2)

    assert sorted(c.name for c in load_report(path).cases) == ["A1-1", "A1-2"]


def test_run_eval_records_task_errors_instead_of_raising(tmp_path):
    async def broken_events(config, deps, question, kind):
        raise RuntimeError("llama.cpp went away")
        yield  # pragma: no cover - makes this an async generator

    report = load_report(_run(tmp_path, events=broken_events))

    assert report.cases == []
    assert "llama.cpp went away" in report.failures[0].error_message


def test_comparison_warns_when_runs_used_different_judges(tmp_path, capsys):
    baseline = load_report(_run(tmp_path, name="q8"))
    pinned = replace(_fake_config(), judge_llamacpp_model="/models/judge.gguf")
    report = load_report(_run(tmp_path, config=pinned, name="q6"))
    capsys.readouterr()

    print_comparison(report, baseline)

    out = capsys.readouterr().out
    assert "judge model differs" in out
    assert "q8 → q6" in out


def test_comparison_does_not_warn_when_judge_is_the_same(tmp_path, capsys):
    baseline = load_report(_run(tmp_path, name="q8"))
    report = load_report(_run(tmp_path, name="q6"))
    capsys.readouterr()

    print_comparison(report, baseline)

    assert "judge model differs" not in capsys.readouterr().out

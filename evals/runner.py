import asyncio
from datetime import datetime
from pathlib import Path

import click
from pydantic_evals import increment_eval_metric
from pydantic_evals.reporting import EvaluationReport, EvaluationReportAdapter

from agent import AgentDeps
from agent.core.loop import ToolCall, prompted_events
from config import Config
from evals.dataset import RagOutput, load_ground_truth, new_ground_truth_dataset
from evals.evaluators import GreekQueries, RagJudge, RetrievalRank
from evals.judge import judge_model

DEFAULT_REPORT_DIR = Path("eval_data/reports")


def _make_task(config: Config, deps: AgentDeps):
    async def answer_question(question: str) -> RagOutput:
        answer_parts: list[str] = []
        sources: list[str] = []
        queries: list[str] = []
        async for event in prompted_events(config, deps, question, "ask"):
            if isinstance(event, ToolCall):
                queries.append(event.query)
                increment_eval_metric("searches", 1)
                for cid in event.celex_ids:
                    if cid not in sources:
                        sources.append(cid)
            else:
                answer_parts.append(event.text)
        return RagOutput(answer="".join(answer_parts), sources=sources, queries=queries)

    return answer_question


def run_eval(
    config: Config,
    embedder,
    ground_truth_path: Path,
    *,
    name: str | None = None,
    limit: int | None = None,
    rerank: bool = True,
    repeat: int = 1,
    baseline_path: Path | None = None,
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> Path:
    dataset = load_ground_truth(ground_truth_path)
    if limit is not None:
        dataset = new_ground_truth_dataset(dataset.cases[:limit])
    dataset.add_evaluator(RetrievalRank())
    dataset.add_evaluator(GreekQueries())
    dataset.add_evaluator(RagJudge(config))

    rag_model = Path(config.llamacpp_model).name
    name = name or (
        f"{Path(config.llamacpp_model).stem}-{'rerank' if rerank else 'norerank'}"
        f"-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    deps = AgentDeps(config=config, embedder=embedder, rerank=rerank)
    # One local llama.cpp server: running cases concurrently only queues requests
    # behind each other and skews per-case durations.
    report = asyncio.run(
        dataset.evaluate(
            _make_task(config, deps),
            name=name,
            max_concurrency=1,
            repeat=repeat,
            metadata={
                "rag_model": rag_model,
                "judge_model": Path(judge_model(config)).name,
                "rerank": rerank,
                "reranker_device": config.reranker_device,
                "max_search_iters": config.max_search_iters,
                "ground_truth": ground_truth_path.name,
            },
        )
    )

    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{name}.json"
    path.write_bytes(EvaluationReportAdapter.dump_json(report, indent=2))
    print_comparison(report, load_report(baseline_path) if baseline_path else None)
    return path


def load_report(path: Path) -> EvaluationReport:
    return EvaluationReportAdapter.validate_json(path.read_bytes())


def print_comparison(report: EvaluationReport, baseline: EvaluationReport | None = None) -> None:
    if baseline is not None:
        judges = [
            (r.experiment_metadata or {}).get("judge_model") for r in (baseline, report)
        ]
        if judges[0] != judges[1]:
            click.echo(
                f"WARNING: judge model differs ({judges[0]} → {judges[1]}); judge scores "
                "are not comparable. Trust only retrieval_hit / hit@1 / reciprocal_rank."
            )
    report.print(baseline=baseline, include_averages=True)

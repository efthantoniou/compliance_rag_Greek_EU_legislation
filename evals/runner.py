import asyncio
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import click

from agent import AgentDeps
from agent.core.loop import collect_answer_and_sources
from config import Config
from evals.judge import judge_answer

_SCORE_KEYS = ("factual_correctness", "completeness", "citation_quality", "no_hedging")


def run_eval(
    config: Config,
    embedder,
    ground_truth_path: Path,
    output_path: Path | None = None,
    limit: int | None = None,
    rerank: bool = True,
) -> Path:
    lines = ground_truth_path.read_text(encoding="utf-8").splitlines()
    qa_pairs = [json.loads(line) for line in lines if line.strip()]
    if limit is not None:
        qa_pairs = qa_pairs[:limit]
    output_path = output_path or (
        Path("eval_data") / f"results-{datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    deps = AgentDeps(config=config, embedder=embedder, rerank=rerank)
    results: list[dict] = []
    with output_path.open("w", encoding="utf-8") as f:
        for qa in qa_pairs:
            try:
                answer, sources = asyncio.run(
                    collect_answer_and_sources(config, deps, qa["question"], "ask")
                )
                judgement = judge_answer(
                    config, qa["question"], qa["expected_answer"], answer, sources
                )
                record = {
                    "ground_truth_id": qa["id"],
                    "celex_id": qa["celex_id"],
                    "difficulty": qa.get("difficulty"),
                    "question": qa["question"],
                    "expected_answer": qa["expected_answer"],
                    "rag_answer": answer,
                    "rag_sources": sources,
                    "retrieval_hit": qa["celex_id"] in sources,
                    "scores": judgement.scores.model_dump(),
                    "verdict": judgement.verdict,
                    "notes": judgement.notes,
                }
            except Exception as exc:
                record = {
                    "ground_truth_id": qa.get("id"),
                    "question": qa.get("question"),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            results.append(record)
            click.echo(
                f"  {record.get('ground_truth_id')}: "
                f"{record.get('verdict', record.get('error'))}"
            )
    _print_summary(results)
    return output_path


def _print_summary(results: list[dict]) -> None:
    scored = [r for r in results if "verdict" in r]
    verdicts = Counter(r["verdict"] for r in scored)
    click.echo(
        f"\nTotal: {len(results)}  correct: {verdicts['correct']}  "
        f"partial: {verdicts['partially_correct']}  "
        f"incorrect: {verdicts['incorrect']}  errors: {len(results) - len(scored)}"
    )
    if scored:
        hit_rate = sum(1 for r in scored if r["retrieval_hit"]) / len(scored)
        click.echo(f"Retrieval hit rate: {hit_rate:.0%}")
    for key in _SCORE_KEYS:
        values = [r["scores"][key] for r in scored if r.get("scores")]
        if values:
            click.echo(f"{key} (mean): {sum(values) / len(values):.2f}")

import re
from dataclasses import dataclass

from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext

from config import Config
from evals.dataset import GroundTruthMeta, RagOutput
from evals.judge import judge_answer

_GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
_LATIN = re.compile(r"[A-Za-z]")

RagContext = EvaluatorContext[str, RagOutput, GroundTruthMeta]


def is_greek_query(query: str) -> bool:
    """Mostly Greek script. Latin is tolerated for conventional names (GDPR, REACH)
    inside an otherwise Greek query, matching the planner's Greek-query rule."""
    return len(_GREEK.findall(query)) > len(_LATIN.findall(query))


@dataclass
class RetrievalRank(Evaluator[str, RagOutput, GroundTruthMeta]):
    """Where the ground-truth document landed among the retrieved sources.
    Deterministic, so it doesn't depend on the local judge's quality."""

    def evaluate(self, ctx: RagContext) -> dict[str, bool | float]:
        sources = ctx.output.sources
        celex_id = ctx.metadata.celex_id
        rank = sources.index(celex_id) + 1 if celex_id in sources else None
        return {
            "retrieval_hit": rank is not None,
            "hit@1": rank == 1,
            "reciprocal_rank": 1 / rank if rank else 0.0,
        }


@dataclass
class GreekQueries(Evaluator[str, RagOutput, GroundTruthMeta]):
    """Every planner search query is Greek. The corpus and the cross-encoder are
    Greek-only, so a non-Greek query retrieves nothing usable."""

    def evaluate(self, ctx: RagContext) -> EvaluationReason:
        bad = [q for q in ctx.output.queries if not is_greek_query(q)]
        if bad:
            return EvaluationReason(value=False, reason=f"non-Greek queries: {bad}")
        return EvaluationReason(value=True)

    def get_default_evaluation_name(self) -> str:
        return "greek_queries"


@dataclass
class RagJudge(Evaluator[str, RagOutput, GroundTruthMeta]):
    """LLM judge: the four rubric scores plus a verdict label (notes as its reason)."""

    config: Config

    async def evaluate(self, ctx: RagContext) -> dict[str, float | EvaluationReason]:
        judgement = await judge_answer(
            self.config,
            ctx.inputs,
            ctx.expected_output,
            ctx.output.answer,
            ctx.output.sources,
        )
        return {
            **judgement.scores.model_dump(),
            "verdict": EvaluationReason(value=judgement.verdict, reason=judgement.notes),
        }

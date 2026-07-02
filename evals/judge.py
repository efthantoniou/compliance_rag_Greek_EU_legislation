from typing import Literal

from pydantic import BaseModel

from config import Config
from evals.llm import build_structured_agent

JUDGE_INSTRUCTIONS = (
    "Είσαι αυστηρός αξιολογητής συστήματος RAG πάνω σε νομοθεσία της ΕΕ. "
    "Δίνεσαι μία ερώτηση, την αναμενόμενη απάντηση από ειδικό, την απάντηση "
    "του συστήματος και τα CELEX ids των πηγών που επικαλέστηκε. Αξιολογείς "
    "την απάντηση του συστήματος ΣΥΓΚΡΙΤΙΚΑ με την αναμενόμενη. "
    "Βαθμοί 0.0-1.0: factual_correctness (σωστά γεγονότα σύμφωνα με την "
    "αναμενόμενη απάντηση), completeness (καλύπτει τα βασικά της σημεία), "
    "citation_quality (επικαλείται CELEX ids κατάλληλα), no_hedging (1.0 αν "
    "δεν υπάρχει διστακτικότητα). verdict: correct = ουσιαστικά σωστή και "
    "πλήρης, partially_correct = σωστά στοιχεία με παραλείψεις ή μικρά λάθη, "
    "incorrect = λάθος, άσχετη, ή αρνείται να απαντήσει ενώ υπάρχει απάντηση. "
    "Το notes είναι μία πρόταση που εξηγεί την αξιολόγηση."
)


class JudgeScores(BaseModel):
    factual_correctness: float
    completeness: float
    citation_quality: float
    no_hedging: float


class JudgeResult(BaseModel):
    scores: JudgeScores
    verdict: Literal["correct", "partially_correct", "incorrect"]
    notes: str


def judge_answer(
    config: Config,
    question: str,
    expected_answer: str,
    rag_answer: str,
    rag_sources: list[str],
) -> JudgeResult:
    agent = build_structured_agent(config, JUDGE_INSTRUCTIONS, JudgeResult)
    sources = ", ".join(rag_sources) if rag_sources else "(κανένα)"
    prompt = (
        f"ΕΡΩΤΗΣΗ:\n{question}\n\n"
        f"ΑΝΑΜΕΝΟΜΕΝΗ ΑΠΑΝΤΗΣΗ:\n{expected_answer}\n\n"
        f"ΑΠΑΝΤΗΣΗ ΣΥΣΤΗΜΑΤΟΣ:\n{rag_answer}\n\n"
        f"ΠΗΓΕΣ ΣΥΣΤΗΜΑΤΟΣ: {sources}"
    )
    return agent.run_sync(prompt).output

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic_evals import Case, Dataset

DATASET_NAME = "eu_legislation_ground_truth"


class GroundTruthMeta(BaseModel):
    celex_id: str
    difficulty: Literal["easy", "medium", "hard"]


# inputs = question, expected_output = expert answer
GroundTruthDataset = Dataset[str, str, GroundTruthMeta]


class RagOutput(BaseModel):
    answer: str
    sources: list[str]  # deduped celex_ids, in retrieval order
    queries: list[str]  # every search query the planner emitted


def new_ground_truth_dataset(cases: list[Case]) -> GroundTruthDataset:
    return GroundTruthDataset(name=DATASET_NAME, cases=cases)


def load_ground_truth(path: Path) -> GroundTruthDataset:
    """Load a YAML/JSON dataset, or a pre-pydantic-evals ground_truth.jsonl."""
    if path.suffix != ".jsonl":
        return GroundTruthDataset.from_file(path)
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return new_ground_truth_dataset([
        Case(
            name=r["id"],
            inputs=r["question"],
            expected_output=r["expected_answer"],
            metadata=GroundTruthMeta(celex_id=r["celex_id"], difficulty=r["difficulty"]),
        )
        for r in records
    ])

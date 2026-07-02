import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from config import Config
from evals.llm import build_structured_agent
from agent.storage.surreal import chunks_by_celex, list_celex_ids

MAX_DOCUMENT_CHARS = 6000

GENERATOR_INSTRUCTIONS = (
    "Είσαι ειδικός στη νομοθεσία της ΕΕ. Δίνεσαι απόσπασμα νομικού κειμένου "
    "και παράγεις ρεαλιστικές ερωτήσεις που θα έκανε νομικός ερευνητής, μαζί "
    "με τις σωστές απαντήσεις βάσει του κειμένου. Κανόνες: οι ερωτήσεις "
    "απαντώνται αποκλειστικά από το κείμενο. Μην εφευρίσκεις πληροφορίες. "
    "Κάνε μίξη δυσκολιών (easy: άμεση αναζήτηση, medium: σύνθεση, hard: "
    "κατανόηση). Οι απαντήσεις είναι κατηγορηματικές, 1-3 προτάσεις. Καμία "
    "ερώτηση δεν αναφέρει το αναγνωριστικό CELEX του εγγράφου."
)


class QAPair(BaseModel):
    question: str
    expected_answer: str
    difficulty: Literal["easy", "medium", "hard"]


class GroundTruthBatch(BaseModel):
    questions: list[QAPair]


def gather_document_text(
    config: Config, celex_id: str, max_chars: int = MAX_DOCUMENT_CHARS
) -> str:
    parts: list[str] = []
    total = 0
    for row in chunks_by_celex(config, celex_id):
        text = (row.get("text") or "").strip()
        if not text:
            continue
        if total + len(text) > max_chars:
            parts.append(text[: max_chars - total])
            break
        parts.append(text)
        total += len(text)
    return "\n\n".join(parts)


def generate_ground_truth(
    config: Config,
    sample_size: int = 5,
    questions_per_doc: int = 3,
    output_path: Path = Path("eval_data/ground_truth.jsonl"),
    seed: int | None = None,
) -> int:
    if seed is not None:
        random.seed(seed)
    celex_ids = list_celex_ids(config)
    if sample_size < len(celex_ids):
        celex_ids = random.sample(celex_ids, sample_size)

    agent = build_structured_agent(config, GENERATOR_INSTRUCTIONS, GroundTruthBatch)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    written = 0
    with output_path.open("w", encoding="utf-8") as f:
        for celex_id in celex_ids:
            document_text = gather_document_text(config, celex_id)
            if not document_text:
                continue
            prompt = (
                f"Παρακάτω είναι απόσπασμα του εγγράφου CELEX {celex_id}. "
                f"Παρήγαγε ακριβώς {questions_per_doc} ερωτοαπαντήσεις.\n\n"
                f"Κείμενο:\n{document_text}"
            )
            try:
                batch = agent.run_sync(prompt).output
            except Exception as exc:
                print(f"skip {celex_id}: {type(exc).__name__}: {exc}")
                continue
            for i, qa in enumerate(batch.questions, start=1):
                record = {
                    "id": f"{celex_id}-{i}",
                    "celex_id": celex_id,
                    "question": qa.question,
                    "expected_answer": qa.expected_answer,
                    "difficulty": qa.difficulty,
                    "generated_at": generated_at,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
    return written

import json
from unittest.mock import MagicMock, patch

from config import Config
from evals.ground_truth import (
    GroundTruthBatch,
    QAPair,
    gather_document_text,
    generate_ground_truth,
)


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


def test_gather_document_text_joins_and_truncates():
    rows = [{"text": "abcde"}, {"text": "fghij"}, {"text": "klmno"}]
    with patch("evals.ground_truth.chunks_by_celex", return_value=rows):
        text = gather_document_text(_fake_config(), "A1", max_chars=8)

    assert text == "abcde\n\nfgh"


def test_generate_ground_truth_writes_jsonl(tmp_path):
    batch = GroundTruthBatch(
        questions=[
            QAPair(question="Q1;", expected_answer="A1.", difficulty="easy"),
            QAPair(question="Q2;", expected_answer="A2.", difficulty="hard"),
        ]
    )
    fake_agent = MagicMock()
    fake_agent.run_sync.return_value.output = batch
    out = tmp_path / "gt.jsonl"

    with patch("evals.ground_truth.list_celex_ids", return_value=["A1"]), \
         patch("evals.ground_truth.chunks_by_celex", return_value=[{"text": "body"}]), \
         patch("evals.ground_truth.build_structured_agent", return_value=fake_agent):
        written = generate_ground_truth(
            _fake_config(), sample_size=1, questions_per_doc=2, output_path=out
        )

    assert written == 2
    records = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert records[0]["id"] == "A1-1"
    assert records[0]["celex_id"] == "A1"
    assert records[1]["question"] == "Q2;"
    assert records[1]["difficulty"] == "hard"

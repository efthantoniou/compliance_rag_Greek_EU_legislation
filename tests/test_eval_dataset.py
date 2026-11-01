import json

from pydantic_evals import Case

from evals.dataset import GroundTruthMeta, load_ground_truth, new_ground_truth_dataset


def _case() -> Case:
    return Case(
        name="A1-1",
        inputs="Ποια είναι η προθεσμία;",
        expected_output="Τρεις μήνες.",
        metadata=GroundTruthMeta(celex_id="A1", difficulty="easy"),
    )


def test_yaml_dataset_round_trips_greek_text_and_metadata(tmp_path):
    path = tmp_path / "gt.yaml"
    new_ground_truth_dataset([_case()]).to_file(path)

    loaded = load_ground_truth(path)

    assert "Ποια είναι η προθεσμία;" in path.read_text(encoding="utf-8")
    case = loaded.cases[0]
    assert case.name == "A1-1"
    assert case.inputs == "Ποια είναι η προθεσμία;"
    assert case.expected_output == "Τρεις μήνες."
    assert case.metadata == GroundTruthMeta(celex_id="A1", difficulty="easy")


def test_legacy_jsonl_ground_truth_still_loads(tmp_path):
    path = tmp_path / "gt.jsonl"
    path.write_text(
        json.dumps({
            "id": "A1-1", "celex_id": "A1", "question": "Q?",
            "expected_answer": "A.", "difficulty": "hard",
            "generated_at": "2026-07-07T00:00:00+00:00",
        }) + "\n\n",
        encoding="utf-8",
    )

    loaded = load_ground_truth(path)

    assert len(loaded.cases) == 1
    case = loaded.cases[0]
    assert (case.name, case.inputs, case.expected_output) == ("A1-1", "Q?", "A.")
    assert case.metadata == GroundTruthMeta(celex_id="A1", difficulty="hard")

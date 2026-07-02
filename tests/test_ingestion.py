import json
import zipfile
from unittest.mock import patch

from agent.ingestion.loader import load_documents


def _build_fixture_zip(path):
    lines = [
        {
            "celex_id": "A1",
            "text": {"el": "Ελληνικό κείμενο ένα", "en": "English one"},
            "eurovoc_concepts": {"level_1": ["100149"]},
        },
        {
            "celex_id": "A2",
            "text": {"de": "Deutscher Text"},
            "eurovoc_concepts": {"level_1": ["100160"]},
        },
        {
            "celex_id": "A3",
            "text": {"el": "Ελληνικό κείμενο τρία", "en": "English three"},
            "eurovoc_concepts": {"level_1": ["100148", "100147"]},
        },
    ]
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("train.jsonl", "\n".join(json.dumps(line) for line in lines))


def test_load_documents_skips_docs_without_greek_text(tmp_path):
    zip_path = tmp_path / "multi_eurlex_translated.zip"
    _build_fixture_zip(zip_path)

    with patch("agent.ingestion.loader.hf_hub_download", return_value=str(zip_path)):
        documents = load_documents(limit=10)

    assert [d.celex_id for d in documents] == ["A1", "A3"]
    assert documents[0].text == "Ελληνικό κείμενο ένα"
    assert documents[0].labels == ["100149"]
    assert documents[1].labels == ["100148", "100147"]


def test_load_documents_respects_limit(tmp_path):
    zip_path = tmp_path / "multi_eurlex_translated.zip"
    _build_fixture_zip(zip_path)

    with patch("agent.ingestion.loader.hf_hub_download", return_value=str(zip_path)):
        documents = load_documents(limit=1)

    assert [d.celex_id for d in documents] == ["A1"]


def test_load_documents_none_limit_loads_all(tmp_path):
    zip_path = tmp_path / "multi_eurlex_translated.zip"
    _build_fixture_zip(zip_path)

    with patch("agent.ingestion.loader.hf_hub_download", return_value=str(zip_path)):
        documents = load_documents(limit=None)

    assert [d.celex_id for d in documents] == ["A1", "A3"]

import pytest
from pydantic import ValidationError

from models import Chunk, Document


def test_document_holds_expected_fields():
    doc = Document(celex_id="A1", text="hello", labels=["100149"])
    assert doc.celex_id == "A1"
    assert doc.text == "hello"
    assert doc.labels == ["100149"]


def test_document_requires_all_fields():
    with pytest.raises(ValidationError):
        Document(celex_id="A1", text="hello")


def test_chunk_holds_expected_fields():
    chunk = Chunk(text="hello", celex_id="A1", labels=[])
    assert chunk.text == "hello"
    assert chunk.celex_id == "A1"
    assert chunk.labels == []


def test_chunk_requires_all_fields():
    with pytest.raises(ValidationError):
        Chunk(celex_id="A1", labels=[])

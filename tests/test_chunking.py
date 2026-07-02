from agent.ingestion.chunking import chunk_document
from models import Document


def _by_words(text: str) -> int:
    return len(text.split())


def test_short_text_single_chunk():
    doc = Document(celex_id="Y", text="a b c", labels=["100149"])

    chunks = chunk_document(doc, _by_words, chunk_tokens=500)

    assert len(chunks) == 1
    assert chunks[0].text == "a b c"
    assert chunks[0].celex_id == "Y"
    assert chunks[0].labels == ["100149"]
    assert chunks[0].chunk_index == 0


def test_paragraph_boundaries_preserved():
    doc = Document(celex_id="Z", text="para one here.\n\npara two here.", labels=[])

    chunks = chunk_document(doc, _by_words, chunk_tokens=500)

    assert len(chunks) == 1
    assert chunks[0].text == "para one here.\n\npara two here."


def test_paragraphs_packed_up_to_token_budget():
    doc = Document(celex_id="X", text="a b c\n\nd e f\n\ng h i", labels=[])

    chunks = chunk_document(doc, _by_words, chunk_tokens=6)

    assert [c.text for c in chunks] == ["a b c\n\nd e f", "g h i"]
    assert [c.chunk_index for c in chunks] == [0, 1]


def test_oversized_paragraph_is_split_by_words():
    doc = Document(
        celex_id="X",
        text=" ".join(f"w{i}" for i in range(10)),
        labels=["100149"],
    )

    chunks = chunk_document(doc, _by_words, chunk_tokens=4)

    assert [c.text for c in chunks] == ["w0 w1 w2 w3", "w4 w5 w6 w7", "w8 w9"]
    assert all(c.celex_id == "X" and c.labels == ["100149"] for c in chunks)


def test_empty_text_produces_no_chunks():
    doc = Document(celex_id="E", text="   \n\n  ", labels=[])

    assert chunk_document(doc, _by_words) == []

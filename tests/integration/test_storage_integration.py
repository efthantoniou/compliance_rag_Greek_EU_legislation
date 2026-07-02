import pytest

from config import Config
from models import Chunk
from agent.storage.surreal import fts_search, insert_chunks, reset_schema, vector_search

pytestmark = pytest.mark.integration


def _test_config() -> Config:
    return Config(
        surrealdb_url="ws://localhost:8000/rpc",
        surrealdb_user="root",
        surrealdb_pass="root",
        surrealdb_ns="test",
        surrealdb_db="test",
        llamacpp_url="http://localhost:8080/v1",
        llamacpp_model="test-model",
        ingest_limit=10,
    )


def test_insert_and_vector_search_roundtrip():
    config = _test_config()
    reset_schema(config)

    chunks = [
        Chunk(text="alpha document about tax law", celex_id="A1", labels=["100149"], chunk_index=0),
        Chunk(text="beta document about food safety", celex_id="A2", labels=["100160"], chunk_index=1),
    ]
    embeddings = [
        [1.0, 0.0] + [0.0] * 766,
        [0.0, 1.0] + [0.0] * 766,
    ]
    insert_chunks(config, chunks, embeddings)

    query_embedding = [1.0, 0.0] + [0.0] * 766
    results = vector_search(config, query_embedding, top_k=1)

    assert len(results) == 1
    assert results[0]["celex_id"] == "A1"
    assert results[0]["chunk_index"] == 0


def test_vector_search_respects_label_filter():
    config = _test_config()
    reset_schema(config)

    chunks = [
        Chunk(text="alpha document about tax law", celex_id="A1", labels=["100149"]),
        Chunk(text="near-duplicate alpha document", celex_id="A2", labels=["100160"]),
    ]
    embeddings = [
        [1.0, 0.0] + [0.0] * 766,
        [0.99, 0.01] + [0.0] * 766,
    ]
    insert_chunks(config, chunks, embeddings)

    query_embedding = [1.0, 0.0] + [0.0] * 766
    results = vector_search(config, query_embedding, top_k=5, label_filter="100160")

    assert len(results) == 1
    assert results[0]["celex_id"] == "A2"


def test_fts_search_finds_matching_chunk():
    config = _test_config()
    reset_schema(config)

    chunks = [
        Chunk(text="κανονισμός για τη φορολογία ακινήτων", celex_id="A1", labels=["100149"]),
        Chunk(text="οδηγία για την ασφάλεια τροφίμων", celex_id="A2", labels=["100160"]),
    ]
    embeddings = [
        [1.0, 0.0] + [0.0] * 766,
        [0.0, 1.0] + [0.0] * 766,
    ]
    insert_chunks(config, chunks, embeddings)

    results = fts_search(config, "φορολογία", top_k=5)

    assert any(r["celex_id"] == "A1" for r in results)

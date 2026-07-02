from unittest.mock import MagicMock, patch

import pytest

from config import Config
from models import Chunk
from agent.storage.surreal import (
    _run_query,
    chunks_by_celex,
    close_connections,
    count_chunks,
    fts_search,
    get_db,
    insert_chunks,
    list_celex_ids,
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


@pytest.fixture(autouse=True)
def _clean_connections():
    close_connections()
    yield
    close_connections()


def test_get_db_reuses_connection_for_same_config():
    config = _fake_config()
    with patch("agent.storage.surreal._connect", return_value=MagicMock()) as mock_connect:
        first = get_db(config)
        second = get_db(config)

    assert first is second
    mock_connect.assert_called_once_with(config)


def test_run_query_reconnects_once_on_failure():
    config = _fake_config()
    bad = MagicMock()
    bad.query.side_effect = RuntimeError("websocket closed")
    good = MagicMock()
    good.query.return_value = [{"ok": True}]

    with patch("agent.storage.surreal._connect", side_effect=[bad, good]):
        result = _run_query(config, "SELECT 1;", {})

    assert result == [{"ok": True}]
    bad.query.assert_called_once()
    good.query.assert_called_once()


def test_insert_chunks_batches_rows():
    config = _fake_config()
    chunks = [
        Chunk(text=f"t{i}", celex_id="A", labels=["100149"], chunk_index=i)
        for i in range(450)
    ]
    embeddings = [[0.0, 0.1]] * 450
    fake_db = MagicMock()

    with patch("agent.storage.surreal._connect", return_value=fake_db):
        insert_chunks(config, chunks, embeddings)

    assert fake_db.insert.call_count == 3  # 200 + 200 + 50
    first_table, first_batch = fake_db.insert.call_args_list[0].args
    assert first_table == "chunk"
    assert len(first_batch) == 200
    assert first_batch[0] == {
        "text": "t0",
        "celex_id": "A",
        "labels": ["100149"],
        "chunk_index": 0,
        "embedding": [0.0, 0.1],
    }


def test_list_celex_ids_returns_sorted_ids():
    config = _fake_config()
    rows = [{"celex_id": "B2"}, {"celex_id": "A1"}]
    with patch("agent.storage.surreal._run_query", return_value=rows) as mock_query:
        result = list_celex_ids(config)

    assert result == ["A1", "B2"]
    assert "GROUP BY celex_id" in mock_query.call_args.args[1]


def test_chunks_by_celex_orders_by_chunk_index():
    config = _fake_config()
    with patch("agent.storage.surreal._run_query", return_value=[]) as mock_query:
        chunks_by_celex(config, "A1", limit=5)

    sql = mock_query.call_args.args[1]
    assert "ORDER BY chunk_index" in sql
    assert "LIMIT 5" in sql
    assert mock_query.call_args.args[2] == {"celex_id": "A1"}


def test_count_chunks_returns_count_field():
    config = _fake_config()
    with patch("agent.storage.surreal._run_query", return_value=[{"count": 42}]) as mock_query:
        result = count_chunks(config)

    assert result == 42
    sql = mock_query.call_args.args[1]
    assert "count()" in sql
    assert "GROUP ALL" in sql


def test_count_chunks_empty_table_returns_zero():
    config = _fake_config()
    with patch("agent.storage.surreal._run_query", return_value=[]):
        assert count_chunks(config) == 0


def test_fts_search_uses_search_score_and_limit():
    config = _fake_config()
    with patch("agent.storage.surreal._run_query", return_value=[]) as mock_query:
        fts_search(config, "φορολογία ακινήτων", top_k=7)

    sql = mock_query.call_args.args[1]
    assert "@1@ $q" in sql
    assert "search::score(1)" in sql
    assert "LIMIT 7" in sql
    assert mock_query.call_args.args[2] == {"q": "φορολογία ακινήτων"}

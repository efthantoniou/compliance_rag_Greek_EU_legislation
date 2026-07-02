import threading

from surrealdb import Surreal

from config import Config
from models import Chunk

TABLE = "chunk"
EMBEDDING_DIM = 768

_local = threading.local()


def _connect(config: Config) -> Surreal:
    db = Surreal(config.surrealdb_url)
    db.signin({"username": config.surrealdb_user, "password": config.surrealdb_pass})
    db.use(config.surrealdb_ns, config.surrealdb_db)
    return db


def get_db(config: Config) -> Surreal:
    connections = getattr(_local, "connections", None)
    if connections is None:
        connections = _local.connections = {}
    db = connections.get(config)
    if db is None:
        db = connections[config] = _connect(config)
    return db


def close_connections() -> None:
    connections = getattr(_local, "connections", None) or {}
    for db in connections.values():
        try:
            db.close()
        except Exception:
            pass
    _local.connections = {}


def _run_query(config: Config, sql: str, query_vars: dict | None = None):
    # WebSocket connections go stale (server restart, idle timeout);
    # reconnect once before giving up.
    try:
        return get_db(config).query(sql, query_vars)
    except Exception:
        close_connections()
        return get_db(config).query(sql, query_vars)


def reset_schema(config: Config) -> None:
    _run_query(config, f"REMOVE TABLE IF EXISTS {TABLE};")
    _run_query(config, f"DEFINE TABLE {TABLE} SCHEMAFULL;")
    _run_query(config, f"DEFINE FIELD text ON {TABLE} TYPE string;")
    _run_query(config, f"DEFINE FIELD celex_id ON {TABLE} TYPE string;")
    _run_query(config, f"DEFINE FIELD labels ON {TABLE} TYPE array<string>;")
    _run_query(config, f"DEFINE FIELD chunk_index ON {TABLE} TYPE int;")
    _run_query(config, f"DEFINE FIELD embedding ON {TABLE} TYPE array<float>;")
    _run_query(
        config,
        f"DEFINE INDEX chunk_embedding_idx ON {TABLE} "
        f"FIELDS embedding HNSW DIMENSION {EMBEDDING_DIM};",
    )
    _run_query(
        config,
        "DEFINE ANALYZER OVERWRITE greek_text "
        "TOKENIZERS class FILTERS lowercase, snowball(greek);",
    )
    _run_query(
        config,
        f"DEFINE INDEX chunk_text_fts ON {TABLE} FIELDS text "
        f"FULLTEXT ANALYZER greek_text BM25;",
    )


_INSERT_BATCH_SIZE = 200


def insert_chunks(config: Config, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    rows = [
        {
            "text": chunk.text,
            "celex_id": chunk.celex_id,
            "labels": chunk.labels,
            "chunk_index": chunk.chunk_index,
            "embedding": embedding,
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]
    db = get_db(config)
    for i in range(0, len(rows), _INSERT_BATCH_SIZE):
        db.insert(TABLE, rows[i : i + _INSERT_BATCH_SIZE])


def count_chunks(config: Config) -> int:
    rows = _run_query(config, f"SELECT count() FROM {TABLE} GROUP ALL;")
    return rows[0]["count"] if rows else 0


def list_celex_ids(config: Config) -> list[str]:
    rows = _run_query(config, f"SELECT celex_id FROM {TABLE} GROUP BY celex_id;")
    return sorted(row["celex_id"] for row in rows)


def chunks_by_celex(config: Config, celex_id: str, limit: int = 20) -> list[dict]:
    sql = (
        f"SELECT text, celex_id, labels, chunk_index FROM {TABLE} "
        f"WHERE celex_id = $celex_id ORDER BY chunk_index LIMIT {int(limit)};"
    )
    return _run_query(config, sql, {"celex_id": celex_id})


def fts_search(
    config: Config,
    query_text: str,
    top_k: int,
    label_filter: str | None = None,
) -> list[dict]:
    where = "text @1@ $q"
    query_vars: dict = {"q": query_text}
    if label_filter is not None:
        where += " AND $label IN labels"
        query_vars["label"] = label_filter
    sql = (
        f"SELECT id, text, celex_id, labels, chunk_index, "
        f"search::score(1) AS score "
        f"FROM {TABLE} WHERE {where} ORDER BY score DESC LIMIT {int(top_k)};"
    )
    return _run_query(config, sql, query_vars)


def vector_search(
    config: Config,
    query_embedding: list[float],
    top_k: int,
    label_filter: str | None = None,
) -> list[dict]:
    where = f"embedding <|{top_k},40|> $vec"
    query_vars: dict = {"vec": query_embedding}
    if label_filter is not None:
        where += " AND $label IN labels"
        query_vars["label"] = label_filter
    sql = (
        f"SELECT id, text, celex_id, labels, chunk_index, "
        f"vector::distance::knn() AS distance "
        f"FROM {TABLE} WHERE {where} ORDER BY distance;"
    )
    return _run_query(config, sql, query_vars)

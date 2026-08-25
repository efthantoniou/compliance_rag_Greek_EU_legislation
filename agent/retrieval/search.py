from agent.ingestion.embeddings import Embedder
from agent.retrieval.reranker import rerank_chunks, rerank_chunks_scored
from agent.storage.surreal import fts_search, vector_search
from config import Config
from models import Chunk

RRF_K = 60
CANDIDATE_MULTIPLIER = 3


def _rrf_fuse(ranked_lists: list[list[dict]], top_k: int) -> list[dict]:
    scores: dict[str, float] = {}
    rows_by_id: dict[str, dict] = {}
    for rows in ranked_lists:
        for rank, row in enumerate(rows):
            rid = str(row["id"])
            rows_by_id[rid] = row
            scores[rid] = scores.get(rid, 0.0) + 1.0 / (RRF_K + rank + 1)
    ranked = sorted(scores, key=lambda rid: scores[rid], reverse=True)
    return [rows_by_id[rid] for rid in ranked[:top_k]]


def _row_to_chunk(row: dict) -> Chunk:
    return Chunk(
        text=row["text"],
        celex_id=row["celex_id"],
        # `or []` guards against rows from an older schema where these come back
        # as NULL rather than an empty array.
        labels=row.get("labels") or [],
        labels_l2=row.get("labels_l2") or [],
        labels_l3=row.get("labels_l3") or [],
        chunk_index=row.get("chunk_index", 0),
    )


def _candidates(
    config: Config,
    embedder: Embedder,
    query: str,
    top_k: int,
    label_filter: str | None,
    rerank: bool,
) -> list[Chunk]:
    query_embedding = embedder.embed_query(query)
    candidates = top_k * CANDIDATE_MULTIPLIER
    vector_rows = vector_search(
        config, query_embedding, top_k=candidates, label_filter=label_filter
    )
    fts_rows = fts_search(config, query, top_k=candidates, label_filter=label_filter)
    fused = _rrf_fuse([vector_rows, fts_rows], candidates if rerank else top_k)
    return [_row_to_chunk(row) for row in fused]


def search(
    config: Config,
    embedder: Embedder,
    query: str,
    top_k: int = 5,
    label_filter: str | None = None,
    rerank: bool = True,
) -> list[Chunk]:
    chunks = _candidates(config, embedder, query, top_k, label_filter, rerank)
    if rerank:
        chunks = rerank_chunks(
            query,
            chunks,
            top_n=top_k,
            model_name=config.reranker_model,
            device=config.reranker_device,
        )
    return chunks


def search_scored(
    config: Config,
    embedder: Embedder,
    query: str,
    top_k: int = 5,
    label_filter: str | None = None,
    rerank: bool = True,
) -> list[tuple[Chunk, float | None]]:
    """As search(), but each chunk carries its cross-encoder score.

    The score is None when reranking is disabled — there is no cross-encoder
    pass to produce one, and callers must not mistake that for a score of zero.
    """
    chunks = _candidates(config, embedder, query, top_k, label_filter, rerank)
    if not rerank:
        return [(chunk, None) for chunk in chunks]
    return list(
        rerank_chunks_scored(
            query,
            chunks,
            top_n=top_k,
            model_name=config.reranker_model,
            device=config.reranker_device,
        )
    )

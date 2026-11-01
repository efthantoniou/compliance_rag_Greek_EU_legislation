import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    surrealdb_url: str
    surrealdb_user: str
    surrealdb_pass: str
    surrealdb_ns: str
    surrealdb_db: str
    llamacpp_url: str
    llamacpp_model: str
    ingest_limit: int
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_device: str = "cpu"
    max_search_iters: int = 5
    # Search shows only results whose cross-encoder score (sigmoid-squashed to
    # [0, 1]) is at least this. Measured on this corpus (2026-08-25, n=28):
    # legitimate Greek queries score 0.75-0.99 at top-1, off-topic and nonsense
    # below 0.08; 0.55 also drops the tangential 0.10-0.50 band.
    retrieval_min_score: float = 0.55
    # Candidates retrieved and reranked per search query. Pages slice this one
    # ranked pool, so it also caps how many results a query can return.
    search_pool: int = 50
    # Optional separate llama.cpp server for the eval judge. When unset the judge
    # shares the RAG model, so swapping the RAG model (e.g. Q8_0 -> Q6_K) also
    # swaps the grader and the two runs' judge scores are not comparable.
    judge_llamacpp_url: str | None = None
    judge_llamacpp_model: str | None = None


def load_config() -> Config:
    llamacpp_model = os.environ.get("LLAMACPP_MODEL")
    if not llamacpp_model:
        raise RuntimeError(
            "LLAMACPP_MODEL environment variable is required "
            "(the model name/tag as served by llama.cpp)."
        )
    return Config(
        surrealdb_url=os.environ.get("SURREALDB_URL", "ws://localhost:8000/rpc"),
        surrealdb_user=os.environ.get("SURREALDB_USER", "root"),
        surrealdb_pass=os.environ.get("SURREALDB_PASS", "root"),
        surrealdb_ns=os.environ.get("SURREALDB_NS", "compliance"),
        surrealdb_db=os.environ.get("SURREALDB_DB", "compliance"),
        llamacpp_url=os.environ.get("LLAMACPP_URL", "http://localhost:8080/v1"),
        llamacpp_model=llamacpp_model,
        ingest_limit=int(os.environ.get("INGEST_LIMIT", "300")),
        reranker_model=os.environ.get("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"),
        reranker_device=os.environ.get("RERANKER_DEVICE", "cpu"),
        max_search_iters=int(os.environ.get("MAX_SEARCH_ITERS", "5")),
        retrieval_min_score=float(os.environ.get("RETRIEVAL_MIN_SCORE", "0.55")),
        search_pool=int(os.environ.get("SEARCH_POOL", "50")),
        judge_llamacpp_url=os.environ.get("JUDGE_LLAMACPP_URL") or None,
        judge_llamacpp_model=os.environ.get("JUDGE_LLAMACPP_MODEL") or None,
    )

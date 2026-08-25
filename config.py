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
    # Cross-encoder score bands. Scores are sigmoid-squashed to [0, 1].
    # Measured on this corpus (2026-08-25, n=28): legitimate Greek queries score
    # 0.75-0.99 at top-1, off-topic and nonsense queries score below 0.08, and
    # nothing landed in between. `min` drops individual junk results; `weak`
    # separates a confident answer from one that should carry a caveat.
    retrieval_min_score: float = 0.10
    retrieval_weak_score: float = 0.50


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
        retrieval_min_score=float(os.environ.get("RETRIEVAL_MIN_SCORE", "0.10")),
        retrieval_weak_score=float(os.environ.get("RETRIEVAL_WEAK_SCORE", "0.50")),
    )

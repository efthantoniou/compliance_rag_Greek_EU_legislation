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
    )

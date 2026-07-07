from dataclasses import dataclass

from agent.ingestion.embeddings import Embedder
from agent.retrieval import search
from config import Config
from models import Chunk


@dataclass
class AgentDeps:
    config: Config
    embedder: Embedder
    rerank: bool = True


def search_regulations(deps: AgentDeps, query: str, top_k: int = 5) -> list[Chunk]:
    return search(deps.config, deps.embedder, query, top_k=top_k, rerank=deps.rerank)

from dataclasses import dataclass

from pydantic_ai import RunContext

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


async def _search_regulations_tool(
    ctx: RunContext[AgentDeps], query: str, top_k: int = 5
) -> list[Chunk]:
    """Search the Greek/EU legislation corpus for passages relevant to `query`."""
    return search_regulations(ctx.deps, query, top_k=top_k)

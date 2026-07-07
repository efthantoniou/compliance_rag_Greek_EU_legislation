from unittest.mock import patch

from pydantic_ai import Agent

from agent import AgentDeps, search_regulations
from config import Config
from models import Chunk


def _test_config() -> Config:
    return Config(
        surrealdb_url="ws://localhost:8000/rpc",
        surrealdb_user="root",
        surrealdb_pass="root",
        surrealdb_ns="compliance",
        surrealdb_db="compliance",
        llamacpp_url="http://localhost:8080/v1",
        llamacpp_model="test-model",
        ingest_limit=10,
    )


def test_search_regulations_delegates_to_retrieval_search():
    deps = AgentDeps(config=object(), embedder=object())
    fake_chunks = [Chunk(text="t", celex_id="C1", labels=[])]

    with patch("agent.core.deps.search", return_value=fake_chunks) as mock_search:
        result = search_regulations(deps, "query text", top_k=3)

    mock_search.assert_called_once_with(
        deps.config, deps.embedder, "query text", top_k=3, rerank=True
    )
    assert result == fake_chunks


def test_build_planner_and_writer_agents():
    from agent.core.factory import build_planner_agent, build_writer_agent

    planner = build_planner_agent(_test_config(), "plan instructions")
    writer = build_writer_agent(_test_config(), "write instructions")
    assert isinstance(planner, Agent)
    assert isinstance(writer, Agent)

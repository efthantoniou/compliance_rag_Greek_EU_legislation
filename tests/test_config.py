import pytest

from config import load_config


def test_load_config_uses_defaults(monkeypatch):
    monkeypatch.delenv("SURREALDB_URL", raising=False)
    monkeypatch.delenv("SURREALDB_USER", raising=False)
    monkeypatch.delenv("SURREALDB_PASS", raising=False)
    monkeypatch.delenv("SURREALDB_NS", raising=False)
    monkeypatch.delenv("SURREALDB_DB", raising=False)
    monkeypatch.delenv("LLAMACPP_URL", raising=False)
    monkeypatch.delenv("INGEST_LIMIT", raising=False)
    monkeypatch.setenv("LLAMACPP_MODEL", "qwen-test")

    config = load_config()

    assert config.surrealdb_url == "ws://localhost:8000/rpc"
    assert config.surrealdb_user == "root"
    assert config.surrealdb_pass == "root"
    assert config.surrealdb_ns == "compliance"
    assert config.surrealdb_db == "compliance"
    assert config.llamacpp_url == "http://localhost:8080/v1"
    assert config.llamacpp_model == "qwen-test"
    assert config.ingest_limit == 300


def test_load_config_reads_env_overrides(monkeypatch):
    monkeypatch.setenv("SURREALDB_URL", "ws://db.example:9000/rpc")
    monkeypatch.setenv("INGEST_LIMIT", "42")
    monkeypatch.setenv("LLAMACPP_MODEL", "qwen-test")

    config = load_config()

    assert config.surrealdb_url == "ws://db.example:9000/rpc"
    assert config.ingest_limit == 42


def test_load_config_requires_llamacpp_model(monkeypatch):
    monkeypatch.delenv("LLAMACPP_MODEL", raising=False)

    with pytest.raises(RuntimeError):
        load_config()

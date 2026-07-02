from unittest.mock import MagicMock, patch

import click as _click
from click.testing import CliRunner

from main import cli
from config import Config
from models import Chunk, Document


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


def test_init_db_command_resets_schema_with_force():
    runner = CliRunner()

    with patch("main.load_config", return_value=_fake_config()), \
         patch("main.reset_schema") as mock_reset:
        result = runner.invoke(cli, ["init-db", "--force"])

    assert result.exit_code == 0, result.output
    mock_reset.assert_called_once()
    assert "Schema initialized" in result.output


def test_init_db_command_aborts_without_confirmation():
    runner = CliRunner()

    with patch("main.load_config", return_value=_fake_config()), \
         patch("main.reset_schema") as mock_reset:
        result = runner.invoke(cli, ["init-db"], input="n\n")

    assert result.exit_code != 0
    mock_reset.assert_not_called()


def test_stats_command_prints_counts():
    runner = CliRunner()

    with patch("main.load_config", return_value=_fake_config()), \
         patch("main.count_chunks", return_value=1270), \
         patch("main.list_celex_ids", return_value=["A1", "A2", "A3"]):
        result = runner.invoke(cli, ["stats"])

    assert result.exit_code == 0, result.output
    assert "1270" in result.output
    assert "3" in result.output


def test_ingest_command_runs_full_pipeline():
    runner = CliRunner()
    doc = Document(celex_id="A1", text="hello world", labels=["100149"])
    chunk = Chunk(text="hello world", celex_id="A1", labels=["100149"])

    with patch("main.load_config", return_value=_fake_config()), \
         patch("main.load_documents", return_value=[doc]) as mock_load, \
         patch("main.chunk_document", return_value=[chunk]), \
         patch("main.Embedder") as mock_embedder_cls, \
         patch("main.reset_schema") as mock_reset, \
         patch("main.insert_chunks") as mock_insert:
        mock_embedder_cls.from_pretrained.return_value.embed_passages.return_value = [[0.1, 0.2]]

        result = runner.invoke(cli, ["ingest", "--limit", "1"])

    assert result.exit_code == 0, result.output
    mock_load.assert_called_once_with(limit=1)
    mock_reset.assert_called_once()
    mock_insert.assert_called_once()
    assert "Ingest complete" in result.output


def test_search_command_prints_no_results_message():
    runner = CliRunner()

    with patch("main.load_config", return_value=_fake_config()), \
         patch("main.Embedder"), \
         patch("main.search", return_value=[]):
        result = runner.invoke(cli, ["search", "some query"])

    assert result.exit_code == 0, result.output
    assert "No relevant passages found." in result.output


def test_search_command_prints_results():
    runner = CliRunner()
    chunk = Chunk(text="relevant passage text", celex_id="A1", labels=["100149"])

    with patch("main.load_config", return_value=_fake_config()), \
         patch("main.Embedder"), \
         patch("main.search", return_value=[chunk]):
        result = runner.invoke(cli, ["search", "some query"])

    assert result.exit_code == 0, result.output
    assert "A1" in result.output
    assert "relevant passage text" in result.output


def test_ask_command_prints_agent_output():
    runner = CliRunner()
    fake_agent = MagicMock()
    fake_agent.run_sync.return_value.output = "Here is the answer with citation CELEX:A1."

    with patch("main.load_config", return_value=_fake_config()), \
         patch("main._check_llamacpp_reachable"), \
         patch("main.Embedder"), \
         patch("main.build_ask_agent", return_value=fake_agent):
        result = runner.invoke(cli, ["ask", "what are the rules?"])

    assert result.exit_code == 0, result.output
    assert "Here is the answer" in result.output


def test_ask_command_fails_loudly_when_llamacpp_unreachable():
    runner = CliRunner()

    with patch("main.load_config", return_value=_fake_config()), \
         patch("main._check_llamacpp_reachable", side_effect=_click.ClickException("unreachable")):
        result = runner.invoke(cli, ["ask", "what are the rules?"])

    assert result.exit_code != 0
    assert "unreachable" in result.output


def test_check_command_reads_file_and_prints_agent_output(tmp_path):
    runner = CliRunner()
    policy_file = tmp_path / "policy.txt"
    policy_file.write_text("We process personal data for marketing.", encoding="utf-8")
    fake_agent = MagicMock()
    fake_agent.run_sync.return_value.output = "Topic: data processing -> CELEX:A1"

    with patch("main.load_config", return_value=_fake_config()), \
         patch("main._check_llamacpp_reachable"), \
         patch("main.Embedder"), \
         patch("main.build_check_agent", return_value=fake_agent):
        result = runner.invoke(cli, ["check", str(policy_file)])

    assert result.exit_code == 0, result.output
    assert "Topic: data processing" in result.output

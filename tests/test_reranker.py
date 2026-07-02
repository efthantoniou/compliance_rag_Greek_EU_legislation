from unittest.mock import MagicMock, patch

from models import Chunk
from agent.retrieval.reranker import rerank_chunks


def _chunks(*texts):
    return [Chunk(text=t, celex_id="A1", labels=[]) for t in texts]


def test_rerank_orders_by_score_and_truncates():
    fake_model = MagicMock()
    fake_model.predict.return_value = [0.1, 0.9, 0.5]

    with patch("agent.retrieval.reranker._load", return_value=fake_model):
        result = rerank_chunks("q", _chunks("a", "b", "c"), top_n=2, model_name="m")

    assert [c.text for c in result] == ["b", "c"]
    fake_model.predict.assert_called_once_with(
        [("q", "a"), ("q", "b"), ("q", "c")], show_progress_bar=False
    )


def test_rerank_empty_input_returns_empty_without_loading_model():
    with patch("agent.retrieval.reranker._load") as mock_load:
        assert rerank_chunks("q", [], top_n=5, model_name="m") == []
    mock_load.assert_not_called()

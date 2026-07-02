from unittest.mock import MagicMock, patch

from models import Chunk
from agent.retrieval.search import _rrf_fuse, search


class _FakeEmbedder:
    def embed_query(self, text):
        return [0.1, 0.2]


def _row(rid, text):
    return {"id": rid, "text": text, "celex_id": "A1", "labels": [], "chunk_index": 0}


def test_rrf_fuse_boosts_results_in_both_lists():
    shared, vec_only, fts_only = _row("c:1", "s"), _row("c:2", "v"), _row("c:3", "f")

    fused = _rrf_fuse([[vec_only, shared], [fts_only, shared]], top_k=3)

    assert fused[0]["id"] == "c:1"  # appears in both lists → highest RRF score
    assert {r["id"] for r in fused} == {"c:1", "c:2", "c:3"}


def test_rrf_fuse_truncates_to_top_k():
    rows = [_row(f"c:{i}", f"t{i}") for i in range(5)]

    assert len(_rrf_fuse([rows, []], top_k=2)) == 2


def test_search_fuses_vector_and_fts():
    config = object()
    embedder = _FakeEmbedder()
    vec_rows = [_row("c:1", "alpha")]
    fts_rows = [_row("c:2", "beta")]

    with patch("agent.retrieval.search.vector_search", return_value=vec_rows) as mock_vec, \
         patch("agent.retrieval.search.fts_search", return_value=fts_rows) as mock_fts:
        results = search(config, embedder, "tax law", top_k=2, rerank=False)

    mock_vec.assert_called_once_with(config, [0.1, 0.2], top_k=6, label_filter=None)
    mock_fts.assert_called_once_with(config, "tax law", top_k=6, label_filter=None)
    assert all(isinstance(c, Chunk) for c in results)
    assert {c.text for c in results} == {"alpha", "beta"}


def test_search_returns_empty_when_no_rows():
    with patch("agent.retrieval.search.vector_search", return_value=[]), \
         patch("agent.retrieval.search.fts_search", return_value=[]):
        assert search(object(), _FakeEmbedder(), "tax law", rerank=False) == []


def test_search_reranks_when_enabled():
    config = MagicMock()
    config.reranker_model = "m"
    config.reranker_device = "cpu"
    rows = [_row("c:1", "alpha"), _row("c:2", "beta")]
    reranked = [Chunk(text="beta", celex_id="A1", labels=[])]

    with patch("agent.retrieval.search.vector_search", return_value=rows), \
         patch("agent.retrieval.search.fts_search", return_value=[]), \
         patch("agent.retrieval.search.rerank_chunks", return_value=reranked) as mock_rerank:
        results = search(config, _FakeEmbedder(), "tax law", top_k=1)

    assert results == reranked
    kwargs = mock_rerank.call_args.kwargs
    assert kwargs["top_n"] == 1
    assert kwargs["model_name"] == "m"

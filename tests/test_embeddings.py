from unittest.mock import MagicMock

from agent.ingestion.embeddings import Embedder


class _FakeArray(list):
    def tolist(self):
        return list(self)


class _FakeModel:
    def __init__(self):
        self.calls = []

    def encode(self, inputs, normalize_embeddings=True):
        self.calls.append(inputs)
        if isinstance(inputs, str):
            return _FakeArray([0.1, 0.2])
        return _FakeArray([[0.1, 0.2] for _ in inputs])


def test_embed_passages_adds_passage_prefix():
    model = _FakeModel()
    embedder = Embedder(model)

    result = embedder.embed_passages(["alpha", "beta"])

    assert model.calls == [["passage: alpha", "passage: beta"]]
    assert result == [[0.1, 0.2], [0.1, 0.2]]


def test_embed_query_adds_query_prefix():
    model = _FakeModel()
    embedder = Embedder(model)

    result = embedder.embed_query("what is x")

    assert model.calls == ["query: what is x"]
    assert result == [0.1, 0.2]


def test_count_tokens_uses_model_tokenizer():
    fake_model = MagicMock()
    fake_model.tokenizer.return_value = {"input_ids": [1, 2, 3]}
    embedder = Embedder(fake_model)

    assert embedder.count_tokens("some text") == 3
    fake_model.tokenizer.assert_called_once_with("some text", add_special_tokens=False)

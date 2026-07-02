from sentence_transformers import SentenceTransformer

DEFAULT_MODEL_NAME = "intfloat/multilingual-e5-base"


class Embedder:
    def __init__(self, model):
        self._model = model

    @classmethod
    def from_pretrained(cls, model_name: str = DEFAULT_MODEL_NAME) -> "Embedder":
        return cls(SentenceTransformer(model_name))

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        prefixed = [f"passage: {text}" for text in texts]
        return self._model.encode(prefixed, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(f"query: {text}", normalize_embeddings=True).tolist()

    def count_tokens(self, text: str) -> int:
        return len(self._model.tokenizer(text, add_special_tokens=False)["input_ids"])

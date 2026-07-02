from functools import lru_cache

from sentence_transformers import CrossEncoder

from models import Chunk

DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


@lru_cache(maxsize=1)
def _load(model_name: str, device: str = "cpu") -> CrossEncoder:
    return CrossEncoder(model_name, device=device, max_length=512)


def rerank_chunks(
    query: str,
    chunks: list[Chunk],
    top_n: int,
    model_name: str,
    device: str = "cpu",
) -> list[Chunk]:
    if not chunks:
        return []
    model = _load(model_name, device)
    scores = model.predict([(query, c.text) for c in chunks], show_progress_bar=False)
    ranked = sorted(zip(chunks, scores), key=lambda pair: float(pair[1]), reverse=True)
    return [chunk for chunk, _ in ranked[:top_n]]

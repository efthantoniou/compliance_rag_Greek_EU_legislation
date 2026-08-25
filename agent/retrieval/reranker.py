from functools import lru_cache

from sentence_transformers import CrossEncoder

from models import Chunk

DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


@lru_cache(maxsize=1)
def _load(model_name: str, device: str = "cpu") -> CrossEncoder:
    return CrossEncoder(model_name, device=device, max_length=512)


def rerank_chunks_scored(
    query: str,
    chunks: list[Chunk],
    top_n: int,
    model_name: str,
    device: str = "cpu",
) -> list[tuple[Chunk, float]]:
    """Rerank and keep the cross-encoder score alongside each chunk.

    The score is what separates a real hit from a passage that merely came back
    because vector search always returns its top_k. Scores are sigmoid-squashed
    to [0, 1] by the CrossEncoder, so they compare directly against the
    thresholds in Config.
    """
    if not chunks:
        return []
    model = _load(model_name, device)
    scores = model.predict([(query, c.text) for c in chunks], show_progress_bar=False)
    ranked = sorted(zip(chunks, scores), key=lambda pair: float(pair[1]), reverse=True)
    return [(chunk, float(score)) for chunk, score in ranked[:top_n]]


def rerank_chunks(
    query: str,
    chunks: list[Chunk],
    top_n: int,
    model_name: str,
    device: str = "cpu",
) -> list[Chunk]:
    """Score-free view of rerank_chunks_scored, for callers that only want order."""
    return [
        chunk
        for chunk, _ in rerank_chunks_scored(
            query, chunks, top_n=top_n, model_name=model_name, device=device
        )
    ]

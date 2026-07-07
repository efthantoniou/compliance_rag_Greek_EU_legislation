from collections.abc import Callable

from models import Chunk, Document

# multilingual-e5-base truncates at 512 tokens; leave headroom for the
# "passage: " prefix and the special tokens added at embed time.
DEFAULT_CHUNK_TOKENS = 480


def chunk_document(
    doc: Document,
    count_tokens: Callable[[str], int],
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
) -> list[Chunk]:
    paragraphs = [p.strip() for p in doc.text.split("\n\n") if p.strip()]

    pieces: list[tuple[str, int]] = []
    for paragraph in paragraphs:
        tokens = count_tokens(paragraph)
        if tokens <= chunk_tokens:
            pieces.append((paragraph, tokens))
        else:
            pieces.extend(_split_paragraph(paragraph, count_tokens, chunk_tokens))

    chunks: list[Chunk] = []
    current: list[str] = []
    current_tokens = 0
    for text, tokens in pieces:
        if current and current_tokens + tokens > chunk_tokens:
            chunks.append(_make_chunk(doc, current, len(chunks)))
            current, current_tokens = [], 0
        current.append(text)
        current_tokens += tokens
    if current:
        chunks.append(_make_chunk(doc, current, len(chunks)))
    return chunks


def _make_chunk(doc: Document, paragraphs: list[str], index: int) -> Chunk:
    return Chunk(
        text="\n\n".join(paragraphs),
        celex_id=doc.celex_id,
        labels=doc.labels,
        labels_l2=doc.labels_l2,
        labels_l3=doc.labels_l3,
        chunk_index=index,
    )


def _split_paragraph(
    paragraph: str,
    count_tokens: Callable[[str], int],
    chunk_tokens: int,
) -> list[tuple[str, int]]:
    # Per-word token sums slightly overestimate the joined text's count for
    # subword tokenizers — errs on the safe (under-budget) side.
    pieces: list[tuple[str, int]] = []
    current: list[str] = []
    current_tokens = 0
    for word in paragraph.split():
        tokens = count_tokens(word)
        if current and current_tokens + tokens > chunk_tokens:
            pieces.append((" ".join(current), current_tokens))
            current, current_tokens = [], 0
        current.append(word)
        current_tokens += tokens
    if current:
        pieces.append((" ".join(current), current_tokens))
    return pieces

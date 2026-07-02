from pydantic import BaseModel


class Document(BaseModel):
    celex_id: str
    text: str
    labels: list[str]


class Chunk(BaseModel):
    text: str
    celex_id: str
    labels: list[str]
    chunk_index: int = 0


__all__ = ["Document", "Chunk"]

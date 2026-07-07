from pydantic import BaseModel


class Document(BaseModel):
    celex_id: str
    text: str
    labels: list[str]  # EUROVOC level_1 concept IDs (broad domains)
    labels_l2: list[str] = []  # level_2 (microthesauri)
    labels_l3: list[str] = []  # level_3 (specific concepts)


class Chunk(BaseModel):
    text: str
    celex_id: str
    labels: list[str]  # EUROVOC level_1 concept IDs (broad domains)
    labels_l2: list[str] = []  # level_2 (microthesauri)
    labels_l3: list[str] = []  # level_3 (specific concepts)
    chunk_index: int = 0


__all__ = ["Document", "Chunk"]

from typing import Literal

from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    label: str | None = None


class Concept(BaseModel):
    id: str
    el: str
    en: str


class SearchResult(BaseModel):
    celex_id: str
    labels: list[Concept]  # EUROVOC level_1 (broad domains)
    subtopics: list[Concept]  # level_2 (microthesauri)
    topics: list[Concept]  # level_3 (specific concepts)
    text: str
    # Cross-encoder relevance in [0, 1]. None when reranking was disabled.
    score: float | None = None


# How much the corpus actually had to say. The UI renders these differently:
# grounded is a normal result list, weak carries a caveat, refused is a
# first-class state rather than an empty list.
RetrievalStatus = Literal["grounded", "weak", "refused"]


class SearchResponse(BaseModel):
    results: list[SearchResult]
    status: RetrievalStatus = "grounded"
    # Best score before filtering, so the UI can show why it refused.
    top_score: float | None = None


class LabelsResponse(BaseModel):
    labels: list[Concept]  # the 21 level_1 domains, for the filter dropdown


class AskRequest(BaseModel):
    question: str


class CheckRequest(BaseModel):
    document: str

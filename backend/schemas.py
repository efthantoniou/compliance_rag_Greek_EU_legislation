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


class SearchResponse(BaseModel):
    results: list[SearchResult]


class LabelsResponse(BaseModel):
    labels: list[Concept]  # the 21 level_1 domains, for the filter dropdown


class AskRequest(BaseModel):
    question: str


class CheckRequest(BaseModel):
    document: str

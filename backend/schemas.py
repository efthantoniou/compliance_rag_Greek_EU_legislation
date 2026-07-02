from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    label: str | None = None


class SearchResult(BaseModel):
    celex_id: str
    labels: list[str]
    text: str


class SearchResponse(BaseModel):
    results: list[SearchResult]


class AskRequest(BaseModel):
    question: str


class CheckRequest(BaseModel):
    document: str

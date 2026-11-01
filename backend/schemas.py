from typing import Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=50)
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
    # Cross-encoder relevance in [0, 1] of this, the document's best passage.
    score: float | None = None
    # How many of the document's passages cleared the threshold (search shows
    # each document once, with its best passage).
    matches: int = 1


# How much the corpus actually had to say. Search only shows results at or above
# Config.retrieval_min_score, so either something clears it (grounded) or the
# corpus has nothing on this (refused, a first-class state, not an empty list).
RetrievalStatus = Literal["grounded", "refused"]


class SearchResponse(BaseModel):
    results: list[SearchResult]  # this page only
    status: RetrievalStatus = "grounded"
    # Best score before filtering, so the UI can show why it refused.
    top_score: float | None = None
    total: int = 0  # results above the threshold, across all pages
    page: int = 1
    page_size: int = 10


class LabelsResponse(BaseModel):
    labels: list[Concept]  # the 21 level_1 domains, for the filter dropdown


class AskRequest(BaseModel):
    question: str


class CheckRequest(BaseModel):
    document: str

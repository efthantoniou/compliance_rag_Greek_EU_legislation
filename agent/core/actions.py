"""Discriminated-union actions for the prompted-output tool loop.

The planner agent returns exactly one of these per turn: a SearchAction to
retrieve more passages, or Done when it has enough context to answer.
"""

from pydantic import BaseModel, Field


class SearchAction(BaseModel):
    """Retrieve passages from the legislation corpus for `query`."""

    query: str = Field(description="A search query, in Greek, for the legislation corpus.")
    top_k: int = 5


class Done(BaseModel):
    """Signals that enough context has been gathered to write the answer."""

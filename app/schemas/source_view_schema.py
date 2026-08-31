from __future__ import annotations

from pydantic import BaseModel, Field


class SourceWord(BaseModel):
    text: str
    x: float
    y: float
    width: float
    height: float
    block: int
    line: int
    word: int


class HighlightRect(BaseModel):
    x: float
    y: float
    width: float
    height: float


class SourcePage(BaseModel):
    page: int
    width: float
    height: float
    words: list[SourceWord] = Field(default_factory=list)
    highlights: list[HighlightRect] = Field(default_factory=list)


class EvidenceViewRequest(BaseModel):
    pages: list[int] = Field(min_length=1)
    text: str = Field(min_length=1)


class EvidenceViewResponse(BaseModel):
    source_id: str
    source_pages: list[int]
    pdf_pages: list[int]
    display_pages: list[int]
    pages: list[SourcePage]
    highlight_found: bool
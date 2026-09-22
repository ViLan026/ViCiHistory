from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.config import settings


class EvidenceMapRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 5:
            raise ValueError("'content' must be at least 5 characters long.")

        if len(value) > settings.MAX_INPUT_CHARS:
            raise ValueError(f"'content' must not exceed {settings.MAX_INPUT_CHARS} characters.")

        return value


class EvidenceItem(BaseModel):
    chunk_id: str | None = None
    score: float | None = None
    book_name: str | None = None
    source_id: str | None = None
    pages: list[int] = Field(default_factory=list)
    pdf_pages: list[int] = Field(default_factory=list)
    text: str
    headers: dict[str, str] | None = None
    footnotes: dict[str, Any] | None = None
    token_count: int | None = None


class ExtractedClaim(BaseModel):
    source_text: str
    claim: str

    @field_validator("source_text", "claim")
    @classmethod
    def text_not_empty(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Claim text must not be empty.")

        return value


class ClaimExtractionOutput(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)


class ClaimEvidenceResult(BaseModel):
    id: str
    source_text: str
    claim: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class EvidenceMapResponse(BaseModel):
    claims: list[ClaimEvidenceResult] = Field(default_factory=list)


class PdfExcerptRequest(BaseModel):
    pdf_pages: list[int] = Field(min_length=1, max_length=3)
    text: str

    @field_validator("pdf_pages")
    @classmethod
    def validate_pdf_pages(cls, value: list[int]) -> list[int]:
        pages = sorted(set(value))

        if not pages or any(page < 1 for page in pages):
            raise ValueError("'pdf_pages' must contain page numbers >= 1.")

        return pages

    @field_validator("text")
    @classmethod
    def excerpt_text_not_empty(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("'text' must not be empty.")

        return value
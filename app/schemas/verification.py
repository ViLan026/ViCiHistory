from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.config import settings


class VerificationLabel(str, Enum):
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    NOT_ENOUGH_EVIDENCE = "NOT_ENOUGH_EVIDENCE"


class VerifyRequest(BaseModel):
    content: str = Field(..., min_length=5)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("'content' must be at least 5 characters long.")
        if len(value) > settings.MAX_INPUT_CHARS:
            raise ValueError(
                f"'content' must not exceed {settings.MAX_INPUT_CHARS} characters."
            )
        return value


class EvidenceItem(BaseModel):
    chunk_id: str | None = None
    score: float | None = None
    book_name: str | None = None
    pages: list[int] = Field(default_factory=list)

    text: str

    headers: dict[str, str] | None = None
    footnotes: dict[str, Any] | None = None
    # token_count: int | None = None

class ClaimResult(BaseModel):
    id: str
    source_text: str
    claim: str
    label: VerificationLabel
    explanation: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class VerifyResponse(BaseModel):
    claims: list[ClaimResult] = Field(default_factory=list)


# Structured Gemini outputs
class ExtractedClaim(BaseModel):
    source_text: str
    claim: str

    @field_validator("source_text", "claim")
    @classmethod
    def text_not_empty(cls, value: str) -> str:
        value = " ".join(value.split()).strip()
        if not value:
            raise ValueError("Claim fields must not be empty.")
        return value


class ClaimExtractionOutput(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)


class ClaimVerificationOutput(BaseModel):
    label: VerificationLabel
    explanation: str

    @field_validator("explanation")
    @classmethod
    def explanation_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("'explanation' must not be empty.")
        return value

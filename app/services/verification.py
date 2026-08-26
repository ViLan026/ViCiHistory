from __future__ import annotations

import logging
import re

from app.config import settings
from app.prompts.claim_extraction import build_claim_extraction_prompt
from app.schemas.verification import (
    ClaimEvidenceResult,
    EvidenceMapResponse,
    ExtractedClaim,
)
from app.services.gemini import GeminiService
from app.services.retrieval import RetrievalService

logger = logging.getLogger(__name__)

_WHITESPACE_PATTERN = re.compile(r"\s+")
_END_PUNCTUATION_PATTERN = re.compile(r"[.!?…]+$")


class VerificationService:
    def __init__(
        self,
        gemini_service: GeminiService,
        retrieval_service: RetrievalService,
    ) -> None:
        self._gemini_service = gemini_service
        self._retrieval_service = retrieval_service

    @staticmethod
    def _normalize_claim_key(claim: str) -> str:
        normalized = _WHITESPACE_PATTERN.sub(" ", claim.strip())
        normalized = _END_PUNCTUATION_PATTERN.sub("", normalized)

        return normalized.casefold()

    def extract_claims(self, content: str) -> list[ExtractedClaim]:
        prompt = build_claim_extraction_prompt(content)
        output = self._gemini_service.extract_claims(prompt)

        seen: set[str] = set()
        claims: list[ExtractedClaim] = []

        for item in output.claims:
            claim = _WHITESPACE_PATTERN.sub(" ", item.claim.strip())
            source_text = item.source_text.strip()

            if not claim or not source_text:
                continue

            normalized_key = self._normalize_claim_key(claim)

            if not normalized_key or normalized_key in seen:
                continue

            seen.add(normalized_key)

            claims.append(
                ExtractedClaim(
                    source_text=source_text,
                    claim=claim,
                )
            )

            if len(claims) >= settings.MAX_CLAIMS_PER_INPUT:
                break

        logger.info("Extracted %d historical claim(s).", len(claims))

        return claims

    def build_evidence_map(self, content: str) -> EvidenceMapResponse:
        extracted_claims = self.extract_claims(content)

        if not extracted_claims:
            return EvidenceMapResponse(claims=[])

        results: list[ClaimEvidenceResult] = []

        for index, item in enumerate(extracted_claims, start=1):
            logger.info("Retrieving evidence for claim: %s", item.claim[:100])

            evidence = self._retrieval_service.retrieve(item.claim)

            results.append(
                ClaimEvidenceResult(
                    id=f"claim_{index}",
                    source_text=item.source_text,
                    claim=item.claim,
                    evidence=evidence,
                )
            )

        return EvidenceMapResponse(claims=results)
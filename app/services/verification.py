from __future__ import annotations

import logging
import re

from app.config import settings
from app.prompts.claim_extraction import build_claim_extraction_prompt
from app.prompts.verification import build_verification_prompt
from app.schemas.verification import (
    ClaimResult,
    ExtractedClaim,
    VerificationLabel,
    VerifyResponse,
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
    def _claim_key(claim: str) -> str:
        value = _WHITESPACE_PATTERN.sub(" ", claim.strip())
        value = _END_PUNCTUATION_PATTERN.sub("", value)
        return value.casefold()

    def extract_claims(self, content: str) -> list[ExtractedClaim]:
        output = self._gemini_service.extract_claims(
            build_claim_extraction_prompt(content)
        )

        seen: set[str] = set()
        results: list[ExtractedClaim] = []

        for item in output.claims:
            claim = _WHITESPACE_PATTERN.sub(" ", item.claim.strip())
            source_text = _WHITESPACE_PATTERN.sub(" ", item.source_text.strip())
            key = self._claim_key(claim)

            if not claim or not source_text or not key or key in seen:
                continue

            seen.add(key)
            results.append(ExtractedClaim(source_text=source_text, claim=claim))

            if len(results) >= settings.MAX_CLAIMS_PER_INPUT:
                break

        return results

    @staticmethod
    def _format_evidence_for_prompt(evidence) -> str:
        sections: list[str] = []

        for index, item in enumerate(evidence, start=1):
            text = item.text.strip()[: settings.MAX_EVIDENCE_CHARS]
            if not text:
                continue

            book_name = item.book_name or "Không rõ tên sách"
            pages = ", ".join(str(page) for page in item.pages) if item.pages else "Không xác định"

            sections.append(
                "\n".join(
                    [
                        f"<EVIDENCE_{index}>",
                        f"Sách: {book_name}",
                        f"Trang: {pages}",
                        "Nội dung:",
                        text,
                        f"</EVIDENCE_{index}>",
                    ]
                )
            )

        return "\n\n".join(sections)

    def _check_claim(self, item: ExtractedClaim, claim_id: str) -> ClaimResult:
        evidence = self._retrieval_service.retrieve(item.claim)

        if not evidence:
            return ClaimResult(
                id=claim_id,
                source_text=item.source_text,
                claim=item.claim,
                label=VerificationLabel.NOT_ENOUGH_EVIDENCE,
                explanation=(
                    "Chưa có đủ thông tin trong nguồn sử liệu hiện có để xác nhận "
                    "hoặc bác bỏ nội dung này."
                ),
                evidence=[],
            )

        evidence_text = self._format_evidence_for_prompt(evidence)
        if not evidence_text:
            return ClaimResult(
                id=claim_id,
                source_text=item.source_text,
                claim=item.claim,
                label=VerificationLabel.NOT_ENOUGH_EVIDENCE,
                explanation=(
                    "Chưa có đủ thông tin trong nguồn sử liệu hiện có để xác nhận "
                    "hoặc bác bỏ nội dung này."
                ),
                evidence=[],
            )

        verification = self._gemini_service.verify_claim(
            build_verification_prompt(item.claim, evidence_text)
        )

        return ClaimResult(
            id=claim_id,
            source_text=item.source_text,
            claim=item.claim,
            label=verification.label,
            explanation=verification.explanation.strip(),
            evidence=evidence,
        )

    def verify(self, content: str) -> VerifyResponse:
        extracted = self.extract_claims(content)
        if not extracted:
            return VerifyResponse(claims=[])

        claims: list[ClaimResult] = []
        for index, item in enumerate(extracted, start=1):
            logger.info("Verifying claim %d/%d", index, len(extracted))
            claims.append(self._check_claim(item, f"claim_{index}"))

        return VerifyResponse(claims=claims)

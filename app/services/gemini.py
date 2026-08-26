from __future__ import annotations

import logging
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.exceptions import GeminiServiceError
from app.schemas.verification import (
    ClaimExtractionOutput,
    ClaimVerificationOutput,
)

logger = logging.getLogger(__name__)
ModelT = TypeVar("ModelT", bound=BaseModel)


class GeminiService:
    def __init__(self) -> None:
        self._client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(
                timeout=settings.GEMINI_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(
                    attempts=settings.GEMINI_MAX_RETRIES + 1,
                ),
            ),
        )
        logger.info("Gemini client initialized. model=%s", settings.GEMINI_MODEL)

    def extract_claims(self, prompt: str) -> ClaimExtractionOutput:
        return self._generate_structured(
            prompt=prompt,
            response_model=ClaimExtractionOutput,
            operation="claim_extraction",
        )

    def verify_claim(self, prompt: str) -> ClaimVerificationOutput:
        return self._generate_structured(
            prompt=prompt,
            response_model=ClaimVerificationOutput,
            operation="claim_verification",
        )

    def _generate_structured(
        self,
        *,
        prompt: str,
        response_model: type[ModelT],
        operation: str,
    ) -> ModelT:
        prompt = prompt.strip()
        if not prompt:
            raise GeminiServiceError(
                "Gemini prompt must not be empty.",
                operation=operation,
            )

        try:
            response = self._client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=settings.GEMINI_TEMPERATURE,
                    max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
                    response_mime_type="application/json",
                    response_json_schema=response_model.model_json_schema(),
                ),
            )
        except Exception as exc:
            logger.exception("Gemini request failed. operation=%s", operation)
            raise GeminiServiceError(
                "Gemini request failed.",
                operation=operation,
            ) from exc

        try:
            response_text = (response.text or "").strip()
            if not response_text:
                raise ValueError("Gemini returned an empty response.")
            return response_model.model_validate_json(response_text)
        except (ValidationError, ValueError, TypeError) as exc:
            logger.exception(
                "Gemini returned invalid structured output. operation=%s",
                operation,
            )
            raise GeminiServiceError(
                "Gemini returned invalid structured output.",
                operation=operation,
            ) from exc

    def close(self) -> None:
        try:
            self._client.close()
            logger.info("Gemini client closed.")
        except Exception:
            logger.exception("Failed to close Gemini client cleanly.")

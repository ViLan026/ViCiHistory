from __future__ import annotations

import logging

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.config import settings
from app.exceptions import LLMServiceError
from app.schemas.evidence import ClaimExtractionOutput

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self) -> None:
        self._client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
        )
        self._model = settings.GEMINI_MODEL

    def extract_claims(
        self,
        prompt: str,
    ) -> ClaimExtractionOutput:
        prompt = prompt.strip()

        if not prompt:
            raise LLMServiceError(
                "Gemini prompt must not be empty.",
                operation="claim_extraction",
            )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema=ClaimExtractionOutput,
                ),
            )

            if not response.text:
                raise ValueError("Gemini returned an empty response.")

            return ClaimExtractionOutput.model_validate_json(
                response.text,
            )

        except (ValidationError, ValueError) as exc:
            logger.exception("Gemini response validation failed.")

            raise LLMServiceError(
                "Gemini returned an invalid response.",
                operation="claim_extraction",
            ) from exc

        except Exception as exc:
            logger.exception("Gemini request failed.")

            raise LLMServiceError(
                "Gemini request failed.",
                operation="claim_extraction",
            ) from exc

    def close(self) -> None:
        self._client.close()
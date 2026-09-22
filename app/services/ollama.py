# prompt -> HTTP request -> Ollama -> Qwen2.5-3B -> JSON -> Pydantic

from __future__ import annotations

import logging
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.exceptions import LLMServiceError
from app.schemas.evidence import ClaimExtractionOutput

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class OllamaService:
    def __init__(self) -> None:
        base_url = settings.OLLAMA_URL.rstrip("/")

        self._client = httpx.Client(
            base_url=base_url,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        )

        logger.info(
            "Ollama client initialized. url=%s model=%s",
            base_url,
            settings.OLLAMA_MODEL,
        )

    def extract_claims(self, prompt: str) -> ClaimExtractionOutput:
        return self._generate_structured(
            prompt=prompt,
            response_model=ClaimExtractionOutput,
            operation="claim_extraction",
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
            raise LLMServiceError(
                "Ollama prompt must not be empty.",
                operation=operation,
            )

        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
            "format": response_model.model_json_schema(),
            "options": {
                "temperature": settings.OLLAMA_TEMPERATURE,
            },
        }

        total_attempts = settings.OLLAMA_MAX_RETRIES + 1
        last_exception: Exception | None = None

        for attempt in range(1, total_attempts + 1):
            try:
                response = self._client.post("/api/chat", json=payload)
                response.raise_for_status()

                response_data = response.json()

                message = response_data.get("message")

                if not isinstance(message, dict):
                    raise ValueError("Ollama response does not contain a valid message.")

                response_text = str(message.get("content") or "").strip()

                if not response_text:
                    raise ValueError("Ollama returned an empty response.")

                result = response_model.model_validate_json(response_text)

                logger.info(
                    "Ollama operation completed. operation=%s attempt=%d",
                    operation,
                    attempt,
                )

                return result

            except (httpx.HTTPError, ValidationError, ValueError, TypeError) as exc:
                last_exception = exc

                logger.warning(
                    "Ollama operation failed. operation=%s attempt=%d/%d error=%s",
                    operation,
                    attempt,
                    total_attempts,
                    exc,
                )

        logger.error("Ollama operation failed after %d attempt(s). operation=%s", total_attempts, operation)

        raise LLMServiceError("Ollama request failed.", operation=operation) from last_exception

    def close(self) -> None:
        try:
            self._client.close()
            logger.info("Ollama client closed.")
        except Exception:
            logger.exception("Failed to close Ollama client cleanly.")
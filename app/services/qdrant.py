from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient

from app.config import settings
from app.exceptions import RetrievalServiceError
from app.schemas.verification import EvidenceItem

from app.data.sources import HISTORICAL_SOURCES

logger = logging.getLogger(__name__)


def _safe_str(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_list_int(value: Any) -> list[int]:
    if value is None:
        return []
    if isinstance(value, list):
        result: list[int] = []
        for item in value:
            try:
                result.append(int(item))
            except (TypeError, ValueError):
                continue
        return result
    try:
        return [int(value)]
    except (TypeError, ValueError):
        return []


class QdrantService:
    def __init__(self) -> None:
        self._client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=settings.QDRANT_TIMEOUT_SECONDS,
        )
        self._collection = settings.QDRANT_COLLECTION_NAME
        logger.info("Qdrant client initialized. collection=%s", self._collection)

    def search(self, vector: list[float], top_k: int | None = None) -> list[EvidenceItem]:
        if not vector:
            raise ValueError("Qdrant search vector must not be empty.")

        limit = top_k if top_k is not None else settings.TOP_K
        if limit <= 0:
            raise ValueError("Qdrant search limit must be greater than zero.")

        try:
            response = self._client.query_points(
                collection_name=self._collection,
                query=vector,
                limit=limit,
                with_payload=True,
            )
        except Exception as exc:
            logger.exception("Qdrant search failed. collection=%s", self._collection)
            raise RetrievalServiceError(
                "Qdrant search could not be completed."
            ) from exc

        items: list[EvidenceItem] = []
        for point in response.points:
            payload: dict[str, Any] = point.payload or {}
            text = _safe_str(payload.get("raw_text") or payload.get("overlap_text")).strip()
            chunk_id = _safe_str(
                payload.get("chunk_id") or point.id,
                fallback=str(point.id),
            )
            book_name_text = _safe_str(payload.get("book_name")).strip()
            book_name = book_name_text or None

            source_id = None

            if book_name and book_name in HISTORICAL_SOURCES:
                source_id = HISTORICAL_SOURCES[book_name]["source_id"]

            headers_raw = payload.get("headers")
            headers: dict[str, str] | None = None

            if isinstance(headers_raw, dict):
                headers = {
                    str(key): str(value)
                    for key, value in headers_raw.items()
                }

            footnotes_raw = payload.get("footnotes")

            items.append(
                EvidenceItem(
                    chunk_id=chunk_id or None,
                    score=_safe_float(getattr(point, "score", None)),
                    book_name=book_name_text, 
                    source_id=source_id,
                    pages=_safe_list_int(payload.get("pages")),
                    text=text,
                    headers=headers,
                    footnotes=footnotes_raw if isinstance(footnotes_raw, dict) else None,
                )
            )
 
        return items

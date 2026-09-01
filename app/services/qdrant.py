from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient

from app.config import settings
from app.data.sources import HISTORICAL_SOURCES
from app.exceptions import RetrievalServiceError
from app.schemas.verification import EvidenceItem

logger = logging.getLogger(__name__)


def _safe_str(value: Any, fallback: str = "") -> str:
    return fallback if value is None else str(value)


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


def _resolve_source_id(payload: dict[str, Any], book_name: str) -> str | None:
    source_id = _safe_str(payload.get("source_id")).strip()
    if source_id:
        return source_id

    if book_name and book_name in HISTORICAL_SOURCES:
        return HISTORICAL_SOURCES[book_name]["source_id"]

    return None


def _build_evidence_item(point: Any, payload: dict[str, Any], text: str) -> EvidenceItem:
    book_name = _safe_str(payload.get("book_name")).strip()
    source_id = _resolve_source_id(payload, book_name)

    headers_raw = payload.get("headers")
    headers = None
    if isinstance(headers_raw, dict):
        headers = {str(key): str(value) for key, value in headers_raw.items()}

    footnotes_raw = payload.get("footnotes")

    return EvidenceItem(
        chunk_id=str(point.id),
        score=_safe_float(getattr(point, "score", None)),
        book_name=book_name,
        source_id=source_id,
        pages=_safe_list_int(payload.get("pages")),
        text=text,
        headers=headers,
        footnotes=footnotes_raw if isinstance(footnotes_raw, dict) else None,
    )


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
            raise RetrievalServiceError("Qdrant search could not be completed.") from exc

        items: list[EvidenceItem] = []

        for point in response.points:
            payload = point.payload or {}
            text = _safe_str(payload.get("raw_text") or payload.get("overlap_text")).strip()

            if not text:
                continue

            items.append(_build_evidence_item(point, payload, text))

        return items

    def scroll_all(self) -> list[EvidenceItem]:
        """
        Chỉ dùng để build BM25 artifact offline.
        Runtime Cloud Run không gọi method này.
        """
        items: list[EvidenceItem] = []
        offset = None

        while True:
            points, offset = self._client.scroll(
                collection_name=self._collection,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            for point in points:
                payload = point.payload or {}
                text = _safe_str(payload.get("raw_text")).strip()

                if not text:
                    continue

                items.append(_build_evidence_item(point, payload, text))

            if offset is None:
                break

        logger.info("Loaded %d Qdrant documents for BM25 build.", len(items))
        return items
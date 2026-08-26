from __future__ import annotations

import logging

from app.config import settings
from app.exceptions import RetrievalServiceError
from app.schemas.verification import EvidenceItem
from app.services.embedding import EmbeddingService
from app.services.qdrant import QdrantService

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        qdrant_service: QdrantService,
    ) -> None:
        self._embedding_service = embedding_service
        self._qdrant_service = qdrant_service

    def retrieve(self, query_text: str, *, top_k: int | None = None) -> list[EvidenceItem]:
        query_text = query_text.strip()
        if not query_text:
            raise ValueError("Retrieval query must not be empty.")

        try:
            vector = self._embedding_service.embed_text(query_text)
            items = self._qdrant_service.search(vector=vector, top_k=top_k)
        except RetrievalServiceError:
            raise
        except Exception as exc:
            logger.exception("Evidence retrieval failed before result filtering.")
            raise RetrievalServiceError(
                "Evidence retrieval could not be completed."
            ) from exc

        valid_items: list[EvidenceItem] = []
        for item in items:
            text = item.text.strip()
            if not text:
                continue

            if settings.MIN_EVIDENCE_SCORE > 0.0:
                if item.score is None or item.score < settings.MIN_EVIDENCE_SCORE:
                    continue

            valid_items.append(item.model_copy(update={"text": text}))

        logger.info("Retrieved %d valid evidence item(s).", len(valid_items))
        return valid_items

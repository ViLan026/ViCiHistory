from __future__ import annotations

import logging

from app.config import settings
from app.exceptions import RetrievalServiceError
from app.schemas.verification import EvidenceItem
from app.services.bm25 import BM25Service
from app.services.embedding import EmbeddingService
from app.services.qdrant import QdrantService

logger = logging.getLogger(__name__)


class RetrievalService:

    def __init__(
        self,
        embedding_service: EmbeddingService,
        qdrant_service: QdrantService,
        bm25_service: BM25Service,
    ) -> None:
        self._embedding_service = embedding_service
        self._qdrant_service = qdrant_service
        self._bm25_service = bm25_service

    @staticmethod
    def _normalize_scores(items: list[EvidenceItem]) -> dict[str, float]:
        if not items:
            return {}

        scores = [item.score or 0.0 for item in items]
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return {
                item.chunk_id: 1.0
                for item in items
                if item.chunk_id
            }

        return {
            item.chunk_id: ((item.score or 0.0) - min_score) / (max_score - min_score)
            for item in items
            if item.chunk_id
        }

    def retrieve(
        self,
        query_text: str,
        *,
        top_k: int | None = None,
    ) -> list[EvidenceItem]:

        query_text = query_text.strip()

        if not query_text:
            raise ValueError("Retrieval query must not be empty.")

        final_k = top_k if top_k is not None else settings.TOP_K
        candidate_k = max(final_k, settings.RETRIEVAL_CANDIDATE_K)

        try:
            vector = self._embedding_service.embed_text(query_text)

            dense_items = self._qdrant_service.search(
                vector=vector,
                top_k=candidate_k,
            )

            bm25_items = self._bm25_service.search(
                query=query_text,
                top_k=candidate_k,
            )

        except RetrievalServiceError:
            raise

        except Exception as exc:
            logger.exception("Hybrid evidence retrieval failed.")

            raise RetrievalServiceError(
                "Evidence retrieval could not be completed."
            ) from exc

        dense_scores = self._normalize_scores(dense_items)
        bm25_scores = self._normalize_scores(bm25_items)

        item_map: dict[str, EvidenceItem] = {}

        for item in dense_items:
            if item.chunk_id:
                item_map[item.chunk_id] = item

        for item in bm25_items:
            if item.chunk_id and item.chunk_id not in item_map:
                item_map[item.chunk_id] = item

        hybrid_items: list[EvidenceItem] = []

        for chunk_id, item in item_map.items():
            dense_score = dense_scores.get(chunk_id, 0.0)
            bm25_score = bm25_scores.get(chunk_id, 0.0)

            hybrid_score = (
                settings.HYBRID_ALPHA * dense_score
                + (1.0 - settings.HYBRID_ALPHA) * bm25_score
            )

            hybrid_items.append(
                item.model_copy(
                    update={"score": hybrid_score}
                )
            )

        hybrid_items.sort(
            key=lambda item: item.score or 0.0,
            reverse=True,
        )

        valid_items: list[EvidenceItem] = []

        for item in hybrid_items[:final_k]:
            text = item.text.strip()

            if not text:
                continue

            if settings.MIN_EVIDENCE_SCORE > 0.0:
                if item.score is None or item.score < settings.MIN_EVIDENCE_SCORE:
                    continue

            valid_items.append(
                item.model_copy(update={"text": text})
            )

        logger.info(
            "Hybrid retrieval: dense=%d bm25=%d merged=%d final=%d",
            len(dense_items),
            len(bm25_items),
            len(hybrid_items),
            len(valid_items),
        )

        return valid_items
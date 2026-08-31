from __future__ import annotations

from app.config import settings
from app.services.bm25_service import BM25Service
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService


class HybridSearchService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        qdrant_service: QdrantService,
        bm25_service: BM25Service,
    ) -> None:
        self._embedding_service = embedding_service
        self._qdrant_service = qdrant_service
        self._bm25_service = bm25_service

    def search(self, query: str) -> list[dict]:
        query_vector = self._embedding_service.embed_text(query)

        dense_results = self._qdrant_service.search(
            query_vector,
            top_k=settings.DENSE_TOP_K,
        )

        bm25_results = self._bm25_service.search(
            query,
            top_k=settings.BM25_TOP_K,
        )

        return self._fuse(dense_results, bm25_results)

    def _fuse(
        self,
        dense_results: list[dict],
        bm25_results: list[dict],
    ) -> list[dict]:
        dense_scores = {
            result["chunk_id"]: result["score"]
            for result in dense_results
        }

        bm25_scores = {
            result["chunk_id"]: result["score"]
            for result in bm25_results
        }

        dense_norm = self._normalize(dense_scores)
        bm25_norm = self._normalize(bm25_scores)

        results_by_id = {}

        for result in dense_results + bm25_results:
            results_by_id[result["chunk_id"]] = result

        results = []

        for chunk_id, result in results_by_id.items():
            dense_score = dense_norm.get(chunk_id, 0.0)
            bm25_score = bm25_norm.get(chunk_id, 0.0)

            hybrid_score = (
                settings.HYBRID_ALPHA * dense_score
                + (1.0 - settings.HYBRID_ALPHA) * bm25_score
            )

            results.append({
                **result,
                "dense_score": dense_score,
                "bm25_score": bm25_score,
                "score": hybrid_score,
            })

        results.sort(
            key=lambda result: result["score"],
            reverse=True,
        )

        return results[:settings.HYBRID_TOP_K]

    @staticmethod
    def _normalize(scores: dict[str, float]) -> dict[str, float]:
        if not scores:
            return {}

        min_score = min(scores.values())
        max_score = max(scores.values())

        if max_score == min_score:
            return {
                chunk_id: 1.0
                for chunk_id in scores
            }

        return {
            chunk_id: (score - min_score) / (max_score - min_score)
            for chunk_id, score in scores.items()
        }
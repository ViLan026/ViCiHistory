from __future__ import annotations

from dataclasses import dataclass
import logging
import time

from app.config import settings
from app.services.bm25 import BM25Service
from app.services.embedding import EmbeddingService
from app.services.evidence_map import EvidenceMapService
from app.services.ollama import OllamaService
from app.services.qdrant import QdrantService
from app.services.retrieval import RetrievalService
from app.services.source_excerpt import SourceExcerptService

logger = logging.getLogger(__name__)


@dataclass
class ServiceContainer:
    ollama: OllamaService
    evidence_map: EvidenceMapService
    source_excerpt: SourceExcerptService

    def close(self) -> None:
        self.ollama.close()


def build_services() -> ServiceContainer:
    start = time.perf_counter()

    embedding = EmbeddingService()
    qdrant = QdrantService()
    bm25 = BM25Service.load(settings.BM25_INDEX_PATH, expected_collection=settings.QDRANT_COLLECTION_NAME)

    retrieval = RetrievalService(
        embedding_service=embedding,
        qdrant_service=qdrant,
        bm25_service=bm25,
    )

    ollama = OllamaService()
    evidence_map = EvidenceMapService(ollama_service=ollama, retrieval_service=retrieval)
    source_excerpt = SourceExcerptService()

    logger.info("All services initialized in %.2fs.", time.perf_counter() - start)

    return ServiceContainer(
        ollama=ollama,
        evidence_map=evidence_map,
        source_excerpt=source_excerpt,
    )
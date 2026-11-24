from __future__ import annotations

from dataclasses import dataclass
import logging
import time

from app.config import settings
from app.services.bm25 import BM25Service
from app.services.embedding import EmbeddingService
from app.services.evidence_map import EvidenceMapService
# from app.services.ollama import OllamaService
from app.services.gemini import GeminiService
from app.services.qdrant import QdrantService
from app.services.retrieval import RetrievalService
from app.services.source_excerpt import SourceExcerptService
from app.services.r2_storage import R2StorageService

logger = logging.getLogger(__name__)


@dataclass
class ServiceContainer:
    gemini: GeminiService
    r2_storage: R2StorageService
    evidence_map: EvidenceMapService
    source_excerpt: SourceExcerptService

    def close(self) -> None:
        self.gemini.close()
        self.r2_storage.close()

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

    gemini = GeminiService()
    evidence_map = EvidenceMapService(gemini_service=gemini, retrieval_service=retrieval)
    r2_storage = R2StorageService()
    source_excerpt = SourceExcerptService(storage_service=r2_storage)

    logger.info("All services initialized in %.2fs.", time.perf_counter() - start)

    return ServiceContainer(
        gemini=gemini,
        r2_storage=r2_storage,
        evidence_map=evidence_map,
        source_excerpt=source_excerpt,
    )
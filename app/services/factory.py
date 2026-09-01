from __future__ import annotations

from dataclasses import dataclass
import logging
import time

from app.config import settings
from app.services.bm25 import BM25Service
from app.services.embedding import EmbeddingService
from app.services.gemini import GeminiService
from app.services.qdrant import QdrantService
from app.services.retrieval import RetrievalService
from app.services.storage import StorageService
from app.services.verification import VerificationService

logger = logging.getLogger(__name__)


@dataclass
class ServiceContainer:
    gemini: GeminiService
    verifier: VerificationService
    storage: StorageService

    def close(self) -> None:
        self.gemini.close()


def build_services() -> ServiceContainer:
    start = time.perf_counter()

    embedding = EmbeddingService()
    qdrant = QdrantService()

    bm25 = BM25Service.load(
        settings.BM25_INDEX_PATH,
        expected_collection=settings.QDRANT_COLLECTION_NAME,
    )

    retrieval = RetrievalService(
        embedding_service=embedding,
        qdrant_service=qdrant,
        bm25_service=bm25,
    )

    gemini = GeminiService()

    verifier = VerificationService(
        gemini_service=gemini,
        retrieval_service=retrieval,
    )

    storage = StorageService()

    logger.info("All services initialized in %.2fs.", time.perf_counter() - start)

    return ServiceContainer(
        gemini=gemini,
        verifier=verifier,
        storage=storage,
    )
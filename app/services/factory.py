from __future__ import annotations

from dataclasses import dataclass

from app.services.embedding import EmbeddingService
from app.services.gemini import GeminiService
from app.services.qdrant import QdrantService
from app.services.retrieval import RetrievalService
from app.services.storage import StorageService
from app.services.verification import VerificationService


@dataclass
class ServiceContainer:
    gemini: GeminiService
    verifier: VerificationService
    storage: StorageService

    def close(self) -> None:
        self.gemini.close()


def build_services() -> ServiceContainer:
    embedding = EmbeddingService()
    qdrant = QdrantService()
    retrieval = RetrievalService(
        embedding_service=embedding,
        qdrant_service=qdrant,
    )
    gemini = GeminiService()
    verifier = VerificationService(
        gemini_service=gemini,
        retrieval_service=retrieval,
    )
    storage = StorageService()

    return ServiceContainer(
        gemini=gemini,
        verifier=verifier,
        storage=storage,
    )
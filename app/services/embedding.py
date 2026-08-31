from __future__ import annotations

import logging
import os
import time

from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        if settings.HF_TOKEN:
            os.environ.setdefault("HF_TOKEN", settings.HF_TOKEN)
            os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", settings.HF_TOKEN)

        logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
        start = time.perf_counter()

        self._model = SentenceTransformer(
            settings.EMBEDDING_MODEL,
            token=settings.HF_TOKEN,
            local_files_only=True,
        )

        logger.info(
            "Embedding model loaded successfully in %.2fs.",
            time.perf_counter() - start,
        )

        warmup_start = time.perf_counter()

        logger.info("Warming up embedding model.")

        self._model.encode(
            ["Khởi động hệ thống truy xuất lịch sử."],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        logger.info(
            "Embedding model warm-up completed in %.2fs.",
            time.perf_counter() - warmup_start,
        )

    def embed_text(self, text: str) -> list[float]:
        text = text.strip()
        if not text:
            raise ValueError("embed_text received an empty string.")

        vector = self._model.encode(text, normalize_embeddings=True)
        return vector.tolist()

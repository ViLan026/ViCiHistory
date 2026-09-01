from __future__ import annotations

import logging
import time

from app.config import settings
from app.services.bm25 import BM25Service
from app.services.qdrant import QdrantService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> None:
    start = time.perf_counter()

    logger.info("Starting BM25 artifact build.")
    logger.info("Source collection: %s", settings.QDRANT_COLLECTION_NAME)

    qdrant = QdrantService()
    documents = qdrant.scroll_all()

    if not documents:
        raise RuntimeError("No documents were loaded from Qdrant.")

    BM25Service.build_and_save(
        documents=documents,
        index_path=settings.BM25_INDEX_PATH,
        collection_name=settings.QDRANT_COLLECTION_NAME,
    )

    logger.info("BM25 build completed in %.2fs.", time.perf_counter() - start)


if __name__ == "__main__":
    main()
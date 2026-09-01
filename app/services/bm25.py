from __future__ import annotations

import logging
import pickle
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from app.schemas.verification import EvidenceItem

logger = logging.getLogger(__name__)

BM25_ARTIFACT_VERSION = 1
BM25_TOKENIZER_VERSION = "raw_text_nfc_lower_regex_v1"


class BM25Service:
    def __init__(self, bm25: BM25Okapi, documents: list[EvidenceItem]) -> None:
        if not documents:
            raise ValueError("BM25 documents must not be empty.")

        self._bm25 = bm25
        self._documents = documents

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        text = unicodedata.normalize("NFC", text.lower())
        return re.findall(r"\w+", text, flags=re.UNICODE)

    @classmethod
    def build_and_save(
        cls,
        documents: list[EvidenceItem],
        index_path: str | Path,
        collection_name: str,
    ) -> None:
        if not documents:
            raise ValueError("Cannot build BM25 index from empty corpus.")

        start = time.perf_counter()
        logger.info("Building BM25 index. documents=%d", len(documents))

        tokenized_corpus = [cls._tokenize(document.text) for document in documents]
        bm25 = BM25Okapi(tokenized_corpus)

        artifact = {
            "artifact_version": BM25_ARTIFACT_VERSION,
            "tokenizer_version": BM25_TOKENIZER_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "collection_name": collection_name,
            "document_count": len(documents),
            "bm25": bm25,
            "documents": [
                document.model_dump(exclude={"score"}, exclude_none=True)
                for document in documents
            ],
        }

        path = Path(index_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("wb") as file:
            pickle.dump(artifact, file, protocol=pickle.HIGHEST_PROTOCOL)

        size_mb = path.stat().st_size / 1024 / 1024

        logger.info(
            "BM25 artifact created. documents=%d path=%s size=%.2fMB time=%.2fs",
            len(documents),
            path,
            size_mb,
            time.perf_counter() - start,
        )

    @classmethod
    def load(
        cls,
        index_path: str | Path,
        expected_collection: str | None = None,
    ) -> "BM25Service":
        start = time.perf_counter()
        path = Path(index_path)

        if not path.exists():
            raise FileNotFoundError(f"BM25 index artifact not found: {path}")

        logger.info("Loading BM25 artifact from %s", path)

        with path.open("rb") as file:
            artifact = pickle.load(file)

        if not isinstance(artifact, dict):
            raise ValueError("Invalid BM25 artifact format.")

        artifact_version = artifact.get("artifact_version")
        if artifact_version != BM25_ARTIFACT_VERSION:
            raise ValueError(
                f"Unsupported BM25 artifact version. "
                f"expected={BM25_ARTIFACT_VERSION} actual={artifact_version}"
            )

        tokenizer_version = artifact.get("tokenizer_version")
        if tokenizer_version != BM25_TOKENIZER_VERSION:
            raise ValueError(
                f"BM25 tokenizer version mismatch. "
                f"expected={BM25_TOKENIZER_VERSION} actual={tokenizer_version}"
            )

        collection_name = str(artifact.get("collection_name", "")).strip()
        if expected_collection and collection_name != expected_collection:
            raise ValueError(
                f"BM25 artifact collection mismatch. "
                f"expected={expected_collection} actual={collection_name}"
            )

        bm25 = artifact.get("bm25")
        if not isinstance(bm25, BM25Okapi):
            raise ValueError("Invalid BM25 object in artifact.")

        raw_documents = artifact.get("documents")
        if not isinstance(raw_documents, list):
            raise ValueError("Invalid BM25 document mapping.")

        documents = [EvidenceItem.model_validate(document) for document in raw_documents]

        expected_count = artifact.get("document_count")
        if expected_count != len(documents):
            raise ValueError(
                f"BM25 document count mismatch. "
                f"expected={expected_count} actual={len(documents)}"
            )

        logger.info(
            "BM25 artifact loaded. documents=%d collection=%s time=%.2fs",
            len(documents),
            collection_name,
            time.perf_counter() - start,
        )

        return cls(bm25=bm25, documents=documents)

    def search(self, query: str, top_k: int) -> list[EvidenceItem]:
        if top_k <= 0:
            raise ValueError("BM25 top_k must be greater than zero.")

        tokens = self._tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)
        indices = np.argsort(scores)[::-1][:top_k]

        results: list[EvidenceItem] = []

        for index in indices:
            score = float(scores[index])

            if score <= 0:
                continue

            results.append(
                self._documents[index].model_copy(update={"score": score})
            )

        return results
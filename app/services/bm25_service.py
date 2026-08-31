from __future__ import annotations

import logging
import re

from rank_bm25 import BM25Okapi
from underthesea import word_tokenize

logger = logging.getLogger(__name__)


class BM25Service:
    def __init__(self, documents: list[dict]) -> None:
        logger.info("Building BM25 index with %d documents.", len(documents))

        self._documents = documents
        self._tokenized_corpus = [
            self._tokenize(document.get("raw_text", ""))
            for document in documents
        ]
        self._bm25 = BM25Okapi(self._tokenized_corpus)

        logger.info("BM25 index built successfully.")

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        tokens = self._tokenize(query)

        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )[:top_k]

        results = []

        for index in ranked_indices:
            document = self._documents[index]
            score = float(scores[index])

            results.append({
                "chunk_id": document["chunk_id"],
                "score": score,
                "payload": document,
            })

        return results

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)

        segmented = word_tokenize(text, format="text")

        return segmented.split()
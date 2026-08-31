from __future__ import annotations

import re
import unicodedata

import numpy as np
from rank_bm25 import BM25Okapi

from app.schemas.verification import EvidenceItem


class BM25Service:

    def __init__(self, documents: list[EvidenceItem]) -> None:
        self._documents = documents
        self._tokenized_corpus = [
            self._tokenize(document.text)
            for document in documents
        ]

        self._bm25 = BM25Okapi(self._tokenized_corpus)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        text = unicodedata.normalize("NFC", text.lower())
        return re.findall(r"\w+", text, flags=re.UNICODE)

    def search(self, query: str, top_k: int) -> list[EvidenceItem]:
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
                self._documents[index].model_copy(
                    update={"score": score}
                )
            )

        return results
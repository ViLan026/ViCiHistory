from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

import fitz
from google.cloud import storage

from app.schemas.source_view_schema import HighlightRect, SourcePage, SourceWord
from app.data.sources import HISTORICAL_SOURCES

logger = logging.getLogger(__name__)

SOURCE_CONFIG = {
    source["source_id"]: {
        "blob": source["object_name"],
        "offset": source.get("offset", 0),
    }
    for source in HISTORICAL_SOURCES.values()
}

TOKEN_PATTERN = re.compile(r"[\wÀ-ỹĐđ]+", re.UNICODE)


def normalize_token(text: str) -> str:
    return text.casefold().strip()


def tokenize(text: str) -> list[str]:
    return [normalize_token(value) for value in TOKEN_PATTERN.findall(text) if value.strip()]


class SourceDocumentService:
    def __init__(self, bucket_name: str) -> None:
        self._bucket_name = bucket_name
        self._storage_client = storage.Client()
        self._cache_dir = Path("/tmp/history_sources")
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def to_pdf_page(source_id: str, source_page: int) -> int:
        config = SOURCE_CONFIG.get(source_id)

        if config is None:
            raise ValueError(f"Unknown source_id: {source_id}")

        return source_page + int(config["offset"])

    def _get_pdf_path(self, source_id: str) -> Path:
        config = SOURCE_CONFIG.get(source_id)

        if config is None:
            raise ValueError(f"Unknown source_id: {source_id}")

        path = self._cache_dir / f"{source_id}.pdf"

        if path.exists() and path.stat().st_size > 0:
            return path

        logger.info("Downloading source PDF from GCS. source_id=%s", source_id)

        bucket = self._storage_client.bucket(self._bucket_name)
        blob = bucket.blob(str(config["blob"]))
        blob.download_to_filename(path)

        return path

    def get_document(self, source_id: str) -> fitz.Document:
        return fitz.open(self._get_pdf_path(source_id))

    def get_page_image(self, source_id: str, pdf_page: int, scale: float = 1.6) -> bytes:
        document = self.get_document(source_id)

        try:
            if pdf_page < 1 or pdf_page > document.page_count:
                raise ValueError("PDF page is out of range.")

            page = document.load_page(pdf_page - 1)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            return pixmap.tobytes("png")
        finally:
            document.close()

    def build_evidence_view(self, source_id: str, source_pages: list[int], evidence_text: str) -> tuple[list[int], list[int], list[SourcePage], bool]:
        if not source_pages or any(page < 1 for page in source_pages):
            raise ValueError("'pages' must contain page numbers >= 1.")

        if not evidence_text.strip():
            raise ValueError("'text' must not be empty.")
        
        source_pages = sorted(set(source_pages))
        pdf_pages = [self.to_pdf_page(source_id, page) for page in source_pages]

        document = self.get_document(source_id)

        try:
            first_page = max(1, min(pdf_pages) - 3)
            last_page = min(document.page_count, max(pdf_pages) + 3)
            display_pages = list(range(first_page, last_page + 1))

            page_words: dict[int, list[SourceWord]] = {}
            token_refs: list[tuple[str, int, int]] = []

            for pdf_page in display_pages:
                page = document.load_page(pdf_page - 1)
                raw_words = page.get_text("words", sort=True)
                words: list[SourceWord] = []

                for index, raw in enumerate(raw_words):
                    x0, y0, x1, y1, text, block, line, word = raw
                    words.append(
                        SourceWord(
                            text=text,
                            x=x0 / page.rect.width,
                            y=y0 / page.rect.height,
                            width=(x1 - x0) / page.rect.width,
                            height=(y1 - y0) / page.rect.height,
                            block=int(block),
                            line=int(line),
                            word=int(word),
                        )
                    )

                    if pdf_page in pdf_pages:
                        for token in tokenize(text):
                            token_refs.append((token, pdf_page, index))

                page_words[pdf_page] = words

            matched = self._find_match(token_refs, evidence_text)
            highlights = self._build_highlights(page_words, matched)

            pages = [
                SourcePage(
                    page=pdf_page,
                    width=1.0,
                    height=1.0,
                    words=page_words[pdf_page],
                    highlights=highlights.get(pdf_page, []),
                )
                for pdf_page in display_pages
            ]

            return pdf_pages, display_pages, pages, bool(matched)
        finally:
            document.close()

    @staticmethod
    def _find_match(token_refs: list[tuple[str, int, int]], evidence_text: str) -> list[tuple[str, int, int]]:
        target = tokenize(evidence_text)
        source = [item[0] for item in token_refs]

        if not target or not source:
            return []

        for start in range(len(source) - len(target) + 1):
            if source[start:start + len(target)] == target:
                return token_refs[start:start + len(target)]

        max_size = min(24, len(target))

        for size in range(max_size, 7, -1):
            for target_start in range(len(target) - size + 1):
                fragment = target[target_start:target_start + size]

                if len(" ".join(fragment)) < 40:
                    continue

                matches = []

                for source_start in range(len(source) - size + 1):
                    if source[source_start:source_start + size] == fragment:
                        matches.append(source_start)

                if len(matches) == 1:
                    start = matches[0]
                    return token_refs[start:start + size]

        return []

    @staticmethod
    def _build_highlights(
        page_words: dict[int, list[SourceWord]],
        matched: list[tuple[str, int, int]],
    ) -> dict[int, list[HighlightRect]]:
        indexes: dict[int, set[int]] = defaultdict(set)

        for _, page, item_index in matched:
            indexes[page].add(item_index)

        result: dict[int, list[HighlightRect]] = {}

        for page_number, item_indexes in indexes.items():
            words = page_words[page_number]
            lines: dict[tuple[int, int], list[SourceWord]] = defaultdict(list)

            for index in sorted(item_indexes):
                word = words[index]
                lines[(word.block, word.line)].append(word)

            rects: list[HighlightRect] = []

            for line_words in lines.values():
                x0 = min(word.x for word in line_words)
                y0 = min(word.y for word in line_words)
                x1 = max(word.x + word.width for word in line_words)
                y1 = max(word.y + word.height for word in line_words)

                rects.append(
                    HighlightRect(
                        x=max(0, x0 - 0.003),
                        y=max(0, y0 - 0.002),
                        width=min(1 - x0, x1 - x0 + 0.006),
                        height=min(1 - y0, y1 - y0 + 0.004),
                    )
                )

            result[page_number] = rects

        return result
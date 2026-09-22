from __future__ import annotations

import logging
import os
import re
import tempfile
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import boto3
import fitz
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.data.sources import SOURCE_BY_ID
from app.exceptions import StorageServiceError

logger = logging.getLogger(__name__)

TOKEN_PATTERN = re.compile(r"[\wÀ-ỹĐđ]+", re.UNICODE)


@dataclass
class TokenRef:
    token: str
    page: int
    block: int
    line: int
    rect: fitz.Rect


@dataclass
class PdfExcerptResult:
    content: bytes
    start_pdf_page: int
    end_pdf_page: int
    target_excerpt_page: int
    highlight_mode: str


def tokenize(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_PATTERN.findall(text) if token.strip()]


class SourceExcerptService:
    def __init__(self) -> None:
        if not settings.S3_BUCKET_NAME:
            raise ValueError("S3_BUCKET_NAME must be configured.")

        self._bucket_name = settings.S3_BUCKET_NAME
        self._cache_dir = Path(settings.SOURCE_CACHE_DIR)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._download_lock = threading.Lock()

        self._client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        )

        logger.info("Source excerpt service initialized. bucket=%s cache=%s", self._bucket_name, self._cache_dir)

    def _get_source(self, source_id: str) -> dict:
        source = SOURCE_BY_ID.get(source_id)

        if source is None:
            raise ValueError(f"Historical source not found: {source_id}")

        return source

    def _get_pdf_path(self, source_id: str) -> Path:
        source = self._get_source(source_id)
        path = self._cache_dir / f"{source_id}.pdf"

        if path.exists() and path.stat().st_size > 0:
            return path

        with self._download_lock:
            if path.exists() and path.stat().st_size > 0:
                return path

            logger.info("Downloading historical PDF from S3. source_id=%s key=%s", source_id, source["s3_key"])

            temp_file = tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=".pdf.part",
                prefix=f"{source_id}_",
                dir=self._cache_dir,
                delete=False,
            )
            temp_path = Path(temp_file.name)
            temp_file.close()

            try:
                self._client.download_file(
                    Bucket=self._bucket_name,
                    Key=source["s3_key"],
                    Filename=str(temp_path),
                )

                if not temp_path.exists() or temp_path.stat().st_size == 0:
                    raise StorageServiceError(f"Downloaded source is empty: {source_id}")

                os.replace(temp_path, path)
                logger.info("Historical PDF cached. source_id=%s size=%d", source_id, path.stat().st_size)
                return path

            except StorageServiceError:
                raise

            except (BotoCoreError, ClientError, OSError) as exc:
                logger.exception("Failed to download source from S3. source_id=%s", source_id)
                raise StorageServiceError(f"Could not download historical source: {source_id}") from exc

            finally:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)

    @staticmethod
    def _build_page_window(target_pages: list[int], page_count: int) -> tuple[int, int]:
        target_pages = sorted(set(target_pages))

        if not target_pages or any(page < 1 or page > page_count for page in target_pages):
            raise ValueError("PDF page is out of range.")

        target_start = min(target_pages)
        target_end = max(target_pages)
        target_span = target_end - target_start + 1
        window_size = min(settings.PDF_EXCERPT_PAGE_COUNT, page_count)

        if target_span > window_size:
            raise ValueError("Evidence spans more pages than the excerpt limit.")

        extra = window_size - target_span
        start = target_start - extra // 2
        end = start + window_size - 1

        if start < 1:
            end += 1 - start
            start = 1

        if end > page_count:
            start = max(1, start - (end - page_count))
            end = page_count

        return start, end

    @staticmethod
    def _collect_token_refs(document: fitz.Document, target_pages: list[int]) -> list[TokenRef]:
        refs: list[TokenRef] = []

        for page_number in sorted(set(target_pages)):
            page = document.load_page(page_number - 1)

            for raw in page.get_text("words", sort=True):
                x0, y0, x1, y1, text, block, line, _word = raw
                rect = fitz.Rect(x0, y0, x1, y1)

                for token in tokenize(text):
                    refs.append(TokenRef(
                        token=token,
                        page=page_number,
                        block=int(block),
                        line=int(line),
                        rect=rect,
                    ))

        return refs

    @staticmethod
    def _find_match(refs: list[TokenRef], evidence_text: str) -> tuple[list[TokenRef], str]:
        target = tokenize(evidence_text)
        source = [ref.token for ref in refs]

        if not target or not source:
            return [], "none"

        for start in range(len(source) - len(target) + 1):
            if source[start:start + len(target)] == target:
                return refs[start:start + len(target)], "exact"

        max_size = min(24, len(target))

        for size in range(max_size, 11, -1):
            for target_start in range(len(target) - size + 1):
                fragment = target[target_start:target_start + size]
                matches: list[int] = []

                for source_start in range(len(source) - size + 1):
                    if source[source_start:source_start + size] == fragment:
                        matches.append(source_start)

                if len(matches) == 1:
                    start = matches[0]
                    return refs[start:start + size], "partial"

        return [], "none"

    @staticmethod
    def _add_highlights(
        excerpt: fitz.Document,
        matched_refs: list[TokenRef],
        excerpt_start_page: int,
    ) -> None:
        grouped: dict[tuple[int, int, int], list[fitz.Rect]] = defaultdict(list)

        for ref in matched_refs:
            grouped[(ref.page, ref.block, ref.line)].append(ref.rect)

        for (original_page, _block, _line), rects in grouped.items():
            unique_rects: dict[tuple[float, float, float, float], fitz.Rect] = {}

            for rect in rects:
                key = (rect.x0, rect.y0, rect.x1, rect.y1)
                unique_rects[key] = rect

            line_rects = list(unique_rects.values())

            if not line_rects:
                continue

            x0 = min(rect.x0 for rect in line_rects)
            y0 = min(rect.y0 for rect in line_rects)
            x1 = max(rect.x1 for rect in line_rects)
            y1 = max(rect.y1 for rect in line_rects)

            excerpt_page_index = original_page - excerpt_start_page
            page = excerpt.load_page(excerpt_page_index)

            highlight_rect = fitz.Rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1)
            annotation = page.add_highlight_annot(highlight_rect)
            annotation.set_opacity(0.35)
            annotation.update()

    def build_excerpt(self, source_id: str, pdf_pages: list[int], evidence_text: str) -> PdfExcerptResult:
        pdf_path = self._get_pdf_path(source_id)
        source_document = fitz.open(pdf_path)
        excerpt = fitz.open()

        try:
            start_page, end_page = self._build_page_window(pdf_pages, source_document.page_count)

            excerpt.insert_pdf(
                source_document,
                from_page=start_page - 1,
                to_page=end_page - 1,
            )

            refs = self._collect_token_refs(source_document, pdf_pages)
            matched_refs, highlight_mode = self._find_match(refs, evidence_text)

            if matched_refs:
                self._add_highlights(excerpt, matched_refs, start_page)

            target_excerpt_page = min(pdf_pages) - start_page + 1

            content = excerpt.tobytes(
                garbage=3,
                deflate=True,
            )

            logger.info(
                "Built PDF excerpt. source_id=%s pages=%d-%d target=%s highlight=%s size=%d",
                source_id,
                start_page,
                end_page,
                pdf_pages,
                highlight_mode,
                len(content),
            )

            return PdfExcerptResult(
                content=content,
                start_pdf_page=start_page,
                end_pdf_page=end_page,
                target_excerpt_page=target_excerpt_page,
                highlight_mode=highlight_mode,
            )

        finally:
            excerpt.close()
            source_document.close()
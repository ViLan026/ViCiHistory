from __future__ import annotations

import logging

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.data.sources import HISTORICAL_SOURCES
from app.exceptions import StorageServiceError

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self) -> None:
        if not settings.S3_BUCKET_NAME:
            raise ValueError("S3_BUCKET_NAME must be configured.")

        self._bucket_name = settings.S3_BUCKET_NAME

        self._client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},
            ),
        )

        self._sources_by_id = {
            source["source_id"]: {
                "book_name": book_name,
                "s3_key": source["s3_key"],
            }
            for book_name, source in HISTORICAL_SOURCES.items()
        }

        logger.info(
            "Amazon S3 client initialized. bucket=%s region=%s",
            self._bucket_name,
            settings.AWS_REGION,
        )

    def get_pdf_url(self, source_id: str) -> tuple[str, str, int]:
        source = self._sources_by_id.get(source_id)

        if source is None:
            raise ValueError(f"Historical source not found: {source_id}")

        expires_in = settings.PDF_URL_EXPIRATION_SECONDS

        try:
            url = self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self._bucket_name,
                    "Key": source["s3_key"],
                },
                ExpiresIn=expires_in,
            )

        except (BotoCoreError, ClientError) as exc:
            logger.exception(
                "Failed to generate S3 presigned URL. source_id=%s key=%s",
                source_id,
                source["s3_key"],
            )

            raise StorageServiceError(
                "Could not generate historical source URL."
            ) from exc

        return source["book_name"], url, expires_in
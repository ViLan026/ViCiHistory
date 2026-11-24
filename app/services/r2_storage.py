from __future__ import annotations

import logging
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.data.sources import HISTORICAL_SOURCES
from app.exceptions import StorageServiceError
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


class R2StorageService(StorageService):
    """Cloudflare R2 adapter using its S3-compatible object API.

    The client is explicitly pointed at Cloudflare's R2 endpoint and does not
    target Amazon S3.
    """

    def __init__(self) -> None:
        self._bucket_name = settings.R2_BUCKET_NAME
        endpoint_url = settings.R2_ENDPOINT_URL.strip() or (
            f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        )
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name="auto",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
        self._sources_by_id = {
            source["source_id"]: {
                "book_name": book_name,
                "object_key": source["object_key"],
            }
            for book_name, source in HISTORICAL_SOURCES.items()
        }
        logger.info("Cloudflare R2 initialized. bucket=%s endpoint=%s", self._bucket_name, endpoint_url)

    def _source(self, source_id: str) -> dict[str, str]:
        source = self._sources_by_id.get(source_id)
        if source is None:
            raise ValueError(f"Historical source not found: {source_id}")
        return source

    def download_pdf(self, source_id: str, destination_path: Path) -> None:
        source = self._source(source_id)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._client.download_file(self._bucket_name, source["object_key"], str(destination_path))
            if not destination_path.exists() or destination_path.stat().st_size == 0:
                raise StorageServiceError(f"Downloaded source is empty: {source_id}")
        except StorageServiceError:
            destination_path.unlink(missing_ok=True)
            raise
        except (BotoCoreError, ClientError, OSError) as exc:
            destination_path.unlink(missing_ok=True)
            logger.exception("R2 download failed. source_id=%s object_key=%s", source_id, source["object_key"])
            raise StorageServiceError(f"Could not download historical source: {source_id}") from exc

    def get_pdf_url(self, source_id: str) -> tuple[str, str, int]:
        source = self._source(source_id)
        expires_in = settings.R2_PRESIGNED_URL_EXPIRATION_SECONDS
        try:
            url = self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self._bucket_name, "Key": source["object_key"]},
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            logger.exception("Could not create R2 presigned URL. source_id=%s", source_id)
            raise StorageServiceError("Could not generate historical source URL.") from exc
        return source["book_name"], url, expires_in

    def close(self) -> None:
        self._client.close()

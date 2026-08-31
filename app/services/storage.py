from __future__ import annotations

import datetime
import logging

import google.auth
from google.auth import impersonated_credentials
from google.cloud import storage

from app.config import settings
from app.data.sources import HISTORICAL_SOURCES

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self) -> None:
        self._client = storage.Client()
        self._bucket = self._client.bucket(settings.GCS_BUCKET_NAME)

        self._sources_by_id = {
            source["source_id"]: {
                "book_name": book_name,
                "object_name": source["object_name"],
            }
            for book_name, source in HISTORICAL_SOURCES.items()
        }

        logger.info("Cloud Storage client initialized. bucket=%s", settings.GCS_BUCKET_NAME)

    def get_pdf_url(self, source_id: str) -> tuple[str, str, int]:
        source = self._sources_by_id.get(source_id)

        if source is None:
            raise ValueError("Historical source not found.")

        credentials, _ = google.auth.default()

        signing_credentials = impersonated_credentials.Credentials(
            source_credentials=credentials,
            target_principal=settings.GCP_SERVICE_ACCOUNT_EMAIL,
            target_scopes=["https://www.googleapis.com/auth/devstorage.read_only"],
            lifetime=3600,
        )

        blob = self._bucket.blob(source["object_name"])

        expiration_minutes = settings.PDF_URL_EXPIRATION_MINUTES

        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiration_minutes),
            method="GET",
            credentials=signing_credentials,
        )

        return source["book_name"], url, expiration_minutes * 60
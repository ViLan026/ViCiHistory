from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StorageService(ABC):
    """Provider-neutral contract for historical source files."""

    @abstractmethod
    def download_pdf(self, source_id: str, destination_path: Path) -> None:
        """Download a source PDF to the given local path."""
        raise NotImplementedError

    @abstractmethod
    def get_pdf_url(self, source_id: str) -> tuple[str, str, int]:
        """Return (book_name, temporary_url, expiry_seconds)."""
        raise NotImplementedError

    def close(self) -> None:
        """Release provider resources, if any."""

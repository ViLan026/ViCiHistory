from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "history_verifier_ai"
    APP_ENV: str = "local"
    APP_HOST: str = "0.0.0.0"
    PORT: int = Field(default=8080, ge=1, le=65535)

    # Optional Hugging Face token. The current embedding model is public,
    # but a token can reduce download throttling during local development.
    HF_TOKEN: str | None = None

    # Qdrant
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_NAME: str = "history_aiteamvn_chunk_256"
    QDRANT_TIMEOUT_SECONDS: float = Field(default=60.0, gt=0)

    # Embedding model MUST match the model used when the collection was indexed.
    EMBEDDING_MODEL: str = "AITeamVN/Vietnamese_Embedding"

    # Gemini
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=2.0)
    GEMINI_MAX_OUTPUT_TOKENS: int = Field(default=2048, gt=0)
    GEMINI_TIMEOUT_MS: int = Field(default=120_000, gt=0)
    GEMINI_MAX_RETRIES: int = Field(default=2, ge=0)

    # Pipeline
    TOP_K: int = Field(default=5, gt=0, le=20)
    MAX_CLAIMS_PER_INPUT: int = Field(default=8, gt=0, le=20)
    MAX_INPUT_CHARS: int = Field(default=12_000, gt=0)
    MAX_EVIDENCE_CHARS: int = Field(default=2_500, gt=0)
    MIN_EVIDENCE_SCORE: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator(
        "QDRANT_URL",
        "QDRANT_COLLECTION_NAME",
        "EMBEDDING_MODEL",
        "GEMINI_MODEL",
    )
    @classmethod
    def text_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Configuration value must not be empty.")
        return value

    @field_validator("QDRANT_API_KEY", "GEMINI_API_KEY")
    @classmethod
    def secret_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Required API key must not be empty.")
        return value

    @field_validator("HF_TOKEN")
    @classmethod
    def optional_token_empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


    GCS_BUCKET_NAME: str = "history-verifier-sources"
    PDF_URL_EXPIRATION_MINUTES: int = Field(default=60, gt=0)
    GCP_SERVICE_ACCOUNT_EMAIL: str

settings = Settings()

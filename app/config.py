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

    # Application
    APP_NAME: str = "history_retrieval"
    APP_ENV: str = "local"
    APP_HOST: str = "0.0.0.0"
    PORT: int = Field(default=8080, ge=1, le=65535)

    # Hugging Face
    HF_TOKEN: str | None = None

    # Qdrant
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_NAME: str = "history_sources_aiteamvn_256"
    QDRANT_TIMEOUT_SECONDS: float = Field(default=60.0, gt=0)

    # Embedding
    EMBEDDING_MODEL: str = "AITeamVN/Vietnamese_Embedding"

    # Ollama / Qwen
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b-instruct"
    OLLAMA_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=2.0)
    OLLAMA_TIMEOUT_SECONDS: float = Field(default=120.0, gt=0)
    OLLAMA_MAX_RETRIES: int = Field(default=2, ge=0)

    # Retrieval pipeline
    TOP_K: int = Field(default=5, gt=0, le=20)
    RETRIEVAL_CANDIDATE_K: int = Field(default=20, gt=0, le=100)
    HYBRID_ALPHA: float = Field(default=0.5, ge=0.0, le=1.0)

    MAX_CLAIMS_PER_INPUT: int = Field(default=8, gt=0, le=20)
    MAX_INPUT_CHARS: int = Field(default=12_000, gt=0)
    MAX_EVIDENCE_CHARS: int = Field(default=2_500, gt=0)
    MIN_EVIDENCE_SCORE: float = Field(default=0.0, ge=0.0, le=1.0)

    BM25_INDEX_PATH: str = "app/data/bm25_index.pkl"

    # AWS / S3
    AWS_REGION: str = "ap-southeast-1"
    S3_BUCKET_NAME: str | None = None
    PDF_URL_EXPIRATION_SECONDS: int = Field(default=3600, gt=0)

    SOURCE_CACHE_DIR: str = ".cache/history_sources"
    PDF_EXCERPT_PAGE_COUNT: int = Field(default=7, ge=1, le=15)

    @field_validator(
        "QDRANT_URL",
        "QDRANT_COLLECTION_NAME",
        "EMBEDDING_MODEL",
        "OLLAMA_URL",
        "OLLAMA_MODEL",
        "BM25_INDEX_PATH",
    )
    @classmethod
    def text_not_empty(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Configuration value must not be empty.")

        return value

    @field_validator("QDRANT_API_KEY")
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


settings = Settings()
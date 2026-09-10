from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env."""

    app_name: str = "Production Text-to-SQL API"
    environment: Literal["development", "test", "staging", "production"] = "development"

    database_url: str = "sqlite:///./data/student.db"

    google_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    # When set, protected endpoints require X-API-Key.
    api_key: str | None = None

    max_result_rows: int = 500
    max_sql_length: int = 4_000
    max_agent_retries: int = 2
    request_timeout_seconds: int = 60

    allowed_origins: str = "http://localhost:8501"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


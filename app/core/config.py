"""Typed application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables or an optional `.env` file."""

    app_name: str = "Skits Strategos Backend"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./skits_strategos.db"
    debug: bool = False
    max_upload_bytes: int = 25_000_000
    artifact_directory: str = "./artifacts"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def get_settings() -> Settings:
    """Load application settings for the application entry point."""

    return Settings()

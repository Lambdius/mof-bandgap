from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    mof_site_base_url: str = "https://ec-mof.njit.edu"
    scraper_click_timeout_ms: int = 10_000
    scraper_page_load_timeout_ms: int = 15_000
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/mof_bandgap"
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "mof-cif"
    minio_secure: bool = False

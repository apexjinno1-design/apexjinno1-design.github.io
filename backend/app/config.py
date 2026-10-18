from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./research.db"
    massive_api_key: SecretStr = SecretStr("")
    massive_requests_per_minute: int = Field(default=5, ge=1, le=1000)
    cors_origins: list[str] = ["http://localhost:3000"]
    demo_mode: bool = False
    scheduler_enabled: bool = False
    initial_refresh_enabled: bool = False
    ingest_symbols: str = "SPY,QQQ,IWM"
    sec_user_agent: str = ""

    @field_validator("database_url")
    @classmethod
    def normalize_postgres_url(cls, value: str) -> str:
        # Managed hosts return a driver-neutral URL; this project pins psycopg 3.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

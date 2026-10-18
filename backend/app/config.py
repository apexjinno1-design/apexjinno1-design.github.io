from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./research.db"
    massive_api_key: SecretStr = SecretStr("")
    cors_origins: list[str] = ["http://localhost:3000"]
    demo_mode: bool = False
    scheduler_enabled: bool = False
    ingest_symbols: str = "SPY,QQQ,IWM"
    sec_user_agent: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()

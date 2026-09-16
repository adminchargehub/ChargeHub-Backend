from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://chargehub:chargehub@localhost:5432/chargehub"

    secret_key: str = "dev-only-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    environment: str = "development"

    # NoDecode stops pydantic-settings from trying to JSON-parse the env var
    # before our validator runs, which is what lets us accept a plain
    # comma-separated list instead of requiring '["http://..."]'.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and settings.secret_key == "dev-only-change-me":
        raise RuntimeError("SECRET_KEY must be set to a real value in production")
    return settings


settings = get_settings()

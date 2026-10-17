from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FastAPI Template"
    app_version: str = "0.1.0"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]
    database_url: str = "sqlite:///./app.db"

    # Klucz do podpisywania tokenów JWT. Brak wartości w zmiennych środowiskowych
    # blokuje start aplikacji (brak domyślnego sekretu). Minimum 32 znaki.
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    # Czas życia tokenu JWT w minutach (po tym czasie token wygasa automatycznie).
    access_token_expire_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

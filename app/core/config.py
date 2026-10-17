from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env (jeśli istnieje) nadpisuje wartości z .env.example
    model_config = SettingsConfigDict(
        env_file=(".env.example", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "FastAPI Template"
    app_version: str = "0.1.0"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]

    # API dane.um.warszawa.pl
    api_key: str = ""
    um_api_base_url: str = "https://dane.um.warszawa.pl/api/action"
    um_api_cache_seconds: int = 300
    um_action_pogoda: str = "get_zom_pogoda"
    um_action_powietrze: str = "get_bopipk_monitoring_jakosci_powietrza"
    um_action_boiska: str = "get_be_otwarte_boiska"
    um_action_zajecia: str = "get_bmm_zajecia_sportowe"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

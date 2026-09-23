from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_prefix: str = "/api"
    database_url: str
    supabase_url: str
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "emc-veritas"
    session_secret: str
    cookie_secure: bool = False
    public_app_url: str = "http://localhost:5173"
    frontend_origins_raw: str = Field(
        default="http://localhost:5173", validation_alias="FRONTEND_ORIGINS"
    )

    @property
    def frontend_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

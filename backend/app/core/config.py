from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables. No secrets hardcoded.

    SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are optional in Phase 1: when absent,
    the DB layer falls back to a local JSON-file store (backend/data/db.json) so the
    app boots and is fully testable without a provisioned Supabase project. Supply
    both to switch to the real database with no code changes (see app/db/repository.py).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "EcomOS AI Backend"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    cors_origins: list[str] = ["http://localhost:3000"]

    rate_limit_requests_per_minute: int = 30

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()

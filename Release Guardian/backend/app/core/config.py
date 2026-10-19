from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Release Guardian"
    environment: str = "development"
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./release_guardian.db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14

    worker_mode: str = "celery"  # celery | inline
    run_timeout_seconds: int = 300
    step_timeout_seconds: int = 60
    max_redirects: int = 5
    allow_private_urls: bool = False

    rate_limit_auth_per_minute: int = 20
    rate_limit_api_per_minute: int = 300

    s3_endpoint_url: str | None = None
    s3_bucket: str = "release-guardian"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None

    cors_origins: list[str] = ["http://localhost:3000"]

    webhook_signing_secret: str = "change-me-webhook-secret"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

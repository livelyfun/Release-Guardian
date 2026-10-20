from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Release Guardian"
    environment: str = "development"
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./release_guardian.db"
    db_pool_size: int = Field(default=10, ge=1, le=200)
    db_max_overflow: int = Field(default=20, ge=0, le=200)
    db_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14

    worker_mode: str = "celery"  # celery | inline
    run_timeout_seconds: int = 300
    pending_run_timeout_seconds: int = 120
    stale_run_sweep_batch: int = 100
    escalation_sweep_batch: int = 200
    step_timeout_seconds: int = 60
    max_redirects: int = 5
    allow_private_urls: bool = False

    rate_limit_auth_per_minute: int = 20
    rate_limit_api_per_minute: int = 300
    rate_limit_backend: str = "auto"  # auto | memory | redis

    # Backpressure: bound queued/executing work per monitor and workspace.
    max_active_runs_per_monitor: int = 1
    max_active_runs_per_workspace: int = 50

    # Delivery retries: total attempts includes the first send.
    notification_max_attempts: int = Field(default=4, ge=1, le=10)
    notification_retry_base_seconds: int = Field(default=30, ge=1, le=3600)
    notification_retry_max_seconds: int = Field(default=900, ge=1, le=86400)
    notification_sweep_batch: int = Field(default=100, ge=1, le=1000)

    log_level: str = "INFO"
    metrics_enabled: bool = True
    metrics_token: str | None = None
    readiness_check_redis: bool = True

    s3_endpoint_url: str | None = None
    s3_bucket: str = "release-guardian"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = True
    s3_force_path_style: bool = False
    artifact_url_ttl_seconds: int = 900

    cors_origins: list[str] = ["http://localhost:3000"]

    webhook_signing_secret: str = "change-me-webhook-secret"

    @field_validator("environment", "worker_mode", "rate_limit_backend")
    @classmethod
    def _normalize_choice(cls, value: str) -> str:
        return value.strip().lower()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

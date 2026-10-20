"""Production configuration guardrails.

Configuration mistakes that are harmless in development become security or
availability incidents in production (default JWT secret, SQLite, private URL
access).  ``validate_production_settings`` fails fast at startup instead of
serving traffic with an unsafe configuration.
"""

from __future__ import annotations

from app.core.config import Settings

_DEFAULT_JWT_SECRETS = {"change-me-in-production", "secret", ""}
_DEFAULT_WEBHOOK_SECRETS = {"change-me-webhook-secret", ""}


def production_config_issues(config: Settings) -> list[str]:
    """Return human-readable misconfigurations for a production environment."""
    issues: list[str] = []

    if config.jwt_secret in _DEFAULT_JWT_SECRETS:
        issues.append("JWT_SECRET must be overridden with a strong random value")
    elif len(config.jwt_secret) < 32:
        issues.append("JWT_SECRET must be at least 32 characters")

    if config.webhook_signing_secret in _DEFAULT_WEBHOOK_SECRETS:
        issues.append("WEBHOOK_SIGNING_SECRET must be overridden")
    elif len(config.webhook_signing_secret) < 16:
        issues.append("WEBHOOK_SIGNING_SECRET must be at least 16 characters")

    if config.database_url.startswith("sqlite"):
        issues.append("DATABASE_URL must use a production database, not SQLite")

    if config.allow_private_urls:
        issues.append("ALLOW_PRIVATE_URLS must be false in production")

    if "*" in config.cors_origins:
        issues.append("CORS_ORIGINS must not allow every origin")

    if config.worker_mode not in {"celery", "inline"}:
        issues.append("WORKER_MODE must be 'celery' or 'inline'")

    if config.rate_limit_backend not in {"auto", "memory", "redis"}:
        issues.append("RATE_LIMIT_BACKEND must be 'auto', 'memory', or 'redis'")

    return issues


def validate_production_settings(config: Settings) -> None:
    """Raise when production starts with unsafe or incomplete configuration."""
    if config.environment.strip().lower() != "production":
        return
    issues = production_config_issues(config)
    if issues:
        raise RuntimeError(
            "Refusing to start in production with unsafe configuration: " + "; ".join(issues)
        )

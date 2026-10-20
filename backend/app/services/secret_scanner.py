"""Secret scanning for Release Guardian configuration and environment values.

The scanner flags accidental credential exposure in environment variables and
settings before those values reach logs, artifacts, or support bundles.  It is
used by ``python -m app.services.secret_scanner`` and can gate CI.

Findings only contain masked values; raw secrets are never returned.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecretScanResult:
    """Result of a secret scan operation."""

    def __init__(
        self,
        found: bool,
        secret_type: str,
        value: str | None = None,
        location: str | None = None,
        severity: str = "medium",
    ) -> None:
        self.found = found
        self.secret_type = secret_type
        self.value = value  # masked value
        self.location = location
        self.severity = severity  # low, medium, high, critical


# (pattern, secret_type, description)
_SECRET_PATTERNS: list[tuple[str, str, str]] = [
    (r"rg_[a-zA-Z0-9]{20,}", "api_key", "RG API key (rg_ prefix)"),
    (r"postgresql(?:\+psycopg)?://[^\s]+", "db_url", "Database connection URL"),
    (r"mysql://[^\s]+", "db_url", "MySQL connection URL"),
    (r"mongodb://[^\s]+", "db_url", "MongoDB connection URL"),
    (r"jwt_secret\s*=\s*['\"]([^'\"]{8,})['\"]", "jwt_secret", "JWT signing secret"),
    (r"[a-f0-9]{32,}", "api_token", "Long hexadecimal token"),
    (r"xoxb-[a-zA-Z0-9]{10,}", "slack_token", "Slack bot token"),
    (r"password\s*=\s*['\"]([^'\"]{4,})['\"]", "password", "Password value"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "private_key", "Private key"),
]


def mask_secret(value: str) -> str:
    """Mask a secret value for safe display."""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def _severity_for(secret_type: str) -> str:
    critical_types = {"jwt_secret", "api_key", "db_url", "private_key"}
    high_types = {"api_token", "slack_token"}
    if secret_type in critical_types:
        return "critical"
    if secret_type in high_types:
        return "high"
    return "medium"


def _scan_values(values: dict[str, Any], prefix: str) -> list[SecretScanResult]:
    findings: list[SecretScanResult] = []
    for key, value in values.items():
        if not isinstance(value, str) or not value:
            continue
        for pattern, secret_type, _description in _SECRET_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                findings.append(
                    SecretScanResult(
                        found=True,
                        secret_type=secret_type,
                        value=mask_secret(value),
                        location=f"{prefix}.{key}",
                        severity=_severity_for(secret_type),
                    )
                )
    return findings


def scan_config(config_dict: dict[str, Any], prefix: str = "config") -> list[SecretScanResult]:
    """Scan a configuration dictionary for potential secrets."""
    return _scan_values(config_dict, prefix)


def scan_environment_vars() -> list[SecretScanResult]:
    """Scan environment variables for potential secrets."""
    return _scan_values(dict(os.environ), "env")


def get_security_status() -> dict[str, Any]:
    """Return a redacted summary of configuration and environment findings."""
    env_findings = scan_environment_vars()
    config_findings = scan_config(vars(settings))
    all_findings = env_findings + config_findings

    by_severity: dict[str, int] = {"critical": 0, "high": 0, "medium": 0}
    for finding in all_findings:
        by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1

    return {
        "scan_timestamp": datetime.now(UTC).isoformat(),
        "environment_variables_scanned": len(os.environ),
        "configuration_values_scanned": len(vars(settings)),
        "findings_count": len(all_findings),
        "critical_findings": by_severity["critical"],
        "high_findings": by_severity["high"],
        "medium_findings": by_severity["medium"],
        "is_secure": by_severity["critical"] == 0 and by_severity["high"] == 0,
        "findings": [
            {
                "type": finding.secret_type,
                "location": finding.location,
                "severity": finding.severity,
                "masked_value": finding.value,
            }
            for finding in all_findings
        ],
    }


def main() -> int:
    """CLI entry point. Exits non-zero when high/critical findings exist."""
    import json

    status = get_security_status()
    print(json.dumps(status, indent=2))
    return 0 if status["is_secure"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

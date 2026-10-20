"""Secret scanning for Release Guardian - detects potential secrets in configuration and code.

This service scans for common secret patterns in environment variables, configuration,
and other sources to prevent accidental credential exposure.

Supported patterns:
- API keys (rg_ prefix format)
- Database URLs
- JWT secrets
- Generic token patterns
"""

import re
import logging
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecretScanResult:
    """Result of a secret scan operation."""
    def __init__(self, found: bool, secret_type: str, value: str | None = None,
                 location: str | None = None, severity: str = "medium"):
        self.found = found
        self.secret_type = secret_type
        self.value = value  # masked/redacted value
        self.location = location
        self.severity = severity  # low, medium, high, critical


# Common secret patterns
_SECRET_PATTERNS = [
    # API keys (rg_ prefix)
    (r"rg_[a-zA-Z0-9]{20,}", "api_key", "RG API key (rg_ prefix)"),
    # Database URLs
    (r"postgresql+psycopg://[^\s]+", "db_url", "Database connection URL"),
    (r"mysql://[^\s]+", "db_url", "MySQL connection URL"),
    (r"mongodb://[^\s]+", "db_url", "MongoDB connection URL"),
    # JWT secrets (short secrets are weak)
    (r"jwt_secret\s*=\s*['\"]]([^'\"]{8,})['\"]", "jwt_secret", "JWT signing secret"),
    # Generic token patterns (32+ char hex strings)
    (r"[a-f0-9]{32,}", "api_token", "Long hexadecimal token"),
    # Slack tokens
    (r"xoxb-[a-zA-Z0-9]{10,}", "slack_token", "Slack bot token"),
    # Generic password patterns
    (r"password\s*=\s*['\"]]([^'\"]{4,})['\"]", "password", "Password value"),
]


def scan_config(config_dict: dict, prefix: str = "config") -> List[SecretScanResult]:
    """Scan a configuration dictionary for potential secrets."""
    findings: List[SecretScanResult] = []

    for pattern, secret_type, description in _SECRET_PATTERNS:
        for key, value in config_dict.items():
            if isinstance(value, str):
                match = re.search(pattern, value, re.IGNORECASE)
                if match:
                    # Mask the secret value
                    masked = mask_secret(value)
                    findings.append(SecretScanResult(
                        found=True,
                        secret_type=secret_type,
                        value=masked,
                        location=f"{prefix}.{key}",
                        severity=_determine_secret_type(secret_type),
                    ))

    return results


def mask_secret(value: str) -> str:
    """Mask a secret value for safe display."""
    if len(value) <= 4:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def _determine_secret_type(secret_type: str) -> str:
    """Determine severity based on secret type."""
    critical_types = {"jwt_secret", "api_key", "db_url"}
    high_types = {"api_token", "slack_token"}
    if secret_type in critical_types:
        return "critical"
    if secret_type in high_types:
        return "high"
    return "medium"


def scan_environment_vars() -> List[SecretScanResult]:
    """Scan environment variables for potential secrets."""
    import os

    findings: List[SecretScanResult] = []
    env_vars = {k: v for k, v in os.environ.items()}

    for pattern, secret_type, description in _SECRET_PATTERNS:
        for key, value in env_vars.items():
            if isinstance(value, str):
                match = re.search(pattern, value, re.IGNORECASE)
                if match:
                    masked = mask_secret(value)
                    findings.append(SecretScanResult(
                        found=True,
                        secret_type=secret_type,
                        value=masked,
                        location=f"env.{key}",
                        severity=_determine_secret_type(secret_type),
                    ))

    return findings


def get_security_status() -> dict[str, Any]:
    """Get overall security status summary."""
    env_scan = scan_environment_vars()
    config_scan = scan_config(vars(settings)) if hasattr(settings, '__dict__') else []

    critical_count = sum(1 for f in env_scan + config_scan if f.severity == "critical")
    high_count = sum(1 for f in env_scan + config_scan if f.severity == "high")
    medium_count = sum(1 for f in env_scan + config_scan if f.severity == "medium")

    return {
        "scan_timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        "environment_variables_scanned": len(env_scan),
        "configuration_scanned": len(config_scan),
        "critical_findings": critical_count,
        "high_findings": high_count,
        "medium_findings": medium_count,
        "is_secure": critical_count == 0 and high_count == 0,
        "findings": [
            {
                "type": f.secret_type,
                "location": f.location,
                "severity": f.severity,
                "masked_value": f.value,
            }
            for f in env_scan + config_scan
        ],
    }
"""SSRF defenses for user-supplied monitoring targets.

Application-layer validation complements (never replaces) network egress controls.
See docs/master-plan/release-guardian/08-SECURITY-AND-THREAT-MODEL.md.
"""

import ipaddress
import socket
from typing import NoReturn
from urllib.parse import urlparse

from app.core.metrics import BLOCKED_URLS

ALLOWED_SCHEMES = {"http", "https"}


class UrlValidationError(ValueError):
    pass


def _reject(reason: str, message: str) -> NoReturn:
    BLOCKED_URLS.inc(reason=reason)
    raise UrlValidationError(message)


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return any(
        (
            not ip.is_global,
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_reserved,
            ip.is_multicast,
            ip.is_unspecified,
        )
    )


def resolve_host(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        BLOCKED_URLS.inc(reason="dns_failure")
        raise UrlValidationError(f"Could not resolve host: {host}") from exc
    return sorted({info[4][0] for info in infos})


def validate_url(url: str, allow_private: bool = False) -> str:
    """Validate scheme, host, and resolved destination addresses."""

    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        _reject("scheme", "Only http and https targets are supported")
    if not parsed.hostname:
        _reject("missing_host", "Target URL must include a host")

    host = parsed.hostname
    # Block obvious literal private hosts before DNS resolution.
    try:
        literal = ipaddress.ip_address(host)
        if not allow_private and _is_blocked_ip(literal):
            _reject("blocked_address", "Target resolves to a disallowed address")
        return url
    except ValueError:
        pass

    for address in resolve_host(host):
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        if not allow_private and _is_blocked_ip(ip):
            _reject("blocked_address", "Target resolves to a disallowed address")

    return url

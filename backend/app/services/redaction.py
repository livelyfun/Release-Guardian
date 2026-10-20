"""Artifact redaction helpers.

HAR files are the highest-risk browser artifact: they include request and
response headers, cookies, query strings, and form bodies.  Redact known
credential carriers before an artifact leaves the worker.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REDACTED = "[REDACTED]"

SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
    "x-xsrf-token",
}

SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "code",
    "credential",
    "csrf",
    "id_token",
    "key",
    "password",
    "passwd",
    "refresh_token",
    "secret",
    "session",
    "sessionid",
    "sig",
    "signature",
    "token",
}


def _is_sensitive(name: object) -> bool:
    return isinstance(name, str) and name.strip().lower().replace("-", "_") in SENSITIVE_KEYS


def _redact_pairs(pairs: object) -> int:
    if not isinstance(pairs, list):
        return 0
    count = 0
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        if _is_sensitive(pair.get("name")):
            pair["value"] = REDACTED
            count += 1
    return count


def _redact_headers(headers: object) -> int:
    if not isinstance(headers, list):
        return 0
    count = 0
    for header in headers:
        if not isinstance(header, dict):
            continue
        name = header.get("name")
        if isinstance(name, str) and name.strip().lower() in SENSITIVE_HEADERS:
            if header.get("value") != REDACTED:
                header["value"] = REDACTED
                count += 1
    return count


def _redact_cookies(cookies: object) -> int:
    if not isinstance(cookies, list):
        return 0
    count = 0
    for cookie in cookies:
        if isinstance(cookie, dict) and cookie.get("value") != REDACTED:
            cookie["value"] = REDACTED
            count += 1
    return count


def _redact_json(value: object) -> tuple[object, int]:
    if isinstance(value, dict):
        count = 0
        for key, item in list(value.items()):
            if _is_sensitive(key):
                value[key] = REDACTED
                count += 1
            else:
                value[key], nested = _redact_json(item)
                count += nested
        return value, count
    if isinstance(value, list):
        count = 0
        for index, item in enumerate(value):
            value[index], nested = _redact_json(item)
            count += nested
        return value, count
    return value, 0


def _redact_form_body(text: str) -> tuple[str, int]:
    pairs = parse_qsl(text, keep_blank_values=True)
    count = sum(1 for name, _value in pairs if _is_sensitive(name))
    if count == 0:
        return text, 0
    return urlencode([(name, REDACTED if _is_sensitive(name) else value) for name, value in pairs]), count


def _redact_post_data(post_data: object) -> int:
    if not isinstance(post_data, dict):
        return 0
    count = _redact_pairs(post_data.get("params"))
    text = post_data.get("text")
    mime_type = str(post_data.get("mimeType") or "").lower()
    if not isinstance(text, str) or not text:
        return count

    if "application/x-www-form-urlencoded" in mime_type:
        redacted, replacements = _redact_form_body(text)
        if replacements:
            post_data["text"] = redacted
        return count + replacements

    if "json" in mime_type:
        try:
            parsed = json.loads(text)
        except ValueError:
            return count
        parsed, replacements = _redact_json(parsed)
        if replacements:
            post_data["text"] = json.dumps(parsed)
        return count + replacements

    return count


def redact_har(data: bytes) -> tuple[bytes, int]:
    """Redact credentials from a HAR payload, returning the new bytes and count."""
    har = json.loads(data)
    count = 0
    log = har.get("log") if isinstance(har, dict) else None
    entries = log.get("entries") if isinstance(log, dict) else None
    if not isinstance(entries, list):
        raise ValueError("HAR payload is missing log.entries")

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for side in ("request", "response"):
            message = entry.get(side)
            if not isinstance(message, dict):
                continue
            count += _redact_headers(message.get("headers"))
            count += _redact_cookies(message.get("cookies"))
            count += _redact_pairs(message.get("queryString"))
            count += _redact_post_data(message.get("postData"))

    return json.dumps(har).encode("utf-8"), count


def redact_url(url: str) -> str:
    """Redact sensitive query parameters from a URL for logs and summaries."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    if not parts.query:
        return url
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    if not any(_is_sensitive(name) for name, _value in pairs):
        return url
    redacted = urlencode(
        [(name, REDACTED if _is_sensitive(name) else value) for name, value in pairs]
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, redacted, parts.fragment))

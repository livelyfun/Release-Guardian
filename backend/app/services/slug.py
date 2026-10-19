import re
import secrets

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    base = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return base or "item"


def unique_slug(value: str) -> str:
    return f"{slugify(value)}-{secrets.token_hex(3)}"


def api_key() -> tuple[str, str, str]:
    """Return (plaintext_key, prefix, sha256_hash)."""

    import hashlib

    raw = f"rg_{secrets.token_urlsafe(32)}"
    prefix = raw[:10]
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, prefix, digest


def hash_api_key(raw: str) -> str:
    import hashlib

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

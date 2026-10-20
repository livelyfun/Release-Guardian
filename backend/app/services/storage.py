"""S3-compatible object storage for Release Guardian artifacts.

Artifacts (screenshots, traces, HAR, Lighthouse reports) live in
S3-compatible storage that can branch with the database.  The service provides
upload, signed-URL generation, listing, and deletion.  Callers remain
responsible for tenant authorization; the API layer enforces workspace
membership before issuing a signed URL.

Env vars (see ``backend/.env.example``):

- S3_ENDPOINT_URL
- S3_BUCKET
- S3_ACCESS_KEY
- S3_SECRET_KEY
- S3_REGION
- S3_USE_SSL
- S3_FORCE_PATH_STYLE
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.core.metrics import ARTIFACT_UPLOADS

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError

    HAS_BOTO3 = True
except ImportError:  # pragma: no cover - boto3 is optional in test environments
    HAS_BOTO3 = False
    ClientError = Exception  # type: ignore[assignment,misc]
    BotoCoreError = Exception  # type: ignore[assignment,misc]
    Config = None  # type: ignore[assignment,misc]


class StorageError(RuntimeError):
    """Raised when storage operations fail."""


def storage_enabled() -> bool:
    """Return True when boto3 and the minimum S3 configuration are present."""
    return bool(HAS_BOTO3 and settings.s3_bucket)


def _client() -> Any:
    """Return a boto3 S3 client built from settings."""
    if not HAS_BOTO3:
        raise StorageError("boto3 is not available. Install boto3 to use artifact storage.")
    kwargs: dict[str, Any] = {
        "endpoint_url": settings.s3_endpoint_url,
        "region_name": settings.s3_region or "us-east-1",
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
        "use_ssl": settings.s3_use_ssl,
    }
    if settings.s3_force_path_style and Config is not None:
        kwargs["config"] = Config(s3={"addressing_style": "path"})
    return boto3.client("s3", **kwargs)


def _bucket() -> str:
    return settings.s3_bucket


def _object_key(run_id: str, kind: str, extension: str | None = None) -> str:
    """Build a deterministic, collision-resistant object key."""
    digest = hashlib.sha256(f"{run_id}:{kind}".encode()).hexdigest()[:12]
    suffix = f".{extension.lstrip('.')}" if extension else ""
    return f"artifacts/{run_id}/{kind}-{digest}{suffix}"


def _presigned_url(client: Any, key: str, expires_in: int) -> str:
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": _bucket(), "Key": key},
        ExpiresIn=expires_in,
    )


def upload_bytes(
    run_id: str,
    kind: str,
    data: bytes,
    mime_type: str | None = None,
    extension: str | None = None,
) -> dict[str, Any]:
    """Upload raw bytes and return metadata including a signed URL."""
    key = _object_key(run_id, kind, extension)
    try:
        client = _client()
    except StorageError:
        ARTIFACT_UPLOADS.inc(kind=kind, status="failure")
        raise

    extra_args: dict[str, Any] = {
        "Metadata": {
            "run_id": run_id,
            "kind": kind,
            "uploaded_at": datetime.now(UTC).isoformat(),
        }
    }
    if mime_type:
        extra_args["ContentType"] = mime_type

    try:
        client.put_object(Bucket=_bucket(), Key=key, Body=data, **extra_args)
        url = _presigned_url(client, key, settings.artifact_url_ttl_seconds)
    except (ClientError, BotoCoreError) as exc:
        ARTIFACT_UPLOADS.inc(kind=kind, status="failure")
        raise StorageError(f"Failed to upload artifact: {exc}") from exc

    ARTIFACT_UPLOADS.inc(kind=kind, status="success")
    return {
        "storage_key": key,
        "url": url,
        "mime_type": mime_type or _infer_mime(kind),
        "size_bytes": len(data),
    }


def upload_fileobj(
    run_id: str,
    kind: str,
    fileobj: Any,
    mime_type: str | None = None,
    extension: str | None = None,
) -> dict[str, Any]:
    """Upload from a file-like object (large traces/HAR archives)."""
    key = _object_key(run_id, kind, extension)
    try:
        client = _client()
    except StorageError:
        ARTIFACT_UPLOADS.inc(kind=kind, status="failure")
        raise

    extra_args: dict[str, Any] = {
        "Metadata": {"run_id": run_id, "kind": kind},
    }
    if mime_type:
        extra_args["ContentType"] = mime_type

    try:
        client.upload_fileobj(fileobj, _bucket(), key, ExtraArgs=extra_args)
        url = _presigned_url(client, key, settings.artifact_url_ttl_seconds)
    except (ClientError, BotoCoreError) as exc:
        ARTIFACT_UPLOADS.inc(kind=kind, status="failure")
        raise StorageError(f"Failed to upload artifact: {exc}") from exc

    ARTIFACT_UPLOADS.inc(kind=kind, status="success")
    return {
        "storage_key": key,
        "url": url,
        "mime_type": mime_type or _infer_mime(kind),
    }


def get_signed_url(storage_key: str, expires_in: int | None = None) -> str:
    """Return a short-lived signed URL for an existing artifact key."""
    ttl = expires_in if expires_in is not None else settings.artifact_url_ttl_seconds
    return _presigned_url(_client(), storage_key, ttl)


def list_artifacts(
    run_id: str | None = None,
    prefix: str | None = None,
) -> list[dict[str, Any]]:
    """List artifacts, optionally filtered by run id or key prefix."""
    client = _client()

    if run_id:
        prefix = f"artifacts/{run_id}/"
    elif prefix:
        prefix = prefix if prefix.endswith("/") else prefix + "/"
    else:
        prefix = "artifacts/"

    try:
        result = client.list_objects_v2(Bucket=_bucket(), Prefix=prefix)
    except (ClientError, BotoCoreError) as exc:
        raise StorageError(f"Failed to list artifacts: {exc}") from exc

    items: list[dict[str, Any]] = []
    for obj in result.get("Contents", []):
        key = obj["Key"]
        relative = key[len(prefix) :] if key.startswith(prefix) else key
        items.append(
            {
                "storage_key": key,
                "url": _presigned_url(client, key, settings.artifact_url_ttl_seconds),
                "kind": _kind_from_key(relative),
                "size_bytes": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            }
        )
    return items


def delete_artifact(storage_key: str) -> bool:
    """Delete a single artifact by its storage key."""
    try:
        _client().delete_object(Bucket=_bucket(), Key=storage_key)
    except (ClientError, BotoCoreError) as exc:
        raise StorageError(f"Failed to delete artifact: {exc}") from exc
    return True


def _infer_mime(kind: str) -> str:
    mapping = {
        "screenshot": "image/png",
        "trace": "application/json",
        "har": "application/json",
        "lighthouse": "application/json",
    }
    return mapping.get(kind, "application/octet-stream")


def _kind_from_key(key: str) -> str:
    """Extract the artifact kind from ``<kind>-<hash>[.ext]``."""
    filename = key.rsplit("/", 1)[-1]
    stem = filename.split(".", 1)[0]
    dash_index = stem.find("-")
    return stem[:dash_index] if dash_index > 0 else "unknown"

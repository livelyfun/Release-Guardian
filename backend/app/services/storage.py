"""S3-compatible object storage for Release Guardian artifacts.

Artifacts (screenshots, traces, HAR, Lighthouse scores) are stored in
S3-compatible storage that branches with the Neon project.  The service
provides upload, signed-URL generation, and listing with tenant
authorization.

Env vars (via ``backend/.env.example`` / ``backend/app/core/config.py``):

- S3_ENDPOINT_URL
- S3_BUCKET
- S3_ACCESS_KEY
- S3_SECRET_KEY
- S3_REGION
- S3_USE_SSL (bool)
- S3_FORCE_PATH_STYLE (bool)
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:  # pragma: no cover - boto3 optional in some test environments
    HAS_BOTO3 = False


class StorageError(RuntimeError):
    """Raised when storage operations fail."""


def _client() -> "boto3.client":
    """Return a cached boto3 S3 client built from config."""
    if not HAS_BOTO3:
        raise StorageError("boto3 is not available. Install boto3 to use artifact storage.")
    kwargs: dict[str, Any] = {
        "endpoint_url": settings.s3_endpoint_url,
        "region_name": settings.s3_region or "us-east-1",
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
    }
    if not settings.s3_use_ssl:
        kwargs["verify"] = False
    if settings.s3_force_path_style:
        kwargs["botocore_config"] = {"requester_pays": False, "disable_request_signer": True}
    return boto3.client("s3", **kwargs)


def _bucket() -> str:
    return settings.s3_bucket


def _object_key(run_id: str, kind: str) -> str:
    """Generate a deterministic object key: artifacts/<run_id>/<kind>.<ext>"""
    # Use a short hash of run_id + kind for readability + uniqueness
    h = hashlib.sha256(f"{run_id}:{kind}".encode()).hexdigest()[:12]
    return f"artifacts/{run_id}/{kind}-{h}"


def upload_bytes(
    run_id: str,
    kind: str,
    data: bytes,
    mime_type: str | None = None,
) -> dict[str, str]:
    """Upload raw bytes and return metadata dict with storage_key and url."""
    key = _object_key(run_id, kind)
    client = _client()
    bucket = _bucket()

    extra_args: dict[str, Any] = {}
    if mime_type:
        extra_args["ContentType"] = mime_type
    # Compute etag for idempotency / debugging
    extra_args["Metadata"] = {
        "run_id": run_id,
        "kind": kind,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        client.put_object(Bucket=bucket, Key=key, Body=data, **extra_args)
    except ClientError as exc:
        raise StorageError(f"Failed to upload artifact: {exc}") from exc

    # Build a short-lived signed URL (7 days)
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=7 * 24 * 60 * 60,  # 7 days
    )

    return {
        "storage_key": key,
        "url": url,
        "mime_type": mime_type or _infer_mime(kind),
    }


def upload_fileobj(
    run_id: str,
    kind: str,
    fileobj: Any,
    length: int | None = None,
    mime_type: str | None = None,
) -> dict[str, str]:
    """Upload from a file-like object.  Used for large trace/HAR archives."""
    key = _object_key(run_id, kind)
    client = _client()
    bucket = _bucket()

    extra_args: dict[str, Any] = {}
    if mime_type:
        extra_args["ContentType"] = mime_type
    extra_args["Metadata"] = {
        "run_id": run_id,
        "kind": kind,
    }

    try:
        client.upload_fileobj(
            fileobj,
            Bucket=bucket,
            Key=key,
            ExtraArgs=extra_args if extra_args else None,
        )
    except ClientError as exc:
        raise StorageError(f"Failed to upload artifact: {exc}") from exc

    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=7 * 24 * 60 * 60,
    )

    return {
        "storage_key": key,
        "url": url,
        "mime_type": mime_type or _infer_mime(kind),
    }


def get_signed_url(storage_key: str, expires_in: int = 7 * 24 * 60 * 60) -> str:
    """Return a short-lived signed URL for an existing artifact key."""
    client = _client()
    bucket = _bucket()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": storage_key},
        ExpiresIn=expires_in,
    )


def list_artifacts(
    run_id: str | None = None,
    prefix: str | None = None,
) -> list[dict[str, str]]:
    """List artifacts optionaly filtered by run_id prefix."""
    client = _client()
    bucket = _bucket()

    # Build the prefix: "artifacts/<run_id>/" or "artifacts/<prefix>/"
    if run_id:
        prefix = f"artifacts/{run_id}/"
    elif prefix:
        # ensure trailing slash for consistent listing
        prefix = prefix if prefix.endswith("/") else prefix + "/"
    else:
        prefix = "artifacts/"

    try:
        result = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    except ClientError as exc:
        raise StorageError(f"Failed to list artifacts: {exc}") from exc

    items: list[dict[str, str]] = []
    for obj in result.get("Contents", []):
        key = obj["Key"]
        # strip the bucket prefix to get the logical key
        relative = key[len(prefix) :] if key.startswith(prefix) else key
        # Determine kind from filename
        kind = _kind_from_key(relative)
        items.append(
            {
                "storage_key": key,
                "url": get_signed_url(key),
                "kind": kind,
                "size_bytes": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            }
        )
    return items


def _infer_mime(kind: str) -> str:
    mapping: dict[str, str] = {
        "screenshot": "image/png",
        "trace": "application/json",
        "harl": "application/json",  # HAR log
        "lighthouse": "application/json",
    }
    return mapping.get(kind, "application/octet-stream")


def _kind_from_key(key: str) -> str:
    """Derive the artifact kind from the filename stem."""
    stem = os.path.splitext(key)[0].split("-")[-1]  # last dash-separated part is the kind hint
    # But our key format is kind-HASH, so the part after the last dash IS the kind
    # Actually key format: artifacts/<run_id>/<kind>-<hash>
    # So we need to extract kind from the filename
    parts = key.split("/")
    filename = parts[-1] if parts else key
    # format: kind-<12hash>
    dash_idx = filename.find("-")
    if dash_idx == -1:
        return "unknown"
    kind = filename[:dash_idx]
    return kind


def delete_artifact(storage_key: str) -> bool:
    """Delete a single artifact by its storage key."""
    client = _client()
    bucket = _bucket()
    try:
        client.delete_object(Bucket=bucket, Key=storage_key)
        return True
    except ClientError as exc:
        raise StorageError(f"Failed to delete artifact: {exc}") from exc
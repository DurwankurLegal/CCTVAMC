"""S3-compatible object storage for media/documents (SRS 4.17/4.18).

Uses boto3 against the configured S3 endpoint (MinIO in dev, S3 in prod). When
storage is not configured (e.g. unit tests), uploads are skipped gracefully and
a local-style key is returned so callers still record a Document row.
"""
from __future__ import annotations

import uuid
from functools import lru_cache

from app.core.config import get_settings


@lru_cache
def _client():
    settings = get_settings()
    if not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY:
        return None
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
    )


def build_key(tenant_id, entity_type: str, file_name: str) -> str:
    return f"{tenant_id}/{entity_type}/{uuid.uuid4().hex}_{file_name}"


def upload_bytes(key: str, data: bytes, content_type: str | None = None) -> str:
    """Upload bytes to S3 and return a URL. Returns a synthetic URL when storage
    is unconfigured or unreachable (dev/test), so media handling never 500s the
    request — the failure is logged for follow-up."""
    settings = get_settings()
    client = _client()
    if client is None:
        return f"local://{settings.S3_BUCKET}/{key}"
    base = (settings.S3_ENDPOINT_URL or "").rstrip("/")
    try:
        extra = {"ContentType": content_type} if content_type else {}
        client.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=data, **extra)
    except Exception as exc:  # noqa: BLE001 — storage outage must not break the API
        import structlog
        structlog.get_logger().warning("S3 upload failed; storing reference only",
                                       key=key, error=str(exc))
        return f"local://{settings.S3_BUCKET}/{key}"
    return f"{base}/{settings.S3_BUCKET}/{key}" if base else f"s3://{settings.S3_BUCKET}/{key}"


def delete_file(key: str) -> None:
    """Delete an object from S3. Graceful no-op when storage is unconfigured or fails."""
    settings = get_settings()
    client = _client()
    if client is None:
        return
    try:
        client.delete_object(Bucket=settings.S3_BUCKET, Key=key)
    except Exception as exc:
        import structlog
        structlog.get_logger().warning("S3 delete failed", key=key, error=str(exc))


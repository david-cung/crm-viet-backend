from __future__ import annotations

import mimetypes
from dataclasses import dataclass

import boto3

from app.config import settings


@dataclass(frozen=True)
class PresignedUrl:
    url: str
    expires_in: int


def _client():
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )


def upload_file(*, file_bytes: bytes, s3_key: str, content_type: str | None = None) -> str:
    if not settings.s3_bucket_name:
        raise ValueError("S3_BUCKET_NAME is not set")
    ct = content_type or mimetypes.guess_type(s3_key)[0] or "application/octet-stream"
    _client().put_object(
        Bucket=settings.s3_bucket_name,
        Key=s3_key,
        Body=file_bytes,
        ContentType=ct,
    )
    return s3_key


def generate_presigned_url(*, s3_key: str, expires: int | None = None) -> PresignedUrl:
    if not settings.s3_bucket_name:
        raise ValueError("S3_BUCKET_NAME is not set")
    ttl = int(expires or settings.s3_presign_ttl or 900)
    url = _client().generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": s3_key},
        ExpiresIn=ttl,
    )
    return PresignedUrl(url=url, expires_in=ttl)


def delete_file(*, s3_key: str) -> None:
    if not settings.s3_bucket_name:
        raise ValueError("S3_BUCKET_NAME is not set")
    _client().delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)


"""Cloudflare R2 S3-compatible client helpers for CyberVerse.

Required environment variables:
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME
Optional:
  R2_ENDPOINT_URL, SIGNED_URL_EXPIRE_SECONDS

Credentials must only be configured on the backend host; never expose them to the browser.
"""
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_r2_client():
    settings = get_settings()
    if not all((settings.R2_ACCOUNT_ID, settings.R2_ACCESS_KEY_ID, settings.R2_SECRET_ACCESS_KEY)):
        return None
    endpoint = settings.R2_ENDPOINT_URL or f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY.get_secret_value(),
        region_name="auto",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}, retries={"max_attempts": 3, "mode": "standard"}),
    )


def get_r2_bucket() -> str | None:
    return get_settings().R2_BUCKET_NAME or None


def is_missing_object_error(exc: Exception) -> bool:
    if isinstance(exc, ClientError):
        code = str(exc.response.get("Error", {}).get("Code", ""))
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        return code in {"404", "NoSuchKey", "NotFound"} or status == 404
    return False


__all__ = ["get_r2_client", "get_r2_bucket", "is_missing_object_error", "BotoCoreError", "ClientError"]

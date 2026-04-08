from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from ...config.settings import EnterpriseSettings


class ObjectStoreClient:
    def __init__(self, settings: EnterpriseSettings):
        self.settings = settings
        self.bucket = settings.s3_bucket
        self.client: BaseClient = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            use_ssl=settings.s3_secure,
        )
        if settings.s3_auto_create_bucket:
            self.ensure_bucket()

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)

    def uri_for(self, key: str) -> str:
        return f"s3://{self.bucket}/{key}"

    def upload_file(self, source_path: str | Path, key: str, *, content_type: str | None = None) -> str:
        extra_args = {"ContentType": content_type} if content_type else None
        self.client.upload_file(str(Path(source_path).resolve()), self.bucket, key, ExtraArgs=extra_args or {})
        return self.uri_for(key)

    def upload_bytes(self, payload: bytes, key: str, *, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=payload, ContentType=content_type)
        return self.uri_for(key)

    def upload_json(self, payload: dict[str, Any], key: str) -> str:
        return self.upload_bytes(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8"),
            key,
            content_type="application/json",
        )

    def download_file(self, key: str, destination_path: str | Path) -> Path:
        destination = Path(destination_path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, str(destination))
        return destination

    def healthcheck(self) -> dict[str, Any]:
        self.client.list_objects_v2(Bucket=self.bucket, MaxKeys=1)
        return {"ok": True, "bucket": self.bucket, "endpoint": self.settings.s3_endpoint_url}

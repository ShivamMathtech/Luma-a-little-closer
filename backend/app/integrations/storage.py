from functools import lru_cache
from pathlib import Path
from datetime import datetime, timezone
from fastapi import HTTPException
from app.core.config import settings


class LocalStorage:
    def put(self, key, data, content_type):
        settings.media_root.mkdir(parents=True, exist_ok=True)
        (settings.media_root / key).write_bytes(data)

    def path(self, key):
        path = settings.media_root / Path(key).name
        if not path.is_file():
            raise HTTPException(404, "Media not found")
        return path

    def delete(self, key):
        (settings.media_root / Path(key).name).unlink(missing_ok=True)

    def keys(self):
        return [
            (p.name, datetime.fromtimestamp(p.stat().st_mtime, timezone.utc))
            for p in settings.media_root.glob("*")
            if p.is_file()
        ]


class S3Storage:
    def __init__(self):
        import boto3
        from botocore.config import Config

        self.client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            config=Config(connect_timeout=5, read_timeout=15, retries={"max_attempts": 2}, signature_version="s3v4"),
        )

    def put(self, key, data, content_type):
        self.client.put_object(Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type)

    def url(self, key):
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=60
        )

    def delete(self, key):
        self.client.delete_object(Bucket=settings.s3_bucket, Key=key)

    def keys(self):
        pages = self.client.get_paginator("list_objects_v2").paginate(Bucket=settings.s3_bucket)
        return [(o["Key"], o["LastModified"]) for p in pages for o in p.get("Contents", [])]


@lru_cache
def storage():
    return S3Storage() if settings.storage_backend == "s3" else LocalStorage()

import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
load_dotenv()

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from io import BytesIO


def get_s3_client(
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    region_name: Optional[str] = None,
    use_resource: bool = False,
):
    """Return a boto3 S3 client or resource.

    Reads credentials and endpoint from environment if not provided:
      - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
      - S3_ENDPOINT_URL (for localstack/minio)
    """
    aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
    region_name = region_name or os.getenv("AWS_REGION")

    session = boto3.session.Session()
    config = Config(signature_version="s3v4")

    if use_resource:
        return session.resource(
            "s3",
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            config=config,
        )

    return session.client(
        "s3",
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        config=config,
    )


def upload_file(
    file_path: str,
    bucket: str,
    key: str,
    extra_args: Optional[Dict[str, Any]] = None,
    client: Optional[Any] = None,
    **client_kwargs,
) -> None:
    client = client or get_s3_client(**client_kwargs)
    try:
        client.upload_file(file_path, bucket, key, ExtraArgs=extra_args or {})
    except ClientError:
        raise


def download_file(
    bucket: str,
    key: str,
    dest_path: str,
    client: Optional[Any] = None,
    **client_kwargs,
) -> None:
    client = client or get_s3_client(**client_kwargs)
    try:
        client.download_file(bucket, key, dest_path)
    except ClientError:
        raise


def list_objects(bucket: str, prefix: str = "", client: Optional[Any] = None, **client_kwargs) -> List[str]:
    client = client or get_s3_client(**client_kwargs)
    paginator = client.get_paginator("list_objects_v2")
    keys: List[str] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def upload_fileobj(
    file_obj,
    bucket: str,
    key: str,
    content_type: Optional[str] = None,
    extra_args: Optional[Dict[str, Any]] = None,
    client: Optional[Any] = None,
    **client_kwargs,
) -> None:
    """Upload a file-like object to S3 (streams directly, no intermediate disk write).

    Use this when your frontend POSTs a file to your backend and you want to stream
    it to S3 without saving locally.
    """
    client = client or get_s3_client(**client_kwargs)
    ExtraArgs = dict(extra_args or {})
    if content_type:
        ExtraArgs.setdefault("ContentType", content_type)
    try:
        client.upload_fileobj(file_obj, bucket, key, ExtraArgs=ExtraArgs)
    except ClientError:
        raise


def upload_image_from_bytes(
    data: bytes,
    bucket: str,
    key: str,
    content_type: str = "image/jpeg",
    client: Optional[Any] = None,
    **client_kwargs,
) -> None:
    """Convenience wrapper to upload image bytes to S3."""

    buf = BytesIO(data)
    buf.seek(0)
    upload_fileobj(buf, bucket, key, content_type=content_type, client=client, **client_kwargs)


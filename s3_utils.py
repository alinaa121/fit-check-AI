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
    bucket: Optional[str],
    key: str,
    extra_args: Optional[Dict[str, Any]] = None,
    client: Optional[Any] = None,
    **client_kwargs,
) -> None:
    client = client or get_s3_client(**client_kwargs)
    bucket = bucket or os.getenv("BUCKET_NAME")
    if not bucket:
        raise ValueError("Bucket name not specified and BUCKET_NAME env var is not set")
    try:
        client.upload_file(file_path, bucket, key, ExtraArgs=extra_args or {})
    except ClientError:
        raise


def download_file(
    bucket: Optional[str],
    key: str,
    dest_path: str,
    client: Optional[Any] = None,
    **client_kwargs,
) -> None:
    client = client or get_s3_client(**client_kwargs)
    bucket = bucket or os.getenv("BUCKET_NAME")
    if not bucket:
        raise ValueError("Bucket name not specified and BUCKET_NAME env var is not set")
    try:
        client.download_file(bucket, key, dest_path)
    except ClientError:
        raise


def list_objects(bucket: Optional[str], prefix: str = "", client: Optional[Any] = None, **client_kwargs) -> List[str]:
    client = client or get_s3_client(**client_kwargs)
    bucket = bucket or os.getenv("BUCKET_NAME")
    if not bucket:
        raise ValueError("Bucket name not specified and BUCKET_NAME env var is not set")
    paginator = client.get_paginator("list_objects_v2")
    keys: List[str] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def upload_fileobj(
    file_obj,
    bucket: Optional[str],
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
    bucket = bucket or os.getenv("BUCKET_NAME")
    if not bucket:
        raise ValueError("Bucket name not specified and BUCKET_NAME env var is not set")
    ExtraArgs = dict(extra_args or {})
    if content_type:
        ExtraArgs.setdefault("ContentType", content_type)
    try:
        client.upload_fileobj(file_obj, bucket, key, ExtraArgs=ExtraArgs)
    except ClientError:
        raise


def upload_image_from_bytes(
    data: bytes,
    bucket: Optional[str],
    key: str,
    content_type: str = "image/jpeg",
    client: Optional[Any] = None,
    **client_kwargs,
) -> None:
    """Convenience wrapper to upload image bytes to S3."""

    buf = BytesIO(data)
    buf.seek(0)
    upload_fileobj(buf, bucket, key, content_type=content_type, client=client, **client_kwargs)


def generate_presigned_url(
    bucket: Optional[str],
    key: str,
    expiration: int = 3600,
    client: Optional[Any] = None,
    region_name: Optional[str] = None,
    **client_kwargs,
) -> str:
    """Generate a presigned URL for an S3 object.
    
    Args:
        bucket: S3 bucket name (optional, reads from BUCKET_NAME env var)
        key: S3 object key
        expiration: URL expiration time in seconds (default: 3600 = 1 hour)
        client: Optional S3 client
        region_name: AWS region (optional, reads from AWS_REGION env var)
        
    Returns:
        str: Presigned URL that allows temporary access to the object
    """
    # Ensure we use the correct region
    if not region_name:
        region_name = client_kwargs.get('region_name') or os.getenv("AWS_REGION")
    
    client = client or get_s3_client(region_name=region_name, **client_kwargs)
    bucket = bucket or os.getenv("BUCKET_NAME")
    if not bucket:
        raise ValueError("Bucket name not specified and BUCKET_NAME env var is not set")
    try:
        url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        raise


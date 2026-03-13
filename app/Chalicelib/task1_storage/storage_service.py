"""
Storage Service - Abstracts S3 storage for the Pictorial Translator.
The fact that storage is provided by AWS S3 is shielded from endpoints and the application.
"""

import boto3


class StorageService:
    """
    Provides storage capability via AWS S3.
    Clients use this abstraction rather than talking to S3 directly.
    """

    def __init__(self, storage_location: str, region: str = "us-east-1"):
        """
        Create a boto3 client for the S3 service.

        Args:
            storage_location: The S3 bucket name in our implementation.
            region: AWS region for the S3 client.
        """
        self._client = boto3.client("s3", region_name=region)
        self._storage_location = storage_location

    def get_storage_location(self) -> str:
        """Return the S3 bucket name (storage_location)."""
        return self._storage_location

    def upload_file(self, file_bytes: bytes, filename: str) -> dict:
        """
        Upload raw file bytes to S3.

        Uses put_object(). For public URLs in a web UI, enable bucket ACLs
        and pass ACL='public-read' (many new buckets disable ACLs by default).

        Args:
            file_bytes: Raw bytes of the file to upload.
            filename: Key/filename under which to store the object.

        Returns:
            Dict with 'filename' and 'url' (public URL to the uploaded file).
        """
        self._client.put_object(
            Bucket=self._storage_location,
            Key=filename,
            Body=file_bytes,
        )
        # URL to the object (public only if bucket/object permissions allow; Rekognition works with private objects)
        url = f"https://{self._storage_location}.s3.amazonaws.com/{filename}"
        return {
            "filename": filename,
            "url": url,
        }

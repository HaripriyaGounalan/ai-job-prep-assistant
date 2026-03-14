"""
S3 storage service.

Handles all interactions with Amazon S3: bucket creation, file uploads,
downloads, and presigned URL generation. Organizes files under a clear
prefix structure for resumes and job descriptions.
"""

import logging
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from config.settings import config
from ocr_pipeline.models import FileMetadata, FileType, ProcessingStatus
from ocr_pipeline.utils.file_validator import (
    validate_file,
    get_content_type,
    FileValidationError,
)

logger = logging.getLogger(__name__)


class S3Service:
    """Manages file storage in Amazon S3."""

    def __init__(self, s3_client=None):
        """
        Initialize S3 service.

        Args:
            s3_client: Optional boto3 S3 client for dependency injection
                       (useful in tests). Creates a default client if None.
        """
        self.client = s3_client or boto3.client(
            "s3",
            region_name=config.aws.region,
        )
        self.bucket = config.s3.bucket_name

    # ------------------------------------------------------------------ #
    #  Bucket management
    # ------------------------------------------------------------------ #

    def ensure_bucket_exists(self) -> None:
        """Create the S3 bucket if it does not already exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            logger.info("S3 bucket already exists: %s", self.bucket)
        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                self._create_bucket()
            else:
                raise

    def _create_bucket(self) -> None:
        """Create the S3 bucket with proper configuration."""
        create_kwargs = {"Bucket": self.bucket}

        # us-east-1 does not accept a LocationConstraint
        if config.aws.region != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {
                "LocationConstraint": config.aws.region,
            }

        self.client.create_bucket(**create_kwargs)

        # Block public access
        self.client.put_public_access_block(
            Bucket=self.bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        # Enable versioning for accidental-overwrite protection
        self.client.put_bucket_versioning(
            Bucket=self.bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )

        logger.info("Created S3 bucket: %s", self.bucket)

    # ------------------------------------------------------------------ #
    #  Upload / download
    # ------------------------------------------------------------------ #

    def upload_file(
        self,
        file_path: str,
        file_type: FileType,
        original_filename: str | None = None,
    ) -> FileMetadata:
        """
        Validate and upload a file to S3.

        The file is stored under the appropriate prefix based on its type
        (resume or job description). A unique file ID is generated and
        embedded in the S3 key.

        Args:
            file_path:         Local path to the file.
            file_type:         Whether this is a resume or job description.
            original_filename: Display name. Defaults to the basename of file_path.

        Returns:
            FileMetadata with all fields populated.

        Raises:
            FileValidationError: If the file fails validation.
        """
        # Validate
        file_format = validate_file(file_path)

        path = Path(file_path)
        if original_filename is None:
            original_filename = path.name

        # Build metadata
        metadata = FileMetadata(
            original_filename=original_filename,
            file_type=file_type,
            file_format=file_format,
            file_size_bytes=path.stat().st_size,
            s3_bucket=self.bucket,
            status=ProcessingStatus.UPLOADING,
        )

        # Determine S3 key
        prefix = (
            config.s3.resume_prefix
            if file_type == FileType.RESUME
            else config.s3.job_desc_prefix
        )
        metadata.s3_key = f"{prefix}{metadata.file_id}/{original_filename}"

        # Upload
        content_type = get_content_type(file_format)
        try:
            self.client.upload_file(
                Filename=file_path,
                Bucket=self.bucket,
                Key=metadata.s3_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": {
                        "file-id": metadata.file_id,
                        "file-type": file_type.value,
                        "original-filename": original_filename,
                    },
                },
            )
            metadata.status = ProcessingStatus.UPLOADED
            logger.info(
                "Uploaded %s to s3://%s/%s",
                original_filename,
                self.bucket,
                metadata.s3_key,
            )
        except ClientError as e:
            metadata.status = ProcessingStatus.FAILED
            logger.error("S3 upload failed: %s", e)
            raise

        return metadata

    def download_file_bytes(self, s3_key: str) -> bytes:
        """
        Download a file from S3 and return its bytes.

        Args:
            s3_key: The S3 object key.

        Returns:
            File contents as bytes.
        """
        response = self.client.get_object(Bucket=self.bucket, Key=s3_key)
        return response["Body"].read()

    def store_processed_result(self, file_id: str, result_json: str) -> str:
        """
        Store a JSON processing result in the processed/ prefix.

        Args:
            file_id:     Unique file identifier.
            result_json: Serialized JSON string of the pipeline output.

        Returns:
            The S3 key where the result was stored.
        """
        key = f"{config.s3.processed_prefix}{file_id}/result.json"
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=result_json.encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Stored processed result at s3://%s/%s", self.bucket, key)
        return key

    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for temporary access to an S3 object.

        Args:
            s3_key:     The S3 object key.
            expiration: URL lifetime in seconds (default 1 hour).

        Returns:
            Presigned URL string.
        """
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": s3_key},
            ExpiresIn=expiration,
        )
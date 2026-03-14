"""Tests for S3 storage service using moto mocks."""

import json
import pytest
import boto3
from moto import mock_aws

from config.settings import config
from ocr_pipeline.services.s3_service import S3Service
from ocr_pipeline.models import FileType


@pytest.fixture
def s3_setup():
    """Create a mocked S3 environment."""
    with mock_aws():
        client = boto3.client("s3", region_name=config.aws.region)
        service = S3Service(s3_client=client)
        service.ensure_bucket_exists()
        yield service, client


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a small fake PDF file."""
    f = tmp_path / "test_resume.pdf"
    f.write_bytes(b"%PDF-1.4 fake resume content for testing")
    return str(f)


@pytest.fixture
def sample_png(tmp_path):
    """Create a small fake PNG file."""
    f = tmp_path / "job_desc.png"
    f.write_bytes(b"\x89PNG fake job description screenshot")
    return str(f)


class TestS3BucketManagement:
    def test_bucket_created(self, s3_setup):
        service, client = s3_setup
        response = client.head_bucket(Bucket=config.s3.bucket_name)
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_bucket_idempotent(self, s3_setup):
        service, _ = s3_setup
        # Should not raise even though bucket already exists
        service.ensure_bucket_exists()


class TestS3Upload:
    def test_upload_resume(self, s3_setup, sample_pdf):
        service, client = s3_setup
        metadata = service.upload_file(sample_pdf, FileType.RESUME)

        assert metadata.file_type == FileType.RESUME
        assert metadata.s3_key.startswith(config.s3.resume_prefix)
        assert metadata.original_filename == "test_resume.pdf"
        assert metadata.file_size_bytes > 0

        # Verify object actually exists in S3
        obj = client.get_object(
            Bucket=config.s3.bucket_name, Key=metadata.s3_key
        )
        assert obj["ContentType"] == "application/pdf"

    def test_upload_job_description(self, s3_setup, sample_png):
        service, _ = s3_setup
        metadata = service.upload_file(sample_png, FileType.JOB_DESCRIPTION)

        assert metadata.file_type == FileType.JOB_DESCRIPTION
        assert metadata.s3_key.startswith(config.s3.job_desc_prefix)

    def test_upload_custom_filename(self, s3_setup, sample_pdf):
        service, _ = s3_setup
        metadata = service.upload_file(
            sample_pdf, FileType.RESUME, original_filename="my_resume_v2.pdf"
        )
        assert metadata.original_filename == "my_resume_v2.pdf"
        assert "my_resume_v2.pdf" in metadata.s3_key


class TestS3Download:
    def test_download_uploaded_file(self, s3_setup, sample_pdf):
        service, _ = s3_setup
        metadata = service.upload_file(sample_pdf, FileType.RESUME)
        downloaded = service.download_file_bytes(metadata.s3_key)
        assert b"%PDF-1.4" in downloaded


class TestS3ProcessedResults:
    def test_store_and_retrieve_result(self, s3_setup):
        service, client = s3_setup
        result = {"resume_text": "Hello world", "score": 85}
        result_json = json.dumps(result)

        key = service.store_processed_result("test-file-id", result_json)

        assert "processed/" in key
        obj = client.get_object(Bucket=config.s3.bucket_name, Key=key)
        stored = json.loads(obj["Body"].read())
        assert stored["resume_text"] == "Hello world"


class TestS3PresignedURL:
    def test_generate_url(self, s3_setup, sample_pdf):
        service, _ = s3_setup
        metadata = service.upload_file(sample_pdf, FileType.RESUME)
        url = service.generate_presigned_url(metadata.s3_key)
        assert "test_resume.pdf" in url
        assert config.s3.bucket_name in url
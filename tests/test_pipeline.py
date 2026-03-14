"""Integration tests for the full OCR pipeline."""

import json
import pytest
from unittest.mock import MagicMock, patch

import boto3
from moto import mock_aws

from config.settings import config
from ocr_pipeline.pipeline import OCRPipeline
from ocr_pipeline.services.s3_service import S3Service
from ocr_pipeline.services.textract_service import TextractService
from ocr_pipeline.models import FileType, ProcessingStatus


def _make_textract_response(lines: list[str]) -> dict:
    blocks = [{"BlockType": "PAGE", "Page": 1}]
    for line in lines:
        blocks.append({
            "BlockType": "LINE",
            "Text": line,
            "Confidence": 98.0,
            "Page": 1,
        })
    return {"Blocks": blocks}


RESUME_LINES = [
    "Jane Doe",
    "jane.doe@email.com | 555-0199",
    "",
    "EXPERIENCE",
    "Senior Software Engineer at TechCorp",
    "Led migration of monolith to microservices using Python and AWS",
    "Reduced deployment time by 60% with CI/CD pipelines",
    "",
    "EDUCATION",
    "BS Computer Science, Stanford University",
    "",
    "SKILLS",
    "Python, Java, AWS, Docker, Kubernetes, PostgreSQL, React",
]

JD_LINES = [
    "Software Engineer - Cloud Infrastructure",
    "Acme Corp - San Francisco, CA",
    "",
    "REQUIREMENTS",
    "5+ years experience in software engineering",
    "Strong Python and Go programming skills",
    "Experience with AWS services (EC2, S3, Lambda)",
    "Kubernetes and container orchestration",
    "CI/CD pipeline design and implementation",
    "",
    "PREFERRED QUALIFICATIONS",
    "Experience with Terraform or CloudFormation",
    "Background in distributed systems",
]


@pytest.fixture
def pipeline_setup():
    """Set up pipeline with mocked S3 and Textract."""
    with mock_aws():
        s3_client = boto3.client("s3", region_name=config.aws.region)
        s3_service = S3Service(s3_client=s3_client)

        textract_client = MagicMock()
        textract_service = TextractService(textract_client=textract_client)

        pipeline = OCRPipeline(
            s3_service=s3_service,
            textract_service=textract_service,
        )
        pipeline.initialize()

        yield pipeline, textract_client


@pytest.fixture
def sample_files(tmp_path):
    resume = tmp_path / "jane_resume.pdf"
    resume.write_bytes(b"%PDF-1.4 resume content")

    jd = tmp_path / "cloud_engineer_jd.png"
    jd.write_bytes(b"\x89PNG job description content")

    return str(resume), str(jd)


class TestSingleFileProcessing:
    def test_process_resume(self, pipeline_setup, sample_files):
        pipeline, textract_client = pipeline_setup
        resume_path, _ = sample_files

        textract_client.detect_document_text.return_value = (
            _make_textract_response(RESUME_LINES)
        )

        result = pipeline.process_file(resume_path, FileType.RESUME)

        assert result.status == ProcessingStatus.COMPLETED.value
        assert result.file_type == "resume"
        assert "Jane Doe" in result.cleaned_text
        assert "Python" in result.cleaned_text
        assert result.word_count > 0
        assert result.confidence > 0
        assert result.error is None

    def test_process_invalid_file(self, pipeline_setup, tmp_path):
        pipeline, _ = pipeline_setup
        bad_file = tmp_path / "bad.docx"
        bad_file.write_bytes(b"not allowed")

        result = pipeline.process_file(str(bad_file), FileType.RESUME)
        assert result.status == ProcessingStatus.FAILED.value
        assert "Validation failed" in result.error


class TestPairProcessing:
    def test_process_pair(self, pipeline_setup, sample_files):
        pipeline, textract_client = pipeline_setup
        resume_path, jd_path = sample_files

        # Different responses for resume vs JD
        textract_client.detect_document_text.side_effect = [
            _make_textract_response(RESUME_LINES),
            _make_textract_response(JD_LINES),
        ]

        result = pipeline.process_pair(resume_path, jd_path)

        # Check resume text
        assert "Jane Doe" in result.resume_text
        assert "Python" in result.resume_text

        # Check JD text
        assert "Cloud Infrastructure" in result.job_description_text
        assert "Kubernetes" in result.job_description_text

        # Check structure
        assert result.resume_output is not None
        assert result.job_description_output is not None
        assert result.session_id is not None

    def test_pair_output_serializable(self, pipeline_setup, sample_files):
        pipeline, textract_client = pipeline_setup
        resume_path, jd_path = sample_files

        textract_client.detect_document_text.side_effect = [
            _make_textract_response(RESUME_LINES),
            _make_textract_response(JD_LINES),
        ]

        result = pipeline.process_pair(resume_path, jd_path)
        output_dict = result.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(output_dict, indent=2)
        parsed = json.loads(json_str)

        assert "resume_text" in parsed
        assert "job_description_text" in parsed
        assert "session_id" in parsed
        assert parsed["resume_output"]["status"] == "completed"
        assert parsed["job_description_output"]["status"] == "completed"
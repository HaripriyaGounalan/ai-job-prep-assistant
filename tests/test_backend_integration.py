import json
import pytest
import os
import boto3
from fastapi.testclient import TestClient
from unittest.mock import patch
from moto import mock_aws

from backend.main import app
from config.settings import config
from extraction_pipeline.models import ExtractionState

from ocr_pipeline.models import OCRResult

client = TestClient(app)

@pytest.fixture
def mock_aws_env():
    """Set up the mock AWS environment (S3) for integration testing."""
    with mock_aws():
        # Create the mock S3 bucket that the backend expects
        s3 = boto3.client("s3", region_name=config.aws.region)
        s3.create_bucket(Bucket=config.s3.bucket_name)
        yield

@patch("ocr_pipeline.services.textract_service.TextractService.extract_text_from_s3")
@patch("backend.services.run_extraction")
@patch("backend.services.run_comparison")
def test_full_api_integration(mock_run_comparison, mock_run_ext, mock_textract, mock_aws_env):
    """
    Integration test of the FastAPI backend.
    
    This exercises the real API endpoints, background task execution,
    and S3 JSON serialization/end-to-end job flow.
    The OCR boundary and the backend extraction/comparison orchestration
    steps are mocked so the test remains deterministic and avoids real
    external processing costs while still verifying the overall system flow.
    """
    
    # 1. Mock the specific LLM/AI operation boundaries
    mock_textract.return_value = OCRResult(raw_text="Extracted OCR text", confidence=99.0, page_count=1)
    
    # Mocking extraction state returned by LangGraph
    dummy_extraction_state = ExtractionState(
        status="completed",
        resume_text="Mocked candidate resume",
        job_description_text="Mocked JD text",
        job_requirements=None,
        candidate_profile=None,
        errors=[]
    )
    mock_run_ext.return_value = dummy_extraction_state
    
    # Mocking ComparisonResult returned by the final layer
    class DummyComparisonResult:
        def model_dump(self):
            return {"overall_score": 95.0, "strengths_summary": "Great mock fit!"}
    mock_run_comparison.return_value = DummyComparisonResult()

    # 2. Prepare mock files for upload
    resume_content = b"PDF dummy content"
    jd_content = b"PNG dummy content"
    
    files = {
        "resume": ("resume.pdf", resume_content, "application/pdf"),
        "job_description": ("jd.png", jd_content, "image/png"),
    }
    
    # 3. Hit the Upload Endpoint
    # Note: FastAPI's TestClient runs background tasks synchronously immediately 
    # before returning the HTTP response. So by the time this returns, process_job is done!
    response = client.post("/upload", files=files)
    
    assert response.status_code == 200
    upload_data = response.json()
    assert "job_id" in upload_data
    job_id = upload_data["job_id"]
    
    # 4. Check the Status Endpoint
    # Since process_job already ran, the status stored in the mock S3 bucket should be 'completed'
    status_response = client.get(f"/status/{job_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"
    
    # 5. Check the Result Endpoint
    result_response = client.get(f"/result/{job_id}")
    assert result_response.status_code == 200
    result_data = result_response.json()
    
    assert result_data["status"] == "completed"
    assert result_data["result"]["overall_score"] == 95.0
    assert result_data["result"]["strengths_summary"] == "Great mock fit!"

import json
import pytest
import os
from unittest.mock import patch, MagicMock
from backend.services import process_job

@patch("backend.services.get_s3_service")
@patch("backend.services.OCRPipeline")
@patch("backend.services.run_extraction")
@patch("backend.services.run_comparison")
def test_process_job_success(mock_run_comp, mock_run_ext, mock_ocr, mock_shared_s3, tmp_path):
    
    mock_ocr_instance = mock_ocr.return_value
    mock_ocr_result = MagicMock(
        session_id="test-session",
        resume_text="Dummy resume text",
        job_description_text="Dummy JD text",
        resume_output=MagicMock(status="completed", error=None),
        job_description_output=MagicMock(status="completed", error=None)
    )
    mock_ocr_instance.process_pair.return_value = mock_ocr_result
    
    mock_ext_result = MagicMock(
        status="completed",
        errors=[]
    )
    mock_run_ext.return_value = mock_ext_result
    
    mock_comp_result = MagicMock()
    mock_comp_result.model_dump.return_value = {"overall_score": 90}
    mock_run_comp.return_value = mock_comp_result
    
    # create dummy files
    test_r = tmp_path / "test_r.pdf"
    test_j = tmp_path / "test_j.pdf"
    test_r.touch()
    test_j.touch()
    
    process_job("job-123", str(test_r), str(test_j))
    
    # files should be deleted
    assert not test_r.exists()
    assert not test_j.exists()
    
    # Verify success saved to S3
    mock_shared_s3.return_value.store_processed_result.assert_called_once()
    args, kwargs = mock_shared_s3.return_value.store_processed_result.call_args
    assert args[0] == "job-123"
    saved_data = json.loads(args[1])
    assert saved_data["status"] == "completed"
    assert saved_data["comparison"]["overall_score"] == 90

@patch("backend.services.get_s3_service")
@patch("backend.services.OCRPipeline")
def test_process_job_failure(mock_ocr, mock_shared_s3, tmp_path):
    
    mock_ocr_instance = mock_ocr.return_value
    # Simulate an OCR crash
    mock_ocr_instance.process_pair.side_effect = Exception("AWS Textract Timeout")
    
    test_r = tmp_path / "test_r.pdf"
    test_j = tmp_path / "test_j.pdf"
    test_r.touch()
    test_j.touch()
    
    process_job("job-456", str(test_r), str(test_j))
    
    # Verify failure saved to S3
    mock_shared_s3.return_value.store_processed_result.assert_called_once()
    args, kwargs = mock_shared_s3.return_value.store_processed_result.call_args
    assert args[0] == "job-456"
    saved_data = json.loads(args[1])
    assert saved_data["status"] == "failed"
    assert "AWS Textract Timeout" in saved_data["error"]



import json
import pytest
import os
from unittest.mock import patch, MagicMock
from backend.services import process_job

@patch("backend.services.S3Service")
@patch("backend.services.OCRPipeline")
@patch("backend.services.run_extraction")
@patch("backend.services.run_comparison")
def test_process_job_success(mock_run_comp, mock_run_ext, mock_ocr, mock_s3_class):
    mock_s3 = mock_s3_class.return_value
    
    mock_ocr_instance = mock_ocr.return_value
    mock_ocr_result = MagicMock()
    mock_ocr_result.status = "COMPLETED"
    mock_ocr_result.session_id = "test-session"
    mock_ocr_instance.process_pair.return_value = mock_ocr_result
    
    mock_ext_result = MagicMock()
    mock_ext_result.status = "completed"
    mock_run_ext.return_value = mock_ext_result
    
    mock_comp_result = MagicMock()
    mock_comp_result.model_dump.return_value = {"overall_score": 90}
    mock_run_comp.return_value = mock_comp_result
    
    # create dummy files
    open("test_r.pdf", "w").close()
    open("test_j.pdf", "w").close()
    
    try:
        process_job("job-123", "test_r.pdf", "test_j.pdf")
        
        # files should be deleted
        assert not os.path.exists("test_r.pdf")
        assert not os.path.exists("test_j.pdf")
        
        # Verify success saved to S3
        mock_s3.store_processed_result.assert_called_once()
        args, kwargs = mock_s3.store_processed_result.call_args
        assert args[0] == "job-123"
        saved_data = json.loads(args[1])
        assert saved_data["status"] == "completed"
        assert saved_data["comparison"]["overall_score"] == 90
    finally:
        if os.path.exists("test_r.pdf"): os.remove("test_r.pdf")
        if os.path.exists("test_j.pdf"): os.remove("test_j.pdf")

@patch("backend.services.S3Service")
@patch("backend.services.OCRPipeline")
def test_process_job_failure(mock_ocr, mock_s3_class):
    mock_s3 = mock_s3_class.return_value
    
    mock_ocr_instance = mock_ocr.return_value
    # Simulate an OCR crash
    mock_ocr_instance.process_pair.side_effect = Exception("AWS Textract Timeout")
    
    open("test_r.pdf", "w").close()
    open("test_j.pdf", "w").close()
    
    try:
        process_job("job-456", "test_r.pdf", "test_j.pdf")
        
        # Verify failure saved to S3
        mock_s3.store_processed_result.assert_called_once()
        args, kwargs = mock_s3.store_processed_result.call_args
        assert args[0] == "job-456"
        saved_data = json.loads(args[1])
        assert saved_data["status"] == "failed"
        assert "AWS Textract Timeout" in saved_data["error"]
        
    finally:
        if os.path.exists("test_r.pdf"): os.remove("test_r.pdf")
        if os.path.exists("test_j.pdf"): os.remove("test_j.pdf")

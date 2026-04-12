import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.main import app
import botocore.exceptions

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@patch("backend.main.process_job")
def test_upload_files(mock_process_job):
    # Create fake files
    resume_content = b"fake resume content"
    jd_content = b"fake jd content"
    
    files = {
        "resume": ("resume.pdf", resume_content, "application/pdf"),
        "job_description": ("jd.pdf", jd_content, "application/pdf"),
    }
    
    response = client.post("/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["message"] == "Files uploaded successfully and processing started."
    
    # Check background task was called
    mock_process_job.assert_called_once()
    args, kwargs = mock_process_job.call_args
    assert args[0] == data["job_id"]
    # args[1] and [2] are temp file paths
    assert "resume.pdf" in args[1]
    assert "jd.pdf" in args[2]

@patch("backend.main.S3Service")
def test_get_status_completed(MockS3Service):
    mock_s3 = MockS3Service.return_value
    mock_s3.download_file_bytes.return_value = json.dumps({
        "job_id": "123",
        "status": "completed"
    }).encode("utf-8")
    
    response = client.get("/status/123")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["job_id"] == "123"

@patch("backend.main.S3Service")
def test_get_status_processing(MockS3Service):
    mock_s3 = MockS3Service.return_value
    # Simulate file not found in S3
    error_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
    mock_s3.download_file_bytes.side_effect = botocore.exceptions.ClientError(error_response, 'GetObject')
    
    response = client.get("/status/123")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"

@patch("backend.main.S3Service")
def test_get_result_completed(MockS3Service):
    mock_s3 = MockS3Service.return_value
    mock_s3.download_file_bytes.return_value = json.dumps({
        "job_id": "123",
        "status": "completed",
        "comparison": {"score": 85}
    }).encode("utf-8")
    
    response = client.get("/result/123")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["result"] == {"score": 85}

@patch("backend.main.S3Service")
def test_get_result_processing(MockS3Service):
    mock_s3 = MockS3Service.return_value
    # Simulate file not found in S3
    error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}}
    mock_s3.download_file_bytes.side_effect = botocore.exceptions.ClientError(error_response, 'GetObject')
    
    response = client.get("/result/123")
    
    assert response.status_code == 404
    assert "processing" in response.json()["detail"]

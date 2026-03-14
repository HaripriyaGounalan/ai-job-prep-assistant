"""Tests for Textract OCR service."""

import pytest
from unittest.mock import MagicMock, patch

from ocr_pipeline.services.textract_service import TextractService, TextractError
from ocr_pipeline.models import FileFormat, OCRResult


def _make_textract_response(lines: list[str], page: int = 1) -> dict:
    """Build a mock Textract API response."""
    blocks = [
        {"BlockType": "PAGE", "Page": page},
    ]
    for line in lines:
        blocks.append({
            "BlockType": "LINE",
            "Text": line,
            "Confidence": 99.5,
            "Page": page,
        })
    return {"Blocks": blocks}


class TestSyncExtraction:
    def test_extract_image(self):
        mock_client = MagicMock()
        mock_client.detect_document_text.return_value = _make_textract_response(
            ["Software Engineer", "5 years experience", "Python, AWS"]
        )

        service = TextractService(textract_client=mock_client)
        result = service.extract_text_from_s3(
            "test-bucket", "resume.png", FileFormat.PNG
        )

        assert isinstance(result, OCRResult)
        assert "Software Engineer" in result.raw_text
        assert "Python, AWS" in result.raw_text
        assert result.confidence > 99.0
        assert result.page_count == 1

    def test_extract_from_bytes(self):
        mock_client = MagicMock()
        mock_client.detect_document_text.return_value = _make_textract_response(
            ["Line 1", "Line 2"]
        )

        service = TextractService(textract_client=mock_client)
        result = service.extract_text_from_bytes(b"fake file bytes")

        assert "Line 1" in result.raw_text
        assert "Line 2" in result.raw_text


class TestAsyncExtraction:
    def test_multipage_pdf(self):
        mock_client = MagicMock()

        # Sync call fails (multi-page)
        from botocore.exceptions import ClientError
        mock_client.detect_document_text.side_effect = ClientError(
            {"Error": {"Code": "UnsupportedDocumentException", "Message": ""}},
            "DetectDocumentText",
        )

        # Async flow
        mock_client.start_document_text_detection.return_value = {
            "JobId": "test-job-123"
        }

        page1 = _make_textract_response(["Page 1 line A", "Page 1 line B"], page=1)
        page1["JobStatus"] = "SUCCEEDED"
        page1["NextToken"] = "token-2"

        page2 = _make_textract_response(["Page 2 line A"], page=2)
        # No NextToken → end of pages

        mock_client.get_document_text_detection.side_effect = [page1, page2]

        service = TextractService(textract_client=mock_client)
        result = service.extract_text_from_s3(
            "test-bucket", "multipage.pdf", FileFormat.PDF
        )

        assert "Page 1 line A" in result.raw_text
        assert "Page 2 line A" in result.raw_text
        assert result.page_count == 2

    def test_job_failure_raises_error(self):
        mock_client = MagicMock()
        from botocore.exceptions import ClientError
        mock_client.detect_document_text.side_effect = ClientError(
            {"Error": {"Code": "UnsupportedDocumentException", "Message": ""}},
            "DetectDocumentText",
        )

        mock_client.start_document_text_detection.return_value = {
            "JobId": "fail-job"
        }
        mock_client.get_document_text_detection.return_value = {
            "JobStatus": "FAILED",
            "StatusMessage": "Invalid document",
        }

        service = TextractService(textract_client=mock_client)
        with pytest.raises(TextractError, match="Invalid document"):
            service.extract_text_from_s3(
                "test-bucket", "bad.pdf", FileFormat.PDF
            )


class TestResponseParsing:
    def test_empty_response(self):
        result = TextractService._parse_response([{"Blocks": []}])
        assert result.raw_text == ""
        assert result.confidence == 0.0

    def test_skips_non_line_blocks(self):
        response = {
            "Blocks": [
                {"BlockType": "PAGE", "Page": 1},
                {"BlockType": "WORD", "Text": "ignored", "Confidence": 99.0},
                {"BlockType": "LINE", "Text": "kept", "Confidence": 95.0},
            ]
        }
        result = TextractService._parse_response([response])
        assert "kept" in result.raw_text
        assert "ignored" not in result.raw_text
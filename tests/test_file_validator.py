"""Tests for file validation utilities."""

import os
import tempfile
import pytest
from ocr_pipeline.utils.file_validator import validate_file, FileValidationError
from ocr_pipeline.models import FileFormat


class TestFileValidation:
    def test_valid_pdf(self, tmp_path):
        f = tmp_path / "resume.pdf"
        f.write_bytes(b"%PDF-1.4 fake content")
        result = validate_file(str(f))
        assert result == FileFormat.PDF

    def test_valid_png(self, tmp_path):
        f = tmp_path / "screenshot.png"
        f.write_bytes(b"\x89PNG fake content")
        result = validate_file(str(f))
        assert result == FileFormat.PNG

    def test_valid_jpg(self, tmp_path):
        f = tmp_path / "photo.jpg"
        f.write_bytes(b"\xff\xd8\xff fake jpg")
        result = validate_file(str(f))
        assert result == FileFormat.JPG

    def test_file_not_found(self):
        with pytest.raises(FileValidationError, match="not found"):
            validate_file("/nonexistent/file.pdf")

    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "document.docx"
        f.write_bytes(b"some content")
        with pytest.raises(FileValidationError, match="Unsupported"):
            validate_file(str(f))

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.pdf"
        f.write_bytes(b"")
        with pytest.raises(FileValidationError, match="empty"):
            validate_file(str(f))

    def test_file_too_large(self, tmp_path, monkeypatch):
        from config import settings
        # Temporarily set max size to 1 byte
        monkeypatch.setattr(settings.config.processing, "max_file_size_mb", 0)
        f = tmp_path / "huge.pdf"
        f.write_bytes(b"x" * 100)
        with pytest.raises(FileValidationError, match="too large"):
            validate_file(str(f))

    def test_directory_rejected(self, tmp_path):
        with pytest.raises(FileValidationError, match="Not a file"):
            validate_file(str(tmp_path))
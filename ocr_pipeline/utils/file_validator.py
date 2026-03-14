"""
File validation utilities.

Validates uploads before they enter the pipeline: checks size limits,
file extensions, and basic content integrity.
"""

import os
from pathlib import Path
from config.settings import config
from ocr_pipeline.models import FileFormat


class FileValidationError(Exception):
    """Raised when a file fails validation."""
    pass


def validate_file(file_path: str) -> FileFormat:
    """
    Validate a file for processing.

    Checks:
        - File exists
        - Extension is allowed
        - File size is within limits
        - File is not empty

    Args:
        file_path: Path to the file on disk.

    Returns:
        FileFormat enum value for the validated file.

    Raises:
        FileValidationError: If any validation check fails.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileValidationError(f"File not found: {file_path}")

    if not path.is_file():
        raise FileValidationError(f"Not a file: {file_path}")

    # Check extension
    ext = path.suffix.lower()
    if ext not in config.processing.allowed_extensions:
        raise FileValidationError(
            f"Unsupported file type: {ext}. "
            f"Allowed: {', '.join(config.processing.allowed_extensions)}"
        )

    # Check size
    file_size = path.stat().st_size
    if file_size == 0:
        raise FileValidationError("File is empty")

    if file_size > config.processing.max_file_size_bytes:
        size_mb = file_size / (1024 * 1024)
        raise FileValidationError(
            f"File too large: {size_mb:.1f}MB. "
            f"Maximum: {config.processing.max_file_size_mb}MB"
        )

    # Map extension to format
    ext_to_format = {
        ".pdf": FileFormat.PDF,
        ".png": FileFormat.PNG,
        ".jpg": FileFormat.JPG,
        ".jpeg": FileFormat.JPEG,
        ".tiff": FileFormat.TIFF,
    }

    return ext_to_format[ext]


def get_content_type(file_format: FileFormat) -> str:
    """Map file format to MIME content type for S3 upload."""
    content_types = {
        FileFormat.PDF: "application/pdf",
        FileFormat.PNG: "image/png",
        FileFormat.JPG: "image/jpeg",
        FileFormat.JPEG: "image/jpeg",
        FileFormat.TIFF: "image/tiff",
    }
    return content_types[file_format]
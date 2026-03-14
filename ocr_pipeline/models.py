"""
Data models for the OCR pipeline.
Defines structured types for file metadata, OCR results, and pipeline output.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class FileType(str, Enum):
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"


class FileFormat(str, Enum):
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    TIFF = "tiff"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    CLEANING = "cleaning"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class FileMetadata:
    """Metadata for an uploaded file."""
    file_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_filename: str = ""
    file_type: FileType = FileType.RESUME
    file_format: FileFormat = FileFormat.PDF
    file_size_bytes: int = 0
    s3_key: str = ""
    s3_bucket: str = ""
    upload_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: ProcessingStatus = ProcessingStatus.PENDING

    def to_dict(self) -> dict:
        return {
            "file_id": self.file_id,
            "original_filename": self.original_filename,
            "file_type": self.file_type.value,
            "file_format": self.file_format.value,
            "file_size_bytes": self.file_size_bytes,
            "s3_key": self.s3_key,
            "s3_bucket": self.s3_bucket,
            "upload_timestamp": self.upload_timestamp,
            "status": self.status.value,
        }


@dataclass
class OCRResult:
    """Raw result from Textract OCR."""
    raw_text: str = ""
    confidence: float = 0.0
    page_count: int = 0
    blocks: list[dict] = field(default_factory=list)


@dataclass
class CleanedText:
    """Text after cleaning and normalization."""
    text: str = ""
    line_count: int = 0
    word_count: int = 0


@dataclass
class PipelineOutput:
    """Final output of the OCR pipeline for one file."""
    file_id: str = ""
    file_type: str = ""
    original_filename: str = ""
    status: str = ProcessingStatus.COMPLETED.value
    raw_text: str = ""
    cleaned_text: str = ""
    confidence: float = 0.0
    page_count: int = 0
    word_count: int = 0
    s3_key: str = ""
    processed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error: Optional[str] = None

    def to_dict(self) -> dict:
        result = {
            "file_id": self.file_id,
            "file_type": self.file_type,
            "original_filename": self.original_filename,
            "status": self.status,
            "raw_text": self.raw_text,
            "cleaned_text": self.cleaned_text,
            "confidence": round(self.confidence, 2),
            "page_count": self.page_count,
            "word_count": self.word_count,
            "s3_key": self.s3_key,
            "processed_at": self.processed_at,
        }
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class FullPipelineResult:
    """Combined output for resume + job description pair."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resume_text: str = ""
    job_description_text: str = ""
    resume_output: Optional[PipelineOutput] = None
    job_description_output: Optional[PipelineOutput] = None
    processed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "resume_text": self.resume_text,
            "job_description_text": self.job_description_text,
            "resume_output": self.resume_output.to_dict() if self.resume_output else None,
            "job_description_output": (
                self.job_description_output.to_dict()
                if self.job_description_output
                else None
            ),
            "processed_at": self.processed_at,
        }
"""
OCR Pipeline — main orchestrator.

Coordinates the full flow: validate → upload to S3 → OCR via Textract →
clean text → store result. Can process a single file or a resume + job
description pair.
"""

import json
import logging
from typing import Optional

from ocr_pipeline.models import (
    FileMetadata,
    FileType,
    PipelineOutput,
    FullPipelineResult,
    ProcessingStatus,
)
from ocr_pipeline.services.s3_service import S3Service
from ocr_pipeline.services.textract_service import TextractService, TextractError
from ocr_pipeline.utils.text_cleaner import clean_ocr_text
from ocr_pipeline.utils.file_validator import FileValidationError

logger = logging.getLogger(__name__)


class OCRPipeline:
    """
    End-to-end OCR pipeline.

    Usage::

        pipeline = OCRPipeline()
        pipeline.initialize()                       # creates bucket if needed

        result = pipeline.process_pair(
            resume_path="resume.pdf",
            job_desc_path="job_posting.png",
        )

        print(result.resume_text)
        print(result.job_description_text)
    """

    def __init__(
        self,
        s3_service: Optional[S3Service] = None,
        textract_service: Optional[TextractService] = None,
    ):
        self.s3 = s3_service or S3Service()
        self.textract = textract_service or TextractService()

    def initialize(self) -> None:
        """One-time setup: ensure S3 bucket exists."""
        self.s3.ensure_bucket_exists()
        logger.info("OCR pipeline initialized")

    # ------------------------------------------------------------------ #
    #  Single-file processing
    # ------------------------------------------------------------------ #

    def process_file(
        self,
        file_path: str,
        file_type: FileType,
        original_filename: Optional[str] = None,
    ) -> PipelineOutput:
        """
        Process a single file through the full pipeline.

        Steps:
            1. Validate and upload to S3
            2. Run Textract OCR
            3. Clean the extracted text
            4. Store the JSON result in S3

        Args:
            file_path:         Local path to the file.
            file_type:         RESUME or JOB_DESCRIPTION.
            original_filename: Optional display name override.

        Returns:
            PipelineOutput with cleaned text and metadata.
        """
        output = PipelineOutput(file_type=file_type.value)

        # --- Step 1: Upload ------------------------------------------------
        try:
            metadata = self.s3.upload_file(file_path, file_type, original_filename)
            output.file_id = metadata.file_id
            output.original_filename = metadata.original_filename
            output.s3_key = metadata.s3_key
            logger.info(
                "Step 1 complete — uploaded %s (%s)",
                metadata.original_filename,
                metadata.file_id,
            )
        except FileValidationError as e:
            output.status = ProcessingStatus.FAILED.value
            output.error = f"Validation failed: {e}"
            logger.error("Validation error: %s", e)
            return output

        # --- Step 2: OCR ---------------------------------------------------
        try:
            metadata.status = ProcessingStatus.EXTRACTING
            ocr_result = self.textract.extract_text_from_s3(
                bucket=metadata.s3_bucket,
                s3_key=metadata.s3_key,
                file_format=metadata.file_format,
            )
            output.raw_text = ocr_result.raw_text
            output.confidence = ocr_result.confidence
            output.page_count = ocr_result.page_count
            logger.info(
                "Step 2 complete — extracted %d pages, confidence %.1f%%",
                ocr_result.page_count,
                ocr_result.confidence,
            )
        except TextractError as e:
            output.status = ProcessingStatus.FAILED.value
            output.error = f"OCR failed: {e}"
            logger.error("Textract error: %s", e)
            return output

        # --- Step 3: Clean text --------------------------------------------
        metadata.status = ProcessingStatus.CLEANING
        cleaned = clean_ocr_text(ocr_result.raw_text)
        output.cleaned_text = cleaned.text
        output.word_count = cleaned.word_count
        logger.info(
            "Step 3 complete — %d words, %d lines",
            cleaned.word_count,
            cleaned.line_count,
        )

        # --- Step 4: Store result ------------------------------------------
        output.status = ProcessingStatus.COMPLETED.value
        result_json = json.dumps(output.to_dict(), indent=2)
        self.s3.store_processed_result(output.file_id, result_json)
        logger.info("Step 4 complete — result stored for %s", output.file_id)

        return output

    # ------------------------------------------------------------------ #
    #  Paired processing (resume + JD)
    # ------------------------------------------------------------------ #

    def process_pair(
        self,
        resume_path: str,
        job_desc_path: str,
        resume_filename: Optional[str] = None,
        job_desc_filename: Optional[str] = None,
    ) -> FullPipelineResult:
        """
        Process a resume and job description together.

        Returns a FullPipelineResult with both cleaned texts readily
        accessible as ``result.resume_text`` and
        ``result.job_description_text`` — the JSON payload expected by
        downstream LangGraph tasks.

        Args:
            resume_path:      Local path to the resume file.
            job_desc_path:    Local path to the job description file.
            resume_filename:  Optional display name for the resume.
            job_desc_filename: Optional display name for the job description.

        Returns:
            FullPipelineResult.
        """
        result = FullPipelineResult()

        logger.info("=== Processing resume ===")
        resume_output = self.process_file(
            resume_path, FileType.RESUME, resume_filename
        )
        result.resume_output = resume_output
        result.resume_text = resume_output.cleaned_text

        logger.info("=== Processing job description ===")
        jd_output = self.process_file(
            job_desc_path, FileType.JOB_DESCRIPTION, job_desc_filename
        )
        result.job_description_output = jd_output
        result.job_description_text = jd_output.cleaned_text

        # Store combined result
        combined_json = json.dumps(result.to_dict(), indent=2)
        self.s3.store_processed_result(result.session_id, combined_json)

        logger.info(
            "Pipeline complete — session %s | resume: %d words | JD: %d words",
            result.session_id,
            resume_output.word_count,
            jd_output.word_count,
        )

        return result
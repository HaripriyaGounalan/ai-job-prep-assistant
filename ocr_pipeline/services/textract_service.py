"""
AWS Textract OCR service.

Supports two modes:
  1. Synchronous (detect_document_text) — for single-page images and
     small PDFs. Fast, returns immediately.
  2. Asynchronous (start/get_document_text_detection) — for multi-page
     PDFs. Polls for completion with exponential backoff.

The service always returns an OCRResult with raw text, average
confidence, page count, and the raw Textract blocks for debugging.
"""

import logging
import time

import boto3
from botocore.exceptions import ClientError

from config.settings import config
from ocr_pipeline.models import OCRResult, FileFormat

logger = logging.getLogger(__name__)


class TextractError(Exception):
    """Raised when Textract processing fails."""
    pass


class TextractService:
    """Handles OCR via AWS Textract."""

    def __init__(self, textract_client=None):
        """
        Args:
            textract_client: Optional boto3 Textract client for DI/testing.
        """
        self.client = textract_client or boto3.client(
            "textract",
            region_name=config.aws.region,
        )
        self.max_retries = config.textract.max_retries
        self.retry_delay = config.textract.retry_delay

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def extract_text_from_s3(
        self,
        bucket: str,
        s3_key: str,
        file_format: FileFormat,
    ) -> OCRResult:
        """
        Run OCR on a document stored in S3.

        Automatically selects sync vs async mode:
          - Images and single-page PDFs → synchronous
          - Multi-page PDFs → asynchronous

        Args:
            bucket:      S3 bucket name.
            s3_key:      S3 object key.
            file_format: The file's format (determines processing mode).

        Returns:
            OCRResult containing extracted text and metadata.
        """
        if file_format in (FileFormat.PNG, FileFormat.JPG, FileFormat.JPEG, FileFormat.TIFF):
            return self._sync_extract(bucket, s3_key)
        else:
            # PDFs: try sync first; fall back to async if it fails
            # (sync only works for single-page PDFs)
            try:
                return self._sync_extract(bucket, s3_key)
            except (ClientError, TextractError):
                logger.info("Sync extraction failed for PDF, using async mode")
                return self._async_extract(bucket, s3_key)

    def extract_text_from_bytes(self, file_bytes: bytes) -> OCRResult:
        """
        Run synchronous OCR directly on file bytes.

        Only works for single-page documents / images.

        Args:
            file_bytes: Raw file content.

        Returns:
            OCRResult.
        """
        try:
            response = self.client.detect_document_text(
                Document={"Bytes": file_bytes}
            )
            return self._parse_response([response])
        except ClientError as e:
            raise TextractError(f"Textract byte extraction failed: {e}") from e

    # ------------------------------------------------------------------ #
    #  Sync mode
    # ------------------------------------------------------------------ #

    def _sync_extract(self, bucket: str, s3_key: str) -> OCRResult:
        """Synchronous single-page extraction."""
        try:
            response = self.client.detect_document_text(
                Document={
                    "S3Object": {
                        "Bucket": bucket,
                        "Name": s3_key,
                    }
                }
            )
            return self._parse_response([response])
        except ClientError as e:
            raise TextractError(f"Sync Textract call failed: {e}") from e

    # ------------------------------------------------------------------ #
    #  Async mode (multi-page PDF)
    # ------------------------------------------------------------------ #

    def _async_extract(self, bucket: str, s3_key: str) -> OCRResult:
        """Asynchronous multi-page extraction with polling."""
        try:
            start_resp = self.client.start_document_text_detection(
                DocumentLocation={
                    "S3Object": {
                        "Bucket": bucket,
                        "Name": s3_key,
                    }
                }
            )
            job_id = start_resp["JobId"]
            logger.info("Started async Textract job: %s", job_id)
        except ClientError as e:
            raise TextractError(f"Failed to start async job: {e}") from e

        # Poll for completion
        responses = self._poll_job(job_id)
        return self._parse_response(responses)

    def _poll_job(self, job_id: str) -> list[dict]:
        """Poll an async Textract job until it completes or fails."""
        responses: list[dict] = []
        delay = self.retry_delay

        for attempt in range(self.max_retries * 10):  # generous limit
            try:
                result = self.client.get_document_text_detection(JobId=job_id)
            except ClientError as e:
                raise TextractError(f"Polling failed: {e}") from e

            status = result.get("JobStatus", "")

            if status == "SUCCEEDED":
                responses.append(result)

                # Handle pagination
                next_token = result.get("NextToken")
                while next_token:
                    result = self.client.get_document_text_detection(
                        JobId=job_id, NextToken=next_token
                    )
                    responses.append(result)
                    next_token = result.get("NextToken")

                return responses

            elif status == "FAILED":
                msg = result.get("StatusMessage", "Unknown error")
                raise TextractError(f"Textract job failed: {msg}")

            # Still in progress
            logger.debug(
                "Job %s status: %s — retrying in %ds (attempt %d)",
                job_id, status, delay, attempt + 1,
            )
            time.sleep(delay)
            delay = min(delay * 1.5, 30)  # exponential backoff, cap at 30s

        raise TextractError(
            f"Textract job {job_id} did not complete within timeout"
        )

    # ------------------------------------------------------------------ #
    #  Response parsing
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_response(responses: list[dict]) -> OCRResult:
        """
        Parse one or more Textract response pages into an OCRResult.

        Extracts LINE blocks, computes average confidence, and counts
        pages.
        """
        lines: list[str] = []
        confidences: list[float] = []
        all_blocks: list[dict] = []
        pages: set[int] = set()

        for response in responses:
            blocks = response.get("Blocks", [])
            all_blocks.extend(blocks)

            for block in blocks:
                if block.get("BlockType") == "PAGE":
                    pages.add(block.get("Page", 1))

                if block.get("BlockType") == "LINE":
                    text = block.get("Text", "")
                    if text.strip():
                        lines.append(text)
                        confidences.append(block.get("Confidence", 0.0))

        avg_confidence = (
            sum(confidences) / len(confidences) if confidences else 0.0
        )

        return OCRResult(
            raw_text="\n".join(lines),
            confidence=avg_confidence,
            page_count=len(pages) or 1,
            blocks=all_blocks,
        )
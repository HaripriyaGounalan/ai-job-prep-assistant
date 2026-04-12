import os
import json
import logging
from ocr_pipeline.pipeline import OCRPipeline
from extraction_pipeline.graph import run_extraction
from comparison_pipeline.run_comparison import run_comparison
from ocr_pipeline.services.s3_service import S3Service
from config.settings import config
from pathlib import Path

logger = logging.getLogger(__name__)

def process_job(job_id: str, resume_path: str, jd_path: str):
    s3_service = S3Service()
    try:
        logger.info(f"Starting job {job_id}")
        
        # 1. OCR Pipeline
        logger.info(f"[{job_id}] Running OCR Pipeline...")
        pipeline = OCRPipeline(s3_service=s3_service)
        pipeline.initialize()
        ocr_result = pipeline.process_pair(resume_path, jd_path)

        if ocr_result.resume_output and ocr_result.resume_output.status == "FAILED":
            raise Exception(f"Resume OCR failed: {ocr_result.resume_output.error}")
        
        if ocr_result.job_description_output and ocr_result.job_description_output.status == "FAILED":
            raise Exception(f"Job Description OCR failed: {ocr_result.job_description_output.error}")

        if not ocr_result.resume_text or not ocr_result.job_description_text:
            raise Exception("OCR completed but returned empty text for one or both documents.")

        # 2. Extraction Pipeline
        extraction_state = run_extraction(
            resume_text=ocr_result.resume_text,
            job_description_text=ocr_result.job_description_text
        )

        if extraction_state.status == "failed":
            raise Exception(f"Extraction Pipeline Failed: {extraction_state.errors}")

        # 3. Comparison Pipeline
        comparison_result = run_comparison(extraction_state)

        # Build final output combining all tasks if needed, or just comparison result
        final_output = {
            "job_id": job_id,
            "status": "completed",
            "task1_session_id": ocr_result.session_id,
            "comparison": comparison_result.model_dump()
        }

        # Save to S3
        s3_service.store_processed_result(job_id, json.dumps(final_output, default=str))

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {str(e)}")
        error_output = {
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        }
        s3_service.store_processed_result(job_id, json.dumps(error_output))

    finally:
        # Cleanup local files
        try:
            if os.path.exists(resume_path):
                os.remove(resume_path)
            if os.path.exists(jd_path):
                os.remove(jd_path)
        except Exception as cleanup_error:
            logger.error(f"Failed to clean up files for job {job_id}: {cleanup_error}")

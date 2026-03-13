#!/usr/bin/env python3
"""
Task 2 demo.

Flow:
1. Storage (upload files)
2. Detect text (Textract)
3. Extract (LLM structured output)
"""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# Allow importing project packages from project root
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

from Chalicelib.task2_processing.extraction.extraction_service import extract_all
from Chalicelib.task1_storage.storage_service import StorageService
from Chalicelib.task2_processing.ocr.textract_service import TextractService


REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("BUCKET_NAME", "ai-job-prep-assistant-715985805749")
MIN_CONFIDENCE = 70.0
ASSETS_DIR = PROJECT_ROOT / "assets"
RESUME_FILE = ASSETS_DIR / "Resume.pdf"
JOB_FILE = ASSETS_DIR / "Job_description.pdf"
FALLBACK_JOB_FILE = ASSETS_DIR / "job_post.png"


def ensure_bucket(s3_client, bucket_name: str) -> bool:
    """Create S3 bucket if it does not exist."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code == "404":
            pass
        elif code == "403":
            print(f"Bucket '{bucket_name}' exists but is owned by another account.")
            return False
        else:
            raise

    try:
        if REGION == "us-east-1":
            s3_us_east = boto3.client("s3", region_name="us-east-1", endpoint_url="https://s3.amazonaws.com")
            s3_us_east.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": REGION},
            )
        print(f"Created bucket: {bucket_name}")
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "BucketAlreadyOwnedByYou":
            raise
    return True


def image_bytes(image_path: Path) -> tuple[bytes, str] | None:
    """Read image bytes; convert WebP to PNG when Pillow is available."""
    suffix = image_path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png"}:
        return image_path.read_bytes(), image_path.name

    if suffix == ".webp":
        if not HAS_PILLOW:
            print("Install Pillow to use .webp files: pip install Pillow")
            return None
        img = Image.open(image_path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue(), image_path.stem + ".png"

    print(f"Unsupported image format: {suffix}")
    return None


def prepare_file_bytes(file_path: Path) -> tuple[bytes, str] | None:
    """Read PDF or image bytes for upload."""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return file_path.read_bytes(), file_path.name
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        return image_bytes(file_path)
    print(f"Unsupported file type: {ext}")
    return None


def lines_to_text(lines: list[dict]) -> str:
    """Join Textract lines into plain text."""
    return "\n".join(line.get("text", "").strip() for line in lines if line.get("text"))


def print_detected_lines(label: str, lines: list[dict]) -> None:
    """Print each detected line with confidence score."""
    print(f"\n   {label} lines with confidence:")
    if not lines:
        print("   (no lines)")
        return

    for line in lines:
        text = str(line.get("text", "")).strip()
        conf = float(line.get("confidence", 0.0))
        mark = "✓" if conf >= MIN_CONFIDENCE else "✗"
        print(f"   [{mark}] \"{text}\" (confidence: {conf:.1f}%)")


def resolve_input_files() -> tuple[Path, Path] | None:
    """Pick resume and job description files from assets/."""
    if not RESUME_FILE.is_file():
        print(f"Resume file not found: {RESUME_FILE}")
        return None

    if JOB_FILE.is_file():
        job_path = JOB_FILE
    elif FALLBACK_JOB_FILE.is_file():
        job_path = FALLBACK_JOB_FILE
    else:
        print("Job file not found. Expected assets/Job_description.pdf or assets/job_post.png")
        return None

    return RESUME_FILE, job_path


def step_1_storage(storage: StorageService, resume_path: Path, job_path: Path) -> dict[str, str] | None:
    """Step 1: Upload resume and job files."""
    print("\n1. Storage...")

    resume_data = prepare_file_bytes(resume_path)
    job_data = prepare_file_bytes(job_path)
    if not resume_data or not job_data:
        return None

    resume_bytes, resume_name = resume_data
    job_bytes, job_name = job_data

    resume_upload = storage.upload_file(resume_bytes, resume_name)
    job_upload = storage.upload_file(job_bytes, job_name)

    print(f"   Resume uploaded: {resume_upload['filename']}")
    print(f"   Resume URL:      {resume_upload['url']}")
    print(f"   Job uploaded:    {job_upload['filename']}")
    print(f"   Job URL:         {job_upload['url']}")

    return {
        "resume_key": resume_name,
        "job_key": job_name,
    }


def step_2_detect_text(textract: TextractService, keys: dict[str, str]) -> dict[str, str]:
    """Step 2: Detect text from uploaded files."""
    print("\n2. Detecting text (line-level)...")

    resume_lines = textract.detect_text(keys["resume_key"])
    job_lines = textract.detect_text(keys["job_key"])

    print(f"\n   Resume lines found: {len(resume_lines)}")
    print_detected_lines("Resume", resume_lines)
    print(f"\n   Job lines found:    {len(job_lines)}")
    print_detected_lines("Job", job_lines)

    return {
        "resume_text": lines_to_text(resume_lines),
        "job_text": lines_to_text(job_lines),
    }


def step_3_extract(texts: dict[str, str]) -> dict:
    """Step 3: Build structured result from OCR text."""
    print("\n3. Extracting structured output...")
    return extract_all(texts["resume_text"], texts["job_text"])


def main() -> None:
    sts = boto3.client("sts")
    print("caller:",sts.get_caller_identity())

    print("TASK 2 EXTRACTOR - Demo")
    print("=" * 60)

    files = resolve_input_files()
    if not files:
        return

    resume_path, job_path = files
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Resume: {resume_path}")
    print(f"Job:    {job_path}")

    s3 = boto3.client("s3", region_name=REGION)
    if not ensure_bucket(s3, BUCKET_NAME):
        return

    storage = StorageService(BUCKET_NAME, region=REGION)
    textract = TextractService(BUCKET_NAME, region=REGION)

    # 1. Storage (upload files)
    upload_keys = step_1_storage(storage, resume_path, job_path)
    if not upload_keys:
        return
    
    # 2. Detect text (Textract)
    texts = step_2_detect_text(textract, upload_keys)
    if not texts["resume_text"] or not texts["job_text"]:
        print("No text found in one or both files.")
        return

    # 3. Extract (LLM structured output)
    structured = step_3_extract(texts)
    print("   Structured extraction completed.")
    print("\nStructured output:")
    print(json.dumps(structured, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

# Task Handover (OCR + Extraction Pipeline)

## 1) What is completed

- End-to-end demo pipeline is working from local script run.
- Current flow:
  1. Upload resume and job description to S3
  2. Run OCR via Textract
  3. Run structured extraction via Bedrock LLM
  4. Print JSON output
- Last local run completed successfully (exit code 0).

## 2) Core files and ownership map

- `app/demo_task2.py`
  - Integration/demo runner (current entry point for testing).
  - Handles env loading, file preparation, bucket check/create, orchestration, and output printing.
- `app/Chalicelib/task1_storage/storage_service.py`
  - S3 upload abstraction.
- `app/Chalicelib/task2_processing/ocr/textract_service.py`
  - Textract OCR abstraction (sync for images, async polling for PDFs).
- `app/Chalicelib/task2_processing/ocr/text_cleaner.py`
  - OCR text cleanup utility.
- `app/Chalicelib/task2_processing/extraction/bedrock_service.py`
  - Bedrock runtime wrapper and model invocation.
- `app/Chalicelib/task2_processing/extraction/prompts.py`
  - Prompt templates for job/resume extraction.
- `app/Chalicelib/task2_processing/extraction/schemas.py`
  - JSON schema shape references.
- `app/Chalicelib/task2_processing/extraction/extraction_service.py`
  - Extraction orchestration and JSON parsing.

## 3) Runtime assumptions

- Python dependencies from `requirements.txt`:
  - boto3
  - Pillow
  - python-dotenv
- Expected assets in `app/assets`:
  - `Resume.pdf`
  - `Job_description.pdf` (pdf)
  - `job_post.png` (image)
- `.env` is read from `app/.env` by the demo script.

## 4) Environment variables used

Required/important:
- `AWS_REGION` (default: `us-east-1`)
- `BUCKET_NAME` (recommended to set explicitly in `app/.env`)
- `BEDROCK_MODEL_ID` (optional override)

Credential options:
- Recommended: standard AWS credential chain (profile/role).
- Optional explicit vars supported by Bedrock service:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`

## 5) AWS permissions needed

At minimum:
- S3: `HeadBucket`, `CreateBucket`, `PutObject`, `GetObject`
- Textract: `DetectDocumentText`, `StartDocumentTextDetection`, `GetDocumentTextDetection`
- Bedrock Runtime: `Converse` (for selected model)
- STS: `GetCallerIdentity` (used in demo script)

## 6) Output contract currently produced

Top-level JSON keys:
- `job_requirements`
- `candidate_profile`

Source function:
- `extract_all(resume_text, job_text)` in extraction service.

## 7) Minimal run instructions for team

Teammates only need to do this:

1. update `app/.env` with .env file

2. Run from repository root:

```bash
python app/demo_task2.py
```

3. Expected result: console prints structured JSON with `job_requirements` and `candidate_profile`.

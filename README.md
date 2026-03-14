# AI Job Preparation Assistant

A cloud-based AI pipeline for a Machine Learning school project. Users upload a
resume and a job description (PDF or screenshot). The system extracts text,
identifies required skills, compares them with the resume, computes a match
score, estimates salary range, and generates interview preparation questions.

---

## Project Status

### Completed

| Task | Name | Description | Status |
|------|------|-------------|--------|
| 1 | File Storage + OCR | Upload files to S3, run Textract OCR, clean text | Done (40 tests) |
| 2 | LangGraph Extraction | Extract structured job requirements and candidate profile via Bedrock | Done (51 tests) |

### Still To Do

| Task | Name | Description | Status |
|------|------|-------------|--------|
| 3 | Comparison, Scoring, Recommendations | Compare JD vs resume skills, compute match score, identify gaps, generate interview questions and upskilling suggestions via LLM | Not started |
| 4 | Backend Integration (FastAPI) | Wire Tasks 1-3 behind REST endpoints: `POST /upload`, `POST /analyze`, `GET /result/{id}`, `GET /health` | Not started |
| 5 | React + shadcn/ui Frontend | Upload UI, processing status, results dashboard with score card, skills gap table, recommendation cards, interview question accordion | Not started |

### What Task 3 will receive from Task 2

Task 2 outputs an `ExtractionState` with typed `JobRequirements` and
`CandidateProfile` objects. Task 3 will consume these to:

- Run **deterministic code** for skill overlap, missing skills, and match percentage
- Call the **LLM** for strengths/gaps explanation, study recommendations, interview prep questions, and salary summary

### What Task 4 will wire together

FastAPI will orchestrate the full flow: accept file uploads, call Task 1 (OCR),
pipe the cleaned text into Task 2 (extraction), feed structured data into
Task 3 (comparison + scoring), and return the final JSON result.

---

## Architecture

```
Task 1                     Task 2                          Task 3 (TODO)
┌──────────────┐           ┌──────────────────────┐        ┌──────────────────┐
│ Validate     │           │  LangGraph Workflow   │        │ Deterministic    │
│ Upload to S3 │── text ──▶│                      │── ──▶│  skill overlap   │
│ Textract OCR │           │ ┌────────┐ ┌───────┐ │        │  match score     │
│ Clean text   │           │ │ JD     │ │Resume │ │        │  missing skills  │
└──────────────┘           │ │Extract │ │Extract│ │        ├──────────────────┤
                           │ └───┬────┘ └──┬────┘ │        │ LLM-powered      │
                           │     └────┬────┘      │        │  gap explanation │
                           │     ┌────▼───┐       │        │  recommendations │
                           │     │Finalize│       │        │  interview Qs    │
                           │     └────────┘       │        │  salary estimate │
                           └──────────────────────┘        └──────────────────┘
                                                                    │
                                                                    ▼
                                                           Task 4: FastAPI
                                                           Task 5: React UI
```

---

## Codebase Structure

```
job-prep-assistant/
│
├── config/
│   ├── __init__.py
│   └── settings.py                  # All env-based config (AWS, S3, Textract, Bedrock)
│
├── ocr_pipeline/                    # ── TASK 1: File Storage + OCR ──
│   ├── __init__.py
│   ├── models.py                    # FileMetadata, OCRResult, PipelineOutput, FullPipelineResult
│   ├── pipeline.py                  # Main orchestrator (validate → upload → OCR → clean → store)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── s3_service.py            # S3 bucket management, upload, download, presigned URLs
│   │   └── textract_service.py      # Textract sync (images) + async (multi-page PDF) with polling
│   └── utils/
│       ├── __init__.py
│       ├── file_validator.py        # File extension, size, and integrity checks
│       └── text_cleaner.py          # 7-step OCR text cleaning + section extraction
│
├── extraction_pipeline/             # ── TASK 2: LangGraph/LangChain Extraction ──
│   ├── __init__.py
│   ├── models.py                    # Pydantic models: JobRequirements, CandidateProfile, ExtractionState
│   ├── llm_client.py               # Amazon Bedrock wrapper with retries + robust JSON parsing
│   ├── graph.py                     # LangGraph StateGraph definition + run_extraction() entry point
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── extract_job.py           # Graph node: JD text → JobRequirements
│   │   └── extract_resume.py        # Graph node: resume text → CandidateProfile
│   └── prompts/
│       ├── __init__.py
│       └── extraction_prompts.py    # System + user prompt templates with embedded JSON schema
│
├── tests/
│   ├── __init__.py
│   ├── fixtures.py                  # Shared sample texts + mock LLM responses
│   │
│   │  # Task 1 tests (40 total)
│   ├── test_file_validator.py       #  8 tests — extension, size, empty, directory checks
│   ├── test_text_cleaner.py         # 14 tests — unicode, OCR artifacts, whitespace, sections
│   ├── test_s3_service.py           #  8 tests — bucket creation, upload, download, presigned URLs
│   ├── test_textract_service.py     #  6 tests — sync/async extraction, pagination, error handling
│   ├── test_pipeline.py             #  4 tests — end-to-end OCR pipeline integration
│   │
│   │  # Task 2 tests (51 total)
│   ├── test_extraction_models.py    # 11 tests — Pydantic model validation, serialization roundtrips
│   ├── test_extraction_prompts.py   #  8 tests — prompt structure, schema embedding, text injection
│   ├── test_llm_client.py           # 14 tests — JSON parsing (fences, preamble, nesting), retries
│   ├── test_extraction_nodes.py     #  7 tests — node success, empty input, LLM errors, validation
│   └── test_extraction_graph.py     # 11 tests — full graph invocation, partial/failed states, serialization
│
├── samples/
│   ├── resume.txt                   # Sample resume text (for Task 2 standalone testing)
│   └── jd.txt                       # Sample job description text
│
├── demo_run.py                      # Run Task 1 + Task 2 against real AWS services
├── main.py                          # CLI entry point for Task 1
├── requirements.txt
├── pytest.ini
├── .env.example                     # Environment variable template
└── README.md
```

---

## Dependencies

### Runtime

| Package | Version | Purpose |
|---------|---------|---------|
| `boto3` | >= 1.34.0 | AWS SDK — S3, Textract, Bedrock Runtime |
| `botocore` | >= 1.34.0 | Low-level AWS client (comes with boto3) |
| `python-dotenv` | >= 1.0.0 | Load `.env` file into environment |
| `pydantic` | >= 2.5.0 | Strict JSON schema validation for LLM output |
| `langgraph` | >= 0.2.0 | Stateful graph workflows with parallel execution |
| `langchain` | >= 0.3.0 | LLM prompt/model tooling |
| `langchain-core` | >= 0.3.0 | Core abstractions for LangChain |
| `Pillow` | >= 10.0.0 | Image handling utilities |
| `pdf2image` | >= 1.16.3 | PDF to image conversion (for Textract) |

### Testing only

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | >= 7.4.0 | Test runner |
| `pytest-mock` | >= 3.12.0 | Mock utilities |
| `moto[s3,textract]` | >= 5.0.0 | AWS service mocking (no credentials needed) |

### AWS services used

| Service | Task | Purpose |
|---------|------|---------|
| Amazon S3 | Task 1 | File storage under `uploads/` and `processed/` prefixes |
| Amazon Textract | Task 1 | OCR on PDFs and images (sync + async modes) |
| Amazon Bedrock | Task 2 | LLM invocation (Claude 3 Sonnet) for structured extraction |

---

## Setup

### 1. Install dependencies

```bash
cd job-prep-assistant
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your values. At minimum you need:

```
AWS_ACCESS_KEY_ID=AKIA...your-key...
AWS_SECRET_ACCESS_KEY=wJalr...your-secret...
AWS_REGION=us-east-1
S3_BUCKET_NAME=my-unique-bucket-name-12345
```

All other variables have sensible defaults. See `.env.example` for the full list.

### 3. Required AWS IAM permissions

Your IAM user/role needs these permissions:

```
s3:CreateBucket, s3:PutObject, s3:GetObject, s3:HeadBucket,
s3:PutBucketVersioning, s3:PutPublicAccessBlock, s3:ListBucket

textract:DetectDocumentText, textract:StartDocumentTextDetection,
textract:GetDocumentTextDetection

bedrock:InvokeModel
```

---

## Running the Pipelines

### Run tests (no AWS credentials required)

Tests use `moto` for S3/Textract mocking and `unittest.mock` for Bedrock.
All 91 tests run entirely locally.

```bash
# All 91 tests
pytest

# Verbose output
pytest -v

# Task 1 only (40 tests)
pytest tests/test_file_validator.py tests/test_text_cleaner.py \
       tests/test_s3_service.py tests/test_textract_service.py \
       tests/test_pipeline.py

# Task 2 only (51 tests)
pytest tests/test_extraction_models.py tests/test_extraction_prompts.py \
       tests/test_llm_client.py tests/test_extraction_nodes.py \
       tests/test_extraction_graph.py

# Specific test area
pytest -k "s3"                # S3 service tests
pytest -k "llm_client"        # Bedrock client + JSON parsing
pytest -k "graph"             # LangGraph workflow integration
```

### Run against real AWS services

The `demo_run.py` script runs the actual pipelines against live AWS.

#### Full pipeline: Task 1 (OCR) → Task 2 (extraction)

Requires: S3 + Textract + Bedrock access, and real PDF/image files.

```bash
python demo_run.py --resume ./my_resume.pdf --job-desc ./job_posting.png
```

#### Task 1 only (OCR + text cleaning)

Requires: S3 + Textract access.

```bash
python demo_run.py --resume ./my_resume.pdf --job-desc ./job_posting.png --step 1
```

#### Task 2 only (extraction from pre-existing text)

Requires: Bedrock access only. No S3 or Textract needed. Use this to
test the extraction pipeline without needing real PDFs.

Sample text files are included in `samples/`.

```bash
python demo_run.py --resume-text ./samples/resume.txt --jd-text ./samples/jd.txt --step 2
```

#### Save output to JSON

```bash
python demo_run.py --resume ./my_resume.pdf --job-desc ./job_posting.png --output result.json
```

#### Verbose mode (debug logging from boto3, LangGraph, etc.)

```bash
python demo_run.py --resume ./my_resume.pdf --job-desc ./job_posting.png -v
```

### Task 1 CLI (standalone)

The `main.py` script provides a simpler CLI for Task 1 only.

```bash
# Process a pair, print summary
python main.py --resume resume.pdf --job-desc jd.png

# Single file
python main.py --resume resume.pdf

# JSON output
python main.py --resume resume.pdf --job-desc jd.png --json
```

---

## Task 2 Output Contract

Task 2 returns an `ExtractionState` with this JSON structure. This is
the input contract for Task 3.

```json
{
  "status": "completed",
  "job_requirements": {
    "job_title": "Software Engineer - Cloud Infrastructure",
    "company_name": "Acme Corp",
    "location": "San Francisco, CA (Hybrid)",
    "required_skills": ["Python", "Go", "AWS", "Kubernetes", "CI/CD"],
    "preferred_skills": ["Terraform", "SRE", "Datadog", "gRPC"],
    "years_experience_required": 5,
    "tools_and_technologies": ["AWS EC2", "AWS S3", "Kubernetes", "Terraform"],
    "education_requirements": ["BS in Computer Science or equivalent"],
    "key_responsibilities": ["Design cloud-native microservices", "..."],
    "employment_type": "Full-time",
    "salary_range": "$180,000 - $240,000 + equity"
  },
  "candidate_profile": {
    "candidate_name": "Jane Doe",
    "contact_info": "jane.doe@email.com | ...",
    "resume_skills": ["Python", "Go", "AWS", "Kubernetes", "Docker", "..."],
    "resume_experience": [
      {
        "title": "Senior Software Engineer",
        "company": "TechCorp Inc.",
        "duration": "Mar 2021 - Present",
        "highlights": ["Led microservices migration", "..."]
      }
    ],
    "total_years_experience": 7,
    "resume_experience_summary": "Senior engineer with 7 years...",
    "resume_projects": [
      {
        "name": "Cloud Cost Optimizer",
        "description": "Automated AWS cost analysis tool",
        "technologies": ["Python", "Boto3", "Lambda"]
      }
    ],
    "education": ["BS Computer Science, Stanford University, 2016"],
    "certifications": ["AWS Solutions Architect - Professional"]
  },
  "errors": []
}
```

---

## S3 Bucket Structure

```
{S3_BUCKET_NAME}/
├── uploads/
│   ├── resumes/{file_id}/original_filename.pdf
│   └── job-descriptions/{file_id}/original_filename.png
└── processed/
    └── {file_id}/result.json
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| OCR as a separate task | Isolates file handling from AI logic; easier to debug and test independently |
| 7-step text cleaner | Removes OCR artifacts (smart quotes, zero-width chars, page numbers, broken hyphenation) before LLM processing |
| Textract sync + async | Images use fast synchronous API; multi-page PDFs automatically fall back to async with polling |
| LangGraph parallel fan-out | JD and resume extraction are independent reads — parallel execution halves latency |
| Pydantic as the schema source | One model drives the prompt, validates the response, and types downstream code |
| Bedrock client with dependency injection | Every service accepts an optional mock client; the full test suite runs without AWS credentials |
| Errors accumulate, never crash | Both extraction nodes append to a shared error list; partial results are still usable |
| Prompts separated from logic | Prompt templates live in their own module so you can iterate on wording without touching node code |
| Temperature 0.0 for extraction | Deterministic output for structured JSON — no creativity needed here |

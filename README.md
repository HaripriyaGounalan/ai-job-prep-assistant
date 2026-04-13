# Aligno

A cloud-based AI pipeline for a Machine Learning school project. Users upload a
resume and a job description (PDF or screenshot). The system extracts text,
identifies required skills, compares them with the resume, computes a match
score, estimates salary range, and generates interview preparation questions.
The repo now also includes the Aligno frontend, a Bun + Vite + shadcn/ui app
with a live upload flow, polling dashboard, and light/dark theme toggle.

---

## Project Status

### Completed

| Task | Name                                 | Description                                                                                                                | Status          |
| ---- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- | --------------- |
| 1    | File Storage + OCR                   | Upload files to S3, run Textract OCR, clean text                                                                           | Done (40 tests) |
| 2    | LangGraph Extraction                 | Extract structured job requirements and candidate profile via Bedrock                                                      | Done (51 tests) |
| 3    | Comparison, Scoring, Recommendations | 5-layer pipeline: skill normalization, ontology matching, semantic similarity, deterministic scoring, Bedrock LLM insights | Done (77 tests) |
| 4    | Backend Integration (FastAPI)        | Wire Tasks 1–3 behind REST endpoints: `POST /upload`, `GET /status/{id}`, `GET /result/{id}`, `GET /health`                | Done (9 tests)  |

### Still To Do

| Task | Name                       | Description                                                                                                                           | Status      |
| ---- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| 5    | React + shadcn/ui Frontend | Upload UI, processing status, results dashboard with score card, skills gap table, recommendation cards, interview question cards | Done        |

### How Tasks 1 → 2 → 3 connect

**Task 1** uploads and OCR-processes both files, outputting two cleaned text
strings (`resume_text`, `job_description_text`).

**Task 2** takes those strings, runs them in parallel through a LangGraph
`StateGraph` backed by AWS Bedrock (Claude), and outputs a typed `ExtractionState`
with `JobRequirements` and `CandidateProfile` objects.

**Task 3** consumes the `ExtractionState` and runs it through a 5-layer
comparison engine (normalize → ontology → semantic similarity → deterministic
scoring → LLM insights), returning a `ComparisonResult` with scores, skill gap
lists, upskilling recommendations, interview questions, and salary context.

### How Task 4 (Backend API) orchestrates the flow

**Task 4** wraps Tasks 1–3 in an asynchronous FastAPI web server. 
It uses non-blocking `BackgroundTasks` to orchestrate the entire end-to-end flow:
1. `POST /upload` accepts files and instantly returns a tracking UUID.
2. The background worker uploads files, runs OCR, triggers Bedrock extraction, evaluates the CV, and dumps the final JSON state to S3.
3. The frontend safely polls AWS S3 via `GET /status/{job_id}` and `GET /result/{job_id}` without hanging or suffering from proxy timeouts.

### How Task 5 (Frontend UI) fits in

**Task 5** adds a Bun-powered React frontend in `frontend/` built with Vite and
shadcn/ui. It lets users upload both files, watch live progress via polling,
review the comparison dashboard, inspect skill gaps, and switch between light
and dark themes.

---

## Architecture

```
Task 1                     Task 2                          Task 3
┌──────────────┐           ┌──────────────────────┐        ┌──────────────────┐
│ Validate     │           │  LangGraph Workflow   │        │ L1 Normalize     │
│ Upload to S3 │── text ──▶│                      │──────▶│ L2 Ontology      │
│ Textract OCR │           │ ┌────────┐ ┌───────┐ │        │ L3 Semantic Sim  │
│ Clean text   │           │ │ JD     │ │Resume │ │        │ L4 Score         │
└──────────────┘           │ │Extract │ │Extract│ │        ├──────────────────┤
                           │ └───┬────┘ └──┬────┘ │        │ L5 LLM-powered   │
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
│   ├── llm_client.py                # Amazon Bedrock wrapper with retries + robust JSON parsing
│   ├── graph.py                     # LangGraph StateGraph definition + run_extraction() entry point
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── extract_job.py           # Graph node: JD text → JobRequirements
│   │   └── extract_resume.py        # Graph node: resume text → CandidateProfile
│   └── prompts/
│       ├── __init__.py
│       └── extraction_prompts.py    # System + user prompt templates with embedded JSON schema
│
├── comparison_pipeline/             # ── TASK 3: Comparison, Scoring & Recommendations ──
│   ├── __init__.py                  # Exports run_comparison and ComparisonResult
│   ├── models.py                    # Pydantic models: SkillMatch, LLMInsights, ComparisonResult
│   ├── normalizer.py                # Layer 1: SKILL_ALIASES (~50 entries), normalize_skill()
│   ├── ontology.py                  # Layer 2: SKILL_ONTOLOGY (~25 entries), exact/alias/related matching
│   ├── similarity.py                # Layer 3: all-MiniLM-L6-v2 cosine similarity with thresholds
│   ├── scorer.py                    # Layer 4: skill score, experience score, education match, overall score
│   ├── llm_layer.py                 # Layer 5: single Bedrock call (temp 0.3) → validated LLMInsights
│   └── run_comparison.py            # Orchestrator: runs all 5 layers, returns ComparisonResult
│
├── backend/                         # ── TASK 4: FastAPI Server & Orchestration ──
│   ├── __init__.py
│   ├── main.py                      # FastAPI app, CORS, routes (/upload, /status, /result, /health)
│   ├── schemas.py                   # Pydantic models for API request/response validation
│   └── services.py                  # Background task worker orchestrating Tasks 1-3 sequentially
│
├── frontend/                        # ── TASK 5: Bun + Vite + shadcn/ui Frontend ──
│   ├── src/
│   │   ├── App.tsx                  # Main upload workspace + results dashboard
│   │   ├── components/              # Theme toggle + shadcn UI components
│   │   └── lib/                     # API/result types + preview data
│   ├── package.json
│   └── components.json              # shadcn/ui configuration
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
│   ├── test_extraction_graph.py     # 11 tests — full graph invocation, partial/failed states, serialization
│   │
│   │  # Task 3 tests (77 total)
│   ├── test_normalizer.py           # 17 tests — alias resolution, dedup, edge cases
│   ├── test_ontology.py             # 12 tests — exact, alias, related, none match types
│   ├── test_similarity.py           #  9 tests — cosine similarity, short-string guard, thresholds
│   ├── test_scorer.py               # 22 tests — skill score, experience fallback, education match, overall
│   ├── test_llm_layer.py            #  7 tests — message structure, 5-question enforcement, graceful failure
│   └── test_comparison_pipeline.py  # 10 tests — end-to-end integration, edge cases, real-world fixture
│
│   │  # Task 4 tests (9 total)
│   ├── test_api.py                  #  6 tests — request validation, routing, HTTP responses, S3 polling
│   ├── test_services.py             #  2 tests — orchestrated pipeline execution, error handling/checkpoints
│   └── test_backend_integration.py  #  1 test  — full E2E mock hitting simulated AWS without patching routes
│
├── samples/
│   ├── resume.pdf                   # Sample resume (John Doe)
│   ├── Jd.pdf                       # Sample job description (TD ML Engineer)
│   ├── resume.txt                   # Pre-extracted resume text (for --step 3 standalone)
│   └── jd.txt                       # Pre-extracted JD text (for --step 3 standalone)
│
├── demo_run.py                      # Run Tasks 1 + 2 + 3 against real AWS; supports --step flag
├── main.py                          # CLI entry point for Task 1
├── requirements.txt
├── pytest.ini
├── .env.example                     # Environment variable template
└── README.md
```

---

## Dependencies

### Runtime

| Package                 | Version   | Purpose                                                   |
| ----------------------- | --------- | --------------------------------------------------------- |
| `fastapi`               | >= 0.100  | REST API framework (Task 4 backend)                       |
| `uvicorn`               | >= 0.20   | ASGI web server for FastAPI                               |
| `python-multipart`      | >= 0.0.5  | Required for `UploadFile` (FastAPI file parsing)          |
| `boto3`                 | >= 1.34.0 | AWS SDK — S3, Textract, Bedrock Runtime                   |
| `botocore`              | >= 1.34.0 | Low-level AWS client (comes with boto3)                   |
| `python-dotenv`         | >= 1.0.0  | Load `.env` file into environment                         |
| `pydantic`              | >= 2.5.0  | Strict JSON schema validation for LLM output              |
| `langgraph`             | >= 0.2.0  | Stateful graph workflows with parallel execution          |
| `langchain`             | >= 0.3.0  | LLM prompt/model tooling                                  |
| `langchain-core`        | >= 0.3.0  | Core abstractions for LangChain                           |
| `sentence-transformers` | >= 2.2.0  | Semantic skill similarity via all-MiniLM-L6-v2 embeddings |
| `Pillow`                | >= 10.0.0 | Image handling utilities                                  |
| `pdf2image`             | >= 1.16.3 | PDF to image conversion (for Textract)                    |

### Testing only

| Package             | Version   | Purpose                                     |
| ------------------- | --------- | ------------------------------------------- |
| `pytest`            | >= 7.4.0  | Test runner                                 |
| `pytest-mock`       | >= 3.12.0 | Mock utilities                              |
| `moto[s3,textract]` | >= 5.0.0  | AWS service mocking (no credentials needed) |

### Frontend toolchain

| Package         | Version | Purpose                                              |
| --------------- | ------- | ---------------------------------------------------- |
| `bun`           | 1.x     | Frontend package manager and script runner           |
| `vite`          | ^8      | React frontend build tool                            |
| `react`         | ^19     | Frontend component runtime                           |
| `tailwindcss`   | ^4      | Utility-first styling + design tokens                |
| `shadcn/ui`     | latest  | Source-first component system used in `frontend/src` |
| `lucide-react`  | ^1.8    | Icon set used by the dashboard and theme toggle      |

### AWS services used

| Service         | Task   | Purpose                                                                               |
| --------------- | ------ | ------------------------------------------------------------------------------------- |
| Amazon S3       | Task 1 | File storage under `uploads/` and `processed/` prefixes                               |
| Amazon Textract | Task 1 | OCR on PDFs and images (sync + async modes)                                           |
| Amazon Bedrock  | Task 2 | LLM invocation (Claude) for structured extraction — 2 calls (JD + resume in parallel) |
| Amazon Bedrock  | Task 3 | LLM invocation (Claude) for career insights — 1 call per comparison                   |

---

## Setup

### 1. Install dependencies

```bash
cd job-prep-assistant
pip install -r requirements.txt
```

### 1b. Install frontend dependencies

```bash
cd frontend
bun install
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
BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
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
All 168 tests run entirely locally.

```bash
# All 168 tests
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

# Task 3 only (77 tests)
pytest tests/test_normalizer.py tests/test_ontology.py tests/test_similarity.py \
       tests/test_scorer.py tests/test_llm_layer.py tests/test_comparison_pipeline.py

# Task 4 Backend only (9 tests)
pytest tests/test_api.py tests/test_services.py tests/test_backend_integration.py
```

### Run against real AWS services

#### Quick Command Reference

| Goal                    | Command                                                                                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Install deps            | `pip install -r requirements.txt`                                                                                                                                   |
| Install frontend deps   | `cd frontend && bun install`                                                                                                                                        |
| Start Backend Server    | `python -m backend.main`                                                                                                                                            |
| Start Frontend Dev App  | `cd frontend && bun dev`                                                                                                                                             |
| Quick import check      | `python -c "from comparison_pipeline import run_comparison; print('OK')"`                                                                                           |
| Run all tests           | `pytest -v`                                                                                                                                                         |
| Run Task 3 tests only   | `pytest tests/test_normalizer.py tests/test_ontology.py tests/test_similarity.py tests/test_scorer.py tests/test_llm_layer.py tests/test_comparison_pipeline.py -v` |
| Task 3 with text files  | `python demo_run.py --resume-text samples/resume.txt --jd-text samples/jd.txt --step 3` _(Note: requires pre-extracted .txt files in samples/)_                     |
| Full pipeline with PDFs | `python demo_run.py --resume samples/resume.pdf --job-desc samples/Jd.pdf`                                                                                          |
| Full pipeline + save    | `python demo_run.py --resume samples/resume.pdf --job-desc samples/Jd.pdf -o task3_result.json`                                                                     |

#### Full pipeline: Tasks 1 + 2 + 3

```bash
python demo_run.py --resume samples/resume.pdf --job-desc samples/Jd.pdf
```

#### Save output to JSON

```bash
python demo_run.py --resume samples/resume.pdf --job-desc samples/Jd.pdf -o task3_result.json
```

#### Skip OCR — run Task 2 + Task 3 from pre-extracted text

Requires only Bedrock access (no S3 or Textract). `samples/resume.txt` and `samples/jd.txt` must exist.

```bash
python demo_run.py --resume-text samples/resume.txt --jd-text samples/jd.txt --step 3
```

#### Task 2 only (extraction from text)

```bash
python demo_run.py --resume-text samples/resume.txt --jd-text samples/jd.txt --step 2
```

#### Task 1 only (OCR only)

```bash
python demo_run.py --resume samples/resume.pdf --job-desc samples/Jd.pdf --step 1
```

#### Verbose mode

```bash
python demo_run.py --resume samples/resume.pdf --job-desc samples/Jd.pdf -v
```

### Verify imports

```bash
python -c "from comparison_pipeline import run_comparison; print('OK')"
python -c "from extraction_pipeline import run_extraction; print('OK')"
python -c "from ocr_pipeline.pipeline import OCRPipeline; print('OK')"
python -c "from backend.main import app; print('OK')"
```

All four should print `OK`.

---

## Backend API Usage (Task 4)

Start the production-ready FastAPI server:

```bash
python -m backend.main
```

By default, the server will bind to `127.0.0.1` and port `8000`. You can easily override these by defining variables in your `.env` file (or exporting them in your terminal run):
```env
HOST=0.0.0.0
PORT=8000
```

Once running, view the interactive Swagger API documentation at your configured address, typically:
- `http://127.0.0.1:8000/docs`

### Example Workflow
1. **Upload Files:** `POST /upload`
    Submit `resume` and `job_description` files as `multipart/form-data`.
    *Returns `{"job_id": "uuid"}`.*
2. **Poll Status:** `GET /status/{job_id}`
    Check the state of processing (e.g., `processing`, `completed`, `failed`).
3. **Get Results:** `GET /result/{job_id}`
    Retrieve the full compiled AI analysis JSON when `completed`.

---

## Frontend Usage (Task 5)

Start the FastAPI backend first:

```bash
python -m backend.main
```

In a second terminal, start the Bun frontend:

```bash
cd frontend
bun dev
```

By default the frontend targets `http://127.0.0.1:8000`. To point it at a
different backend, create `frontend/.env.local` and set:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Open the Vite URL shown in the terminal (typically `http://127.0.0.1:5173`).
The frontend includes:

- file upload fields for `resume` and `job_description`
- live polling against `/status/{job_id}` and `/result/{job_id}`
- score cards, skill coverage table, recommendations, and interview prompts
- a built-in light/dark toggle

---

## Task 3 Output Contract

Task 3 returns a `ComparisonResult` with this JSON structure. This is the input
contract for Task 4.

```json
{
 "overall_score": 62.0,
 "skill_score": 52.5,
 "experience_score": 100.0,
 "education_matched": false,

 "required_skill_matches": [
  {
   "skill": "python",
   "match_type": "exact",
   "score": 1.0,
   "matched_to": "python"
  },
  {
   "skill": "deep learning",
   "match_type": "related",
   "score": 0.75,
   "matched_to": "machine learning"
  },
  { "skill": "c", "match_type": "none", "score": 0.0, "matched_to": null }
 ],

 "preferred_skill_matches": [
  {
   "skill": "tensorflow",
   "match_type": "exact",
   "score": 1.0,
   "matched_to": "tensorflow"
  },
  {
   "skill": "pytorch",
   "match_type": "related",
   "score": 0.75,
   "matched_to": "tensorflow"
  },
  {
   "skill": "langgraph",
   "match_type": "none",
   "score": 0.0,
   "matched_to": null
  }
 ],

 "missing_required_skills": ["c", "c++"],
 "missing_preferred_skills": ["langgraph", "jax", "gpu computing", "research"],

 "strengths_summary": "(LLM-generated paragraph)",
 "gaps_summary": "(LLM-generated paragraph)",

 "upskilling_recommendations": [
  {
   "skill": "C/C++",
   "reason": "...",
   "resource": "Coursera: C++ for C Programmers"
  }
 ],

 "interview_questions": [
  {
   "question": "Walk us through a machine learning project...",
   "category": "technical"
  },
  { "question": "Tell us about a time when...", "category": "behavioral" }
 ],

 "salary_insight": "(LLM-generated sentence)",
 "errors": [
  "Experience estimated from resume entries (2 roles -> ~3 years estimate)"
 ]
}
```

---

## Task 2 Output Contract

Task 2 returns an `ExtractionState` with this JSON structure. This is the input
contract for Task 3.

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
  "resume_skills": ["Python", "Go", "AWS", "Kubernetes", "Docker"],
  "resume_experience": [
   {
    "title": "Senior Software Engineer",
    "company": "TechCorp Inc.",
    "duration": "Mar 2021 - Present",
    "highlights": ["Led microservices migration", "..."]
   }
  ],
  "total_years_experience": 7,
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

| Decision                                      | Rationale                                                                                                                               |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| OCR as a separate task                        | Isolates file handling from AI logic; easier to debug and test independently                                                            |
| 7-step text cleaner                           | Removes OCR artifacts (smart quotes, zero-width chars, page numbers, broken hyphenation) before LLM processing                          |
| Textract sync + async                         | Images use fast synchronous API; multi-page PDFs automatically fall back to async with polling                                          |
| LangGraph parallel fan-out                    | JD and resume extraction are independent reads — parallel execution halves latency                                                      |
| Pydantic as the schema source                 | One model drives the prompt, validates the response, and types downstream code                                                          |
| Bedrock client with dependency injection      | Every service accepts an optional mock client; the full test suite runs without AWS credentials                                         |
| Errors accumulate, never crash                | All pipeline layers append to a shared error list; partial results are still usable                                                     |
| Prompts separated from logic                  | Prompt templates live in their own module so you can iterate on wording without touching node code                                      |
| Temperature 0.0 for extraction                | Deterministic output for structured JSON — no creativity needed in Task 2                                                               |
| 5-layer comparison pipeline                   | Layers stop as soon as a match is found — exact/alias first (free), ontology next (cheap), semantic embeddings last (expensive)         |
| sentence-transformers for semantic similarity | Local inference, no API cost, no rate limits; all-MiniLM-L6-v2 is fast on CPU and accurate enough for skill matching                    |
| Temperature 0.3 for LLM insights              | Slightly creative for varied, personalized career advice — more expressive than extraction's 0.0                                        |
| Education match via keyword intersection      | Extracts 4+ letter words from both degree strings and checks for overlap — tolerant of phrasing differences without needing an LLM call |
| Experience fallback estimation                | When Bedrock can't parse years from dates, estimates conservatively from number of roles (0→0yr, 1→1yr, 2+→3yr) and notes it in errors  |

"""
Prompt templates for the extraction pipeline.

Each prompt is designed to produce strict JSON matching the Pydantic
models in extraction_pipeline.models. The prompts include the target
JSON schema so the LLM knows exactly what structure to return.
"""

from extraction_pipeline.models import JobRequirements, CandidateProfile


def _schema_to_prompt_block(model_class) -> str:
    """Convert a Pydantic model's JSON schema into a readable prompt block."""
    schema = model_class.model_json_schema()
    lines = []
    properties = schema.get("properties", {})
    for field_name, field_info in properties.items():
        field_type = field_info.get("type", "string")
        description = field_info.get("description", "")
        lines.append(f'  "{field_name}": ({field_type}) {description}')
    return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Job Description Extraction Prompt
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

JOB_EXTRACTION_SYSTEM = """You are a precise job description parser. Your task is to extract structured data from a job posting.

RULES:
1. Return ONLY valid JSON — no markdown, no commentary, no backticks.
2. Normalize all skill names to their standard short form (e.g., "JavaScript" not "JS/JavaScript", "Python" not "python programming language").
3. Separate required vs preferred skills carefully. If a section says "nice to have" or "preferred" or "bonus", those skills go in preferred_skills.
4. For years_experience_required, extract only the minimum number. If the JD says "5-7 years", return 5. If it says "3+ years", return 3. If not stated, return null.
5. tools_and_technologies should include specific product names (AWS S3, Jenkins, Docker) while skills can be broader (cloud computing, CI/CD, containerization).
6. If a field cannot be determined from the text, use the appropriate empty value (empty string, empty list, or null).
7. Do NOT invent or infer information not present in the text.

TARGET JSON SCHEMA:
{schema}"""

JOB_EXTRACTION_USER = """Extract structured job requirements from this job description:

<job_description>
{job_description_text}
</job_description>

Return the JSON object now."""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Resume Extraction Prompt
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESUME_EXTRACTION_SYSTEM = """You are a precise resume parser. Your task is to extract structured candidate information from a resume.

RULES:
1. Return ONLY valid JSON — no markdown, no commentary, no backticks.
2. Normalize all skill names to their standard short form (e.g., "Python" not "python 3.x", "React" not "React.js/ReactJS").
3. Extract skills from ALL sections — skills section, experience bullet points, project descriptions, summary, certifications, etc.
4. For total_years_experience, calculate from the earliest start date to the most recent end date (or present). If impossible to determine, return null.
5. resume_experience_summary should be a concise 2-3 sentence synthesis of the candidate's career, not a copy of their summary section.
6. List work experience in reverse chronological order (most recent first).
7. Each project should capture the project name, a brief description, and technologies used.
8. If a field cannot be determined from the text, use the appropriate empty value.
9. Do NOT invent or infer information not present in the text.

TARGET JSON SCHEMA:
{schema}

NESTED SCHEMAS:

ResumeExperience:
  "title": (string) Job title held
  "company": (string) Company name
  "duration": (string) Employment period
  "highlights": (array of strings) Key accomplishments

ResumeProject:
  "name": (string) Project name
  "description": (string) Brief description
  "technologies": (array of strings) Technologies used"""

RESUME_EXTRACTION_USER = """Extract structured candidate information from this resume:

<resume>
{resume_text}
</resume>

Return the JSON object now."""


def get_job_extraction_messages(job_description_text: str) -> list[dict]:
    """Build the message list for job description extraction."""
    schema_block = _schema_to_prompt_block(JobRequirements)
    return [
        {
            "role": "system",
            "content": JOB_EXTRACTION_SYSTEM.format(schema=schema_block),
        },
        {
            "role": "user",
            "content": JOB_EXTRACTION_USER.format(
                job_description_text=job_description_text
            ),
        },
    ]


def get_resume_extraction_messages(resume_text: str) -> list[dict]:
    """Build the message list for resume extraction."""
    schema_block = _schema_to_prompt_block(CandidateProfile)
    return [
        {
            "role": "system",
            "content": RESUME_EXTRACTION_SYSTEM.format(schema=schema_block),
        },
        {
            "role": "user",
            "content": RESUME_EXTRACTION_USER.format(resume_text=resume_text),
        },
    ]
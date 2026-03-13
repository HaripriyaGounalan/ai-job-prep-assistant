"""
Prompt templates for extracting structured information from job descriptions and resumes.
Designed for use with LLMs to generate JSON outputs matching the defined schemas."""

from .schemas import JOB_SCHEMA, RESUME_SCHEMA

def build_job_extraction_prompt(job_text: str) -> str:
    return f"""
You are an information extraction system.

Extract structured information from the following job description.

Return valid JSON only.
Do not include markdown.
Do not include explanations.
Do not include extra text before or after JSON.

If a field is missing:
- return "" for string fields
- return [] for list fields

Rules:
- Extract only information supported by the text.
- Do not invent missing details.
- Keep list items concise.
- Put technical skills into required_skills or preferred_skills.
- Put tools, frameworks, languages, libraries, and platforms into tools_and_technologies.
- Put teamwork, communication, leadership, ownership, accountability, etc. into soft_skills.
- Put domain context like banking, healthcare, AI, e-commerce, analytics, etc. into domain_knowledge.
- job_description_summary should be 2 to 4 sentences.

Return JSON with exactly this schema:
{JOB_SCHEMA}

Job Description:
{job_text}
"""

def build_resume_extraction_prompt(resume_text: str) -> str:
    return f"""
You are an information extraction system.

Extract structured information from the following resume.

Return valid JSON only.
Do not include markdown.
Do not include explanations.
Do not include extra text before or after JSON.

If a field is missing:
- return "" for string fields
- return [] for list fields
- keep nested objects present with empty values

Rules:
- Extract only information supported by the text.
- Do not invent information.
- Keep list items concise.
- Put technical skills in resume_skills.
- Put tools, frameworks, IDEs, libraries, platforms, and software in tools_and_technologies.
- work_experience must be a list of objects like:
  {{
    "organization": "",
    "role": "",
    "duration": "",
    "responsibilities": [],
    "technologies_used": []
  }}
- projects must be a list of objects like:
  {{
    "name": "",
    "role": "",
    "duration": "",
    "description": "",
    "technologies_used": []
  }}
- resume_experience_summary should be 2 to 4 sentences.

Return JSON with exactly this schema:
{RESUME_SCHEMA}

Resume Text:
{resume_text}
"""
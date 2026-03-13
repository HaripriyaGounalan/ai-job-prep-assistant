import json
import re
from ..ocr.text_cleaner import clean_text
from .prompts import (
    build_job_extraction_prompt,
    build_resume_extraction_prompt,
)
from .bedrock_service import BedrockService

bedrock = BedrockService()


def _parse_json(raw: str) -> dict:
    """Strip markdown fences then parse JSON."""
    # Remove ```json ... ``` or ``` ... ``` wrappers
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    return json.loads(cleaned.strip())


def extract_job_data(job_text: str) -> dict:
    cleaned = clean_text(job_text)
    prompt = build_job_extraction_prompt(cleaned)
    raw_output = bedrock.call_llm(prompt)
    return _parse_json(raw_output)


def extract_resume_data(resume_text: str) -> dict:
    cleaned = clean_text(resume_text)
    prompt = build_resume_extraction_prompt(cleaned)
    raw_output = bedrock.call_llm(prompt)
    return _parse_json(raw_output)

def extract_all(resume_text: str, job_text: str) -> dict:
    return {
        "job_requirements": extract_job_data(job_text),
        "candidate_profile": extract_resume_data(resume_text),
    }
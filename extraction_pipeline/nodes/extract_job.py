"""
LangGraph node: extract structured requirements from a job description.

This node reads job_description_text from the graph state, calls the
LLM with the JD extraction prompt, validates the response against the
JobRequirements Pydantic model, and writes the result back to state.
"""

import logging
from typing import Any

from extraction_pipeline.models import JobRequirements, ExtractionState
from extraction_pipeline.prompts import get_job_extraction_messages
from extraction_pipeline.llm_client import BedrockClient, BedrockLLMError

logger = logging.getLogger(__name__)


def extract_job_requirements(
    state: dict[str, Any],
    llm_client: BedrockClient | None = None,
) -> dict[str, Any]:
    """
    LangGraph node function: extract job requirements.

    Args:
        state: Current graph state dict. Must contain 'job_description_text'.
        llm_client: Optional injected client (for testing).

    Returns:
        State update dict with 'job_requirements' (or error in 'errors').
    """
    jd_text = state.get("job_description_text", "")

    if not jd_text.strip():
        logger.warning("No job description text provided")
        return {
            "errors": state.get("errors", []) + [
                "Job description text is empty — skipping JD extraction"
            ],
        }

    client = llm_client or BedrockClient()

    try:
        messages = get_job_extraction_messages(jd_text)
        raw_json = client.invoke_for_json(messages)

        # Validate against Pydantic model
        job_req = JobRequirements.model_validate(raw_json)

        logger.info(
            "Extracted JD: title=%s, %d required skills, %d preferred skills",
            job_req.job_title,
            len(job_req.required_skills),
            len(job_req.preferred_skills),
        )

        return {"job_requirements": job_req}

    except BedrockLLMError as e:
        error_msg = f"LLM extraction failed for job description: {e}"
        logger.error(error_msg)
        return {"errors": state.get("errors", []) + [error_msg]}

    except Exception as e:
        error_msg = f"Validation failed for JD extraction: {e}"
        logger.error(error_msg)
        return {"errors": state.get("errors", []) + [error_msg]}
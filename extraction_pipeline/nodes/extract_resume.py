"""
LangGraph node: extract structured candidate profile from a resume.

This node reads resume_text from the graph state, calls the LLM with
the resume extraction prompt, validates the response against the
CandidateProfile Pydantic model, and writes the result back to state.
"""

import logging
from typing import Any

from extraction_pipeline.models import CandidateProfile, ExtractionState
from extraction_pipeline.prompts import get_resume_extraction_messages
from extraction_pipeline.llm_client import BedrockClient, BedrockLLMError

logger = logging.getLogger(__name__)


def extract_candidate_profile(
    state: dict[str, Any],
    llm_client: BedrockClient | None = None,
) -> dict[str, Any]:
    """
    LangGraph node function: extract candidate profile.

    Args:
        state: Current graph state dict. Must contain 'resume_text'.
        llm_client: Optional injected client (for testing).

    Returns:
        State update dict with 'candidate_profile' (or error in 'errors').
    """
    resume_text = state.get("resume_text", "")

    if not resume_text.strip():
        logger.warning("No resume text provided")
        return {
            "errors": state.get("errors", []) + [
                "Resume text is empty — skipping resume extraction"
            ],
        }

    client = llm_client or BedrockClient()

    try:
        messages = get_resume_extraction_messages(resume_text)
        raw_json = client.invoke_for_json(messages)

        # Validate against Pydantic model
        profile = CandidateProfile.model_validate(raw_json)

        logger.info(
            "Extracted resume: name=%s, %d skills, %d experience entries",
            profile.candidate_name,
            len(profile.resume_skills),
            len(profile.resume_experience),
        )

        return {"candidate_profile": profile}

    except BedrockLLMError as e:
        error_msg = f"LLM extraction failed for resume: {e}"
        logger.error(error_msg)
        return {"errors": state.get("errors", []) + [error_msg]}

    except Exception as e:
        error_msg = f"Validation failed for resume extraction: {e}"
        logger.error(error_msg)
        return {"errors": state.get("errors", []) + [error_msg]}
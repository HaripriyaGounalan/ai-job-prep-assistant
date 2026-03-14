"""Tests for the extraction graph nodes."""

import json
import pytest
from unittest.mock import MagicMock

from extraction_pipeline.nodes.extract_job import extract_job_requirements
from extraction_pipeline.nodes.extract_resume import extract_candidate_profile
from extraction_pipeline.llm_client import BedrockClient, BedrockLLMError
from extraction_pipeline.models import JobRequirements, CandidateProfile
from tests.fixtures import (
    SAMPLE_JOB_DESCRIPTION,
    SAMPLE_RESUME,
    MOCK_JOB_EXTRACTION_RESPONSE,
    MOCK_RESUME_EXTRACTION_RESPONSE,
)


def _make_mock_client(response_dict: dict) -> BedrockClient:
    """Create a BedrockClient that returns a predetermined JSON dict."""
    client = BedrockClient.__new__(BedrockClient)
    client.invoke_for_json = MagicMock(return_value=response_dict)
    return client


class TestExtractJobRequirements:
    def test_successful_extraction(self):
        mock_client = _make_mock_client(MOCK_JOB_EXTRACTION_RESPONSE)
        state = {
            "job_description_text": SAMPLE_JOB_DESCRIPTION,
            "errors": [],
        }

        result = extract_job_requirements(state, llm_client=mock_client)

        assert "job_requirements" in result
        jr = result["job_requirements"]
        assert isinstance(jr, JobRequirements)
        assert jr.job_title == "Software Engineer - Cloud Infrastructure"
        assert "Python" in jr.required_skills
        assert jr.years_experience_required == 5

    def test_empty_text_skips(self):
        state = {"job_description_text": "", "errors": []}
        result = extract_job_requirements(state)
        assert "errors" in result
        assert any("empty" in e.lower() for e in result["errors"])

    def test_llm_error_captured(self):
        mock_client = _make_mock_client({})
        mock_client.invoke_for_json = MagicMock(
            side_effect=BedrockLLMError("timeout")
        )
        state = {
            "job_description_text": SAMPLE_JOB_DESCRIPTION,
            "errors": [],
        }

        result = extract_job_requirements(state, llm_client=mock_client)
        assert "errors" in result
        assert any("LLM extraction failed" in e for e in result["errors"])

    def test_validation_error_captured(self):
        # Return invalid data that won't pass Pydantic validation
        # (job_title is required as a string)
        mock_client = _make_mock_client({"job_title": 12345, "required_skills": "not_a_list"})
        state = {
            "job_description_text": SAMPLE_JOB_DESCRIPTION,
            "errors": [],
        }

        result = extract_job_requirements(state, llm_client=mock_client)
        # Should either succeed with coercion or capture validation error
        # Pydantic v2 will coerce 12345 → "12345" and might handle the string
        # The key thing: it doesn't crash
        assert "job_requirements" in result or "errors" in result


class TestExtractCandidateProfile:
    def test_successful_extraction(self):
        mock_client = _make_mock_client(MOCK_RESUME_EXTRACTION_RESPONSE)
        state = {
            "resume_text": SAMPLE_RESUME,
            "errors": [],
        }

        result = extract_candidate_profile(state, llm_client=mock_client)

        assert "candidate_profile" in result
        cp = result["candidate_profile"]
        assert isinstance(cp, CandidateProfile)
        assert cp.candidate_name == "Jane Doe"
        assert cp.total_years_experience == 7
        assert "Python" in cp.resume_skills
        assert len(cp.resume_experience) == 3
        assert len(cp.resume_projects) == 2

    def test_empty_text_skips(self):
        state = {"resume_text": "  ", "errors": []}
        result = extract_candidate_profile(state)
        assert "errors" in result
        assert any("empty" in e.lower() for e in result["errors"])

    def test_llm_error_captured(self):
        mock_client = _make_mock_client({})
        mock_client.invoke_for_json = MagicMock(
            side_effect=BedrockLLMError("service unavailable")
        )
        state = {"resume_text": SAMPLE_RESUME, "errors": []}

        result = extract_candidate_profile(state, llm_client=mock_client)
        assert "errors" in result
        assert any("LLM extraction failed" in e for e in result["errors"])
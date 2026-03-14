"""Integration tests for the LangGraph extraction graph."""

import json
import pytest
from unittest.mock import MagicMock, call

from extraction_pipeline.graph import (
    build_extraction_graph,
    run_extraction,
    GraphState,
)
from extraction_pipeline.models import (
    JobRequirements,
    CandidateProfile,
    ExtractionState,
)
from extraction_pipeline.llm_client import BedrockClient, BedrockLLMError
from tests.fixtures import (
    SAMPLE_JOB_DESCRIPTION,
    SAMPLE_RESUME,
    MOCK_JOB_EXTRACTION_RESPONSE,
    MOCK_RESUME_EXTRACTION_RESPONSE,
)


def _make_mock_client_for_graph() -> BedrockClient:
    """
    Create a mock client that returns different responses based on
    which prompt it receives (JD vs resume).
    """
    client = BedrockClient.__new__(BedrockClient)

    def side_effect(messages, model_id=None):
        # Detect which extraction this is by checking the user message
        user_msg = next(
            (m["content"] for m in messages if m["role"] == "user"), ""
        )
        if "<job_description>" in user_msg:
            return MOCK_JOB_EXTRACTION_RESPONSE
        elif "<resume>" in user_msg:
            return MOCK_RESUME_EXTRACTION_RESPONSE
        else:
            raise BedrockLLMError("Unknown extraction type")

    client.invoke_for_json = MagicMock(side_effect=side_effect)
    return client


class TestBuildExtractionGraph:
    def test_graph_compiles(self):
        mock_client = _make_mock_client_for_graph()
        graph = build_extraction_graph(mock_client)
        assert graph is not None

    def test_graph_invocation(self):
        mock_client = _make_mock_client_for_graph()
        graph = build_extraction_graph(mock_client)

        result = graph.invoke({
            "resume_text": SAMPLE_RESUME,
            "job_description_text": SAMPLE_JOB_DESCRIPTION,
            "errors": [],
            "status": "running",
        })

        assert result["status"] == "completed"
        assert result["job_requirements"] is not None
        assert result["candidate_profile"] is not None
        assert result["errors"] == []

    def test_graph_jd_data(self):
        mock_client = _make_mock_client_for_graph()
        graph = build_extraction_graph(mock_client)

        result = graph.invoke({
            "resume_text": SAMPLE_RESUME,
            "job_description_text": SAMPLE_JOB_DESCRIPTION,
            "errors": [],
            "status": "running",
        })

        jr = result["job_requirements"]
        assert jr.job_title == "Software Engineer - Cloud Infrastructure"
        assert "Python" in jr.required_skills
        assert jr.years_experience_required == 5

    def test_graph_resume_data(self):
        mock_client = _make_mock_client_for_graph()
        graph = build_extraction_graph(mock_client)

        result = graph.invoke({
            "resume_text": SAMPLE_RESUME,
            "job_description_text": SAMPLE_JOB_DESCRIPTION,
            "errors": [],
            "status": "running",
        })

        cp = result["candidate_profile"]
        assert cp.candidate_name == "Jane Doe"
        assert cp.total_years_experience == 7
        assert len(cp.resume_skills) == 19


class TestRunExtraction:
    def test_full_extraction(self):
        mock_client = _make_mock_client_for_graph()

        result = run_extraction(
            resume_text=SAMPLE_RESUME,
            job_description_text=SAMPLE_JOB_DESCRIPTION,
            llm_client=mock_client,
        )

        assert isinstance(result, ExtractionState)
        assert result.status == "completed"
        assert result.job_requirements is not None
        assert result.candidate_profile is not None
        assert result.errors == []

    def test_extraction_result_serializable(self):
        mock_client = _make_mock_client_for_graph()

        result = run_extraction(
            resume_text=SAMPLE_RESUME,
            job_description_text=SAMPLE_JOB_DESCRIPTION,
            llm_client=mock_client,
        )

        # Must be fully JSON-serializable
        json_str = result.model_dump_json(indent=2)
        parsed = json.loads(json_str)

        assert parsed["status"] == "completed"
        assert parsed["job_requirements"]["job_title"] == "Software Engineer - Cloud Infrastructure"
        assert parsed["candidate_profile"]["candidate_name"] == "Jane Doe"
        assert len(parsed["candidate_profile"]["resume_skills"]) == 19

    def test_empty_resume_partial(self):
        mock_client = _make_mock_client_for_graph()

        result = run_extraction(
            resume_text="",
            job_description_text=SAMPLE_JOB_DESCRIPTION,
            llm_client=mock_client,
        )

        assert result.status == "partial"
        assert result.job_requirements is not None
        assert result.candidate_profile is None
        assert len(result.errors) > 0

    def test_empty_jd_partial(self):
        mock_client = _make_mock_client_for_graph()

        result = run_extraction(
            resume_text=SAMPLE_RESUME,
            job_description_text="",
            llm_client=mock_client,
        )

        assert result.status == "partial"
        assert result.job_requirements is None
        assert result.candidate_profile is not None

    def test_both_empty_failed(self):
        mock_client = _make_mock_client_for_graph()

        result = run_extraction(
            resume_text="",
            job_description_text="",
            llm_client=mock_client,
        )

        assert result.status == "failed"
        assert result.job_requirements is None
        assert result.candidate_profile is None
        assert len(result.errors) == 2

    def test_llm_failure_graceful(self):
        """If the LLM fails entirely, the pipeline should still return."""
        client = BedrockClient.__new__(BedrockClient)
        client.invoke_for_json = MagicMock(
            side_effect=BedrockLLMError("service down")
        )

        result = run_extraction(
            resume_text=SAMPLE_RESUME,
            job_description_text=SAMPLE_JOB_DESCRIPTION,
            llm_client=client,
        )

        assert result.status == "failed"
        assert len(result.errors) == 2
        assert all("LLM extraction failed" in e for e in result.errors)

    def test_output_keys_match_task3_contract(self):
        """Verify the output structure is what Task 3 expects."""
        mock_client = _make_mock_client_for_graph()

        result = run_extraction(
            resume_text=SAMPLE_RESUME,
            job_description_text=SAMPLE_JOB_DESCRIPTION,
            llm_client=mock_client,
        )

        output = result.model_dump()

        # Task 3 expects these top-level keys
        assert "job_requirements" in output
        assert "candidate_profile" in output

        # Task 3 comparison needs these specific fields
        jr = output["job_requirements"]
        assert "required_skills" in jr
        assert "preferred_skills" in jr
        assert "years_experience_required" in jr
        assert "tools_and_technologies" in jr

        cp = output["candidate_profile"]
        assert "resume_skills" in cp
        assert "resume_projects" in cp
        assert "resume_experience_summary" in cp
        assert "total_years_experience" in cp
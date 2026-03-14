"""Tests for extraction prompt templates."""

import pytest
from extraction_pipeline.prompts.extraction_prompts import (
    get_job_extraction_messages,
    get_resume_extraction_messages,
    _schema_to_prompt_block,
)
from extraction_pipeline.models import JobRequirements, CandidateProfile


class TestPromptGeneration:
    def test_job_messages_structure(self):
        messages = get_job_extraction_messages("Some JD text here")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_job_system_contains_schema(self):
        messages = get_job_extraction_messages("JD text")
        system = messages[0]["content"]
        # Should contain field names from JobRequirements
        assert "required_skills" in system
        assert "preferred_skills" in system
        assert "years_experience_required" in system
        assert "tools_and_technologies" in system

    def test_job_user_contains_text(self):
        messages = get_job_extraction_messages("We need a Python expert")
        user = messages[1]["content"]
        assert "We need a Python expert" in user
        assert "<job_description>" in user

    def test_resume_messages_structure(self):
        messages = get_resume_extraction_messages("Some resume text")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_resume_system_contains_schema(self):
        messages = get_resume_extraction_messages("Resume text")
        system = messages[0]["content"]
        assert "resume_skills" in system
        assert "resume_projects" in system
        assert "resume_experience_summary" in system
        assert "total_years_experience" in system

    def test_resume_user_contains_text(self):
        messages = get_resume_extraction_messages("Jane Doe, 7 years exp")
        user = messages[1]["content"]
        assert "Jane Doe, 7 years exp" in user
        assert "<resume>" in user

    def test_prompts_instruct_json_only(self):
        jd_msgs = get_job_extraction_messages("x")
        resume_msgs = get_resume_extraction_messages("x")
        for msgs in [jd_msgs, resume_msgs]:
            system = msgs[0]["content"]
            assert "ONLY valid JSON" in system

    def test_schema_block_generation(self):
        block = _schema_to_prompt_block(JobRequirements)
        assert "job_title" in block
        assert "required_skills" in block
        assert "salary_range" in block
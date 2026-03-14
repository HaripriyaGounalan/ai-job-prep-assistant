"""Tests for extraction pipeline data models."""

import pytest
from pydantic import ValidationError

from extraction_pipeline.models import (
    JobRequirements,
    CandidateProfile,
    ResumeExperience,
    ResumeProject,
    ExtractionState,
)
from tests.fixtures import (
    MOCK_JOB_EXTRACTION_RESPONSE,
    MOCK_RESUME_EXTRACTION_RESPONSE,
)


class TestJobRequirements:
    def test_parse_full_response(self):
        jr = JobRequirements.model_validate(MOCK_JOB_EXTRACTION_RESPONSE)
        assert jr.job_title == "Software Engineer - Cloud Infrastructure"
        assert jr.company_name == "Acme Corp"
        assert jr.years_experience_required == 5
        assert "Python" in jr.required_skills
        assert "Terraform" in jr.preferred_skills
        assert "AWS EC2" in jr.tools_and_technologies
        assert jr.employment_type == "Full-time"

    def test_minimal_valid(self):
        jr = JobRequirements(job_title="Engineer")
        assert jr.job_title == "Engineer"
        assert jr.required_skills == []
        assert jr.years_experience_required is None

    def test_serialization_roundtrip(self):
        jr = JobRequirements.model_validate(MOCK_JOB_EXTRACTION_RESPONSE)
        as_dict = jr.model_dump()
        jr2 = JobRequirements.model_validate(as_dict)
        assert jr == jr2


class TestCandidateProfile:
    def test_parse_full_response(self):
        cp = CandidateProfile.model_validate(MOCK_RESUME_EXTRACTION_RESPONSE)
        assert cp.candidate_name == "Jane Doe"
        assert cp.total_years_experience == 7
        assert len(cp.resume_skills) == 19
        assert len(cp.resume_experience) == 3
        assert len(cp.resume_projects) == 2
        assert "AWS Solutions Architect" in cp.certifications[0]

    def test_experience_entries(self):
        cp = CandidateProfile.model_validate(MOCK_RESUME_EXTRACTION_RESPONSE)
        senior = cp.resume_experience[0]
        assert senior.title == "Senior Software Engineer"
        assert senior.company == "TechCorp Inc."
        assert len(senior.highlights) == 4

    def test_projects(self):
        cp = CandidateProfile.model_validate(MOCK_RESUME_EXTRACTION_RESPONSE)
        project = cp.resume_projects[0]
        assert project.name == "Cloud Cost Optimizer"
        assert "Python" in project.technologies

    def test_minimal_valid(self):
        cp = CandidateProfile()
        assert cp.candidate_name == ""
        assert cp.resume_skills == []

    def test_serialization_roundtrip(self):
        cp = CandidateProfile.model_validate(MOCK_RESUME_EXTRACTION_RESPONSE)
        as_dict = cp.model_dump()
        cp2 = CandidateProfile.model_validate(as_dict)
        assert cp == cp2


class TestExtractionState:
    def test_initial_state(self):
        state = ExtractionState(
            resume_text="text",
            job_description_text="jd text",
        )
        assert state.status == "pending"
        assert state.job_requirements is None
        assert state.candidate_profile is None
        assert state.errors == []

    def test_completed_state(self):
        jr = JobRequirements.model_validate(MOCK_JOB_EXTRACTION_RESPONSE)
        cp = CandidateProfile.model_validate(MOCK_RESUME_EXTRACTION_RESPONSE)
        state = ExtractionState(
            resume_text="x",
            job_description_text="y",
            job_requirements=jr,
            candidate_profile=cp,
            status="completed",
        )
        assert state.status == "completed"
        assert state.job_requirements.job_title == "Software Engineer - Cloud Infrastructure"
        assert state.candidate_profile.candidate_name == "Jane Doe"

    def test_json_serialization(self):
        jr = JobRequirements.model_validate(MOCK_JOB_EXTRACTION_RESPONSE)
        cp = CandidateProfile.model_validate(MOCK_RESUME_EXTRACTION_RESPONSE)
        state = ExtractionState(
            resume_text="x",
            job_description_text="y",
            job_requirements=jr,
            candidate_profile=cp,
            status="completed",
        )
        json_str = state.model_dump_json()
        restored = ExtractionState.model_validate_json(json_str)
        assert restored.job_requirements.required_skills == jr.required_skills
        assert restored.candidate_profile.resume_skills == cp.resume_skills
"""End-to-end tests for the comparison pipeline (Task 3)."""

import json
import pytest
from unittest.mock import MagicMock

from comparison_pipeline.run_comparison import run_comparison
from comparison_pipeline.models import ComparisonResult, SkillMatch
from extraction_pipeline.models import (
    ExtractionState,
    JobRequirements,
    CandidateProfile,
    ResumeExperience,
)
from extraction_pipeline.llm_client import BedrockClient, BedrockLLMError


MOCK_LLM_RESPONSE = {
    "strengths_summary": "Strong Python and ML background.",
    "gaps_summary": "Missing C and C++ experience.",
    "upskilling_recommendations": [
        {
            "skill": "C++",
            "reason": "Required for systems-level work",
            "resource": "Coursera: C++ Specialization",
        },
    ],
    "interview_questions": [
        {"question": "Explain backpropagation.", "category": "technical"},
        {"question": "Describe a time you led a project.", "category": "behavioral"},
        {"question": "Design a real-time ML pipeline.", "category": "technical"},
        {"question": "How would you handle model drift?", "category": "situational"},
        {"question": "What is your debugging process?", "category": "technical"},
    ],
    "salary_insight": "Competitive for the experience level.",
}


def _make_mock_client(response_dict: dict) -> BedrockClient:
    client = BedrockClient.__new__(BedrockClient)
    client.invoke_for_json = MagicMock(return_value=response_dict)
    client.temperature = 0.0
    return client


def _make_extraction_state(
    required_skills=None,
    preferred_skills=None,
    resume_skills=None,
    years_required=3,
    years_candidate=None,
    experience_count=2,
) -> ExtractionState:
    experiences = [
        ResumeExperience(title=f"Role {i}", company=f"Co {i}", duration="2020-2022")
        for i in range(experience_count)
    ]

    return ExtractionState(
        resume_text="sample resume",
        job_description_text="sample jd",
        job_requirements=JobRequirements(
            job_title="ML Engineer",
            company_name="TD",
            required_skills=required_skills if required_skills is not None else ["Python", "Java", "C", "C++", "Machine Learning", "Deep Learning"],
            preferred_skills=preferred_skills if preferred_skills is not None else ["LangGraph", "PyTorch", "TensorFlow"],
            years_experience_required=years_required,
            education_requirements=["Bachelor's degree in Computer Science"],
            key_responsibilities=["Build ML systems", "Write clean code"],
            salary_range="$120,000 - $250,000 CAD",
        ),
        candidate_profile=CandidateProfile(
            candidate_name="John Doe",
            resume_skills=resume_skills if resume_skills is not None else [
                "Python", "Java", "TensorFlow", "Keras",
                "Neural Networks", "Scikit-learn", "React", "SQL",
            ],
            resume_experience=experiences,
            total_years_experience=years_candidate,
            education=["Bachelor of Technology - Information Technology, SMVEC, 2016"],
        ),
        status="completed",
    )


class TestFullComparison:
    def test_end_to_end(self):
        mock_client = _make_mock_client(MOCK_LLM_RESPONSE)
        state = _make_extraction_state()

        result = run_comparison(state, bedrock_client=mock_client)

        assert isinstance(result, ComparisonResult)
        assert result.overall_score > 0
        assert result.skill_score > 0
        assert len(result.required_skill_matches) == 6
        assert len(result.preferred_skill_matches) == 3
        assert result.strengths_summary != ""
        assert len(result.interview_questions) == 5

    def test_output_serializable(self):
        mock_client = _make_mock_client(MOCK_LLM_RESPONSE)
        state = _make_extraction_state()

        result = run_comparison(state, bedrock_client=mock_client)

        json_str = result.model_dump_json(indent=2)
        parsed = json.loads(json_str)

        assert "overall_score" in parsed
        assert "required_skill_matches" in parsed
        assert "interview_questions" in parsed
        assert "errors" in parsed

    def test_output_contract_keys(self):
        mock_client = _make_mock_client(MOCK_LLM_RESPONSE)
        state = _make_extraction_state()

        result = run_comparison(state, bedrock_client=mock_client)
        output = result.model_dump()

        expected_keys = {
            "overall_score", "skill_score", "experience_score",
            "education_matched", "required_skill_matches",
            "preferred_skill_matches", "missing_required_skills",
            "missing_preferred_skills", "strengths_summary",
            "gaps_summary", "upskilling_recommendations",
            "interview_questions", "salary_insight", "errors",
        }
        assert set(output.keys()) == expected_keys


class TestEdgeCases:
    def test_empty_required_skills(self):
        mock_client = _make_mock_client(MOCK_LLM_RESPONSE)
        state = _make_extraction_state(required_skills=[])

        result = run_comparison(state, bedrock_client=mock_client)

        assert result.skill_score == 0.0
        assert any("No required skills" in e for e in result.errors)

    def test_empty_resume_skills(self):
        mock_client = _make_mock_client(MOCK_LLM_RESPONSE)
        state = _make_extraction_state(resume_skills=[])

        result = run_comparison(state, bedrock_client=mock_client)

        assert all(m.score == 0.0 for m in result.required_skill_matches)

    def test_llm_failure_partial_result(self):
        client = BedrockClient.__new__(BedrockClient)
        client.invoke_for_json = MagicMock(
            side_effect=BedrockLLMError("timeout")
        )
        state = _make_extraction_state()

        result = run_comparison(state, bedrock_client=client)

        assert result.skill_score > 0
        assert result.overall_score > 0
        assert result.strengths_summary == ""
        assert any("LLM insight generation failed" in e for e in result.errors)

    def test_none_job_requirements(self):
        state = ExtractionState(
            resume_text="x", job_description_text="y",
            job_requirements=None,
            candidate_profile=CandidateProfile(candidate_name="Test"),
            status="partial",
        )
        result = run_comparison(state)

        assert result.overall_score == 0.0
        assert any("No job requirements" in e for e in result.errors)

    def test_none_candidate_profile(self):
        state = ExtractionState(
            resume_text="x", job_description_text="y",
            job_requirements=JobRequirements(job_title="SWE"),
            candidate_profile=None,
            status="partial",
        )
        result = run_comparison(state)

        assert result.overall_score == 0.0
        assert any("No candidate profile" in e for e in result.errors)

    def test_experience_fallback_noted_in_errors(self):
        mock_client = _make_mock_client(MOCK_LLM_RESPONSE)
        state = _make_extraction_state(years_candidate=None, experience_count=2)

        result = run_comparison(state, bedrock_client=mock_client)

        assert result.experience_score is not None
        assert any("Experience estimated" in e for e in result.errors)

    def test_with_real_world_fixture(self):
        """Test with data modeled on the actual result.json from Task 2."""
        mock_client = _make_mock_client(MOCK_LLM_RESPONSE)
        state = _make_extraction_state(
            required_skills=["Python", "Java", "C", "C++", "Machine Learning", "Deep Learning"],
            preferred_skills=["LangGraph", "PyTorch", "TensorFlow", "JAX", "GPU Computing", "Research"],
            resume_skills=[
                "Java", "Python", "Node.js", "C#", "Flask", "React", "Redux",
                "Angular", "JavaScript", "MySQL", "PostgreSQL", "MongoDB", "SQL",
                "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "Keras",
                "Machine Learning", "Neural Networks", "Git",
            ],
            years_required=3,
            years_candidate=None,
            experience_count=2,
        )

        result = run_comparison(state, bedrock_client=mock_client)

        assert result.overall_score > 0
        assert "c" in [m.skill for m in result.required_skill_matches]
        assert "c++" in [m.skill for m in result.required_skill_matches]

        python_match = next(m for m in result.required_skill_matches if m.skill == "python")
        assert python_match.match_type == "exact"
        assert python_match.score == 1.0

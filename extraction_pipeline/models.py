"""
Structured data models for the extraction pipeline.

These Pydantic models define the exact JSON schema the LLM must produce.
They serve three purposes:
  1. Prompt the LLM with a clear target structure (via schema generation)
  2. Validate and parse the LLM's JSON response
  3. Provide typed objects for downstream comparison in Task 3
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Job Description Extraction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class JobRequirements(BaseModel):
    """Structured extraction of a job description."""

    job_title: str = Field(
        description="The job title as stated in the posting"
    )
    company_name: str = Field(
        default="",
        description="Company or organization name, empty if not stated",
    )
    location: str = Field(
        default="",
        description="Job location (city/state/remote), empty if not stated",
    )
    required_skills: list[str] = Field(
        default_factory=list,
        description=(
            "Hard skills explicitly required. Each item should be a single, "
            "normalized skill name (e.g. 'Python', 'Kubernetes', 'SQL')."
        ),
    )
    preferred_skills: list[str] = Field(
        default_factory=list,
        description=(
            "Skills listed as preferred, nice-to-have, or bonus. "
            "Same normalization rules as required_skills."
        ),
    )
    years_experience_required: Optional[int] = Field(
        default=None,
        description=(
            "Minimum years of experience required. Integer only. "
            "null if not explicitly stated."
        ),
    )
    education_requirements: list[str] = Field(
        default_factory=list,
        description="Degree or certification requirements (e.g. 'BS Computer Science')",
    )
    tools_and_technologies: list[str] = Field(
        default_factory=list,
        description=(
            "Specific tools, platforms, frameworks, or services mentioned "
            "(e.g. 'AWS Lambda', 'Terraform', 'Jenkins'). May overlap with "
            "required_skills — that is expected."
        ),
    )
    key_responsibilities: list[str] = Field(
        default_factory=list,
        description="Main responsibilities or duties listed in the JD",
    )
    employment_type: str = Field(
        default="",
        description="Full-time, part-time, contract, etc. Empty if not stated.",
    )
    salary_range: str = Field(
        default="",
        description="Salary or compensation info if mentioned, empty otherwise",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Resume Extraction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ResumeProject(BaseModel):
    """A single project from the resume."""
    name: str = Field(description="Project name or title")
    description: str = Field(
        default="",
        description="Brief description of the project",
    )
    technologies: list[str] = Field(
        default_factory=list,
        description="Technologies, tools, or frameworks used in this project",
    )


class ResumeExperience(BaseModel):
    """A single work experience entry."""
    title: str = Field(description="Job title held")
    company: str = Field(default="", description="Company or employer name")
    duration: str = Field(
        default="",
        description="Employment period (e.g. 'Jan 2020 - Mar 2023')",
    )
    highlights: list[str] = Field(
        default_factory=list,
        description="Key accomplishments or responsibilities in this role",
    )


class CandidateProfile(BaseModel):
    """Structured extraction of a resume."""

    candidate_name: str = Field(
        default="",
        description="Full name of the candidate",
    )
    contact_info: str = Field(
        default="",
        description="Email, phone, or LinkedIn — combined into a single string",
    )
    resume_skills: list[str] = Field(
        default_factory=list,
        description=(
            "All technical and professional skills found anywhere in the "
            "resume. Normalize to short canonical names "
            "(e.g. 'Python', 'Project Management', 'AWS')."
        ),
    )
    resume_experience: list[ResumeExperience] = Field(
        default_factory=list,
        description="Work experience entries, most recent first",
    )
    total_years_experience: Optional[int] = Field(
        default=None,
        description=(
            "Estimated total years of professional experience. "
            "null if impossible to determine."
        ),
    )
    resume_experience_summary: str = Field(
        default="",
        description=(
            "A 2-3 sentence summary of the candidate's professional "
            "background, career trajectory, and core strengths."
        ),
    )
    resume_projects: list[ResumeProject] = Field(
        default_factory=list,
        description="Notable projects listed on the resume",
    )
    education: list[str] = Field(
        default_factory=list,
        description="Degrees and certifications (e.g. 'BS Computer Science, MIT 2018')",
    )
    certifications: list[str] = Field(
        default_factory=list,
        description="Professional certifications (e.g. 'AWS Solutions Architect')",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LangGraph State
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ExtractionState(BaseModel):
    """
    Full state that flows through the LangGraph extraction workflow.

    This is the TypedDict-equivalent state object. LangGraph nodes read
    from and write to this state as the graph executes.
    """

    # Inputs (set once at the start)
    resume_text: str = ""
    job_description_text: str = ""

    # Outputs (populated by extraction nodes)
    job_requirements: Optional[JobRequirements] = None
    candidate_profile: Optional[CandidateProfile] = None

    # Metadata
    errors: list[str] = Field(default_factory=list)
    status: str = "pending"
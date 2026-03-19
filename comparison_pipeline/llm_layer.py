"""
LLM insight generation (Layer 5).

Makes a single Bedrock call to produce career advice: strengths,
gaps, upskilling recommendations, interview questions, and salary
context.  Uses temperature 0.3 for more creative recommendations.
"""

import logging
from typing import Optional

from comparison_pipeline.models import LLMInsights
from extraction_pipeline.llm_client import BedrockClient, BedrockLLMError

logger = logging.getLogger(__name__)


COMPARISON_SYSTEM = """You are a career advisor AI. You analyze a candidate's fit for a job and provide actionable advice.

RULES:
1. Return ONLY valid JSON — no markdown, no commentary, no backticks.
2. Be specific and reference actual skills and experiences from the data provided.
3. Strengths should highlight where the candidate exceeds or meets requirements.
4. Gaps should be honest but constructive, focusing on addressable weaknesses.
5. Each upskilling recommendation must include a concrete resource (course name, platform, or book).
6. Generate EXACTLY 5 interview questions: at least 2 technical, at least 1 behavioral, at least 1 situational.
7. Salary insight should relate the posted range to the candidate's experience level.
8. Do NOT invent skills or experiences not present in the data.

TARGET JSON SCHEMA:
{
  "strengths_summary": "(string) 2-3 sentences on candidate strengths relative to this role",
  "gaps_summary": "(string) 2-3 sentences on skill/experience gaps the candidate should address",
  "upskilling_recommendations": [
    {
      "skill": "(string) skill name to learn",
      "reason": "(string) why this skill matters for the role",
      "resource": "(string) specific course, book, or platform"
    }
  ],
  "interview_questions": [
    {
      "question": "(string) the interview question",
      "category": "(string) one of: technical, behavioral, situational"
    }
  ],
  "salary_insight": "(string) 1-2 sentences about salary range vs candidate experience level"
}"""


COMPARISON_USER = """Analyze this candidate's fit for the following role and provide career advice.

<job_info>
Job Title: {job_title}
Company: {company_name}
Required Skills: {required_skills}
Preferred Skills: {preferred_skills}
Key Responsibilities:
{key_responsibilities}
Salary Range: {salary_range}
</job_info>

<candidate_info>
Resume Skills: {resume_skills}
Total Years of Experience: {total_years_experience}
</candidate_info>

<match_analysis>
Overall Match Score: {overall_score}%
Missing Required Skills: {missing_required}
Missing Preferred Skills: {missing_preferred}
</match_analysis>

Provide upskilling recommendations for each missing required skill. Generate exactly 5 interview questions.
Return the JSON object now."""


def build_comparison_messages(
    job_title: str,
    company_name: str,
    required_skills: list[str],
    preferred_skills: list[str],
    key_responsibilities: list[str],
    salary_range: str,
    resume_skills: list[str],
    total_years_experience: Optional[int],
    overall_score: float,
    missing_required: list[str],
    missing_preferred: list[str],
) -> list[dict]:
    """Build the system + user message list for the comparison LLM call.

    Args:
        job_title:              From JobRequirements.
        company_name:           From JobRequirements.
        required_skills:        Original (non-normalized) required skills.
        preferred_skills:       Original (non-normalized) preferred skills.
        key_responsibilities:   From JobRequirements.
        salary_range:           From JobRequirements.
        resume_skills:          Original (non-normalized) resume skills.
        total_years_experience: From CandidateProfile (may be None).
        overall_score:          Computed overall match percentage.
        missing_required:       Required skills with score == 0.
        missing_preferred:      Preferred skills with score == 0.

    Returns:
        List of message dicts ready for BedrockClient.invoke_for_json().
    """
    responsibilities_block = "\n".join(
        f"  - {r}" for r in key_responsibilities
    ) if key_responsibilities else "  (none listed)"

    user_content = COMPARISON_USER.format(
        job_title=job_title,
        company_name=company_name,
        required_skills=", ".join(required_skills) if required_skills else "(none)",
        preferred_skills=", ".join(preferred_skills) if preferred_skills else "(none)",
        key_responsibilities=responsibilities_block,
        salary_range=salary_range or "(not specified)",
        resume_skills=", ".join(resume_skills) if resume_skills else "(none)",
        total_years_experience=total_years_experience if total_years_experience is not None else "Unknown",
        overall_score=f"{overall_score:.1f}",
        missing_required=", ".join(missing_required) if missing_required else "(none)",
        missing_preferred=", ".join(missing_preferred) if missing_preferred else "(none)",
    )

    return [
        {"role": "system", "content": COMPARISON_SYSTEM},
        {"role": "user", "content": user_content},
    ]


def generate_llm_insights(
    job_title: str,
    company_name: str,
    required_skills: list[str],
    preferred_skills: list[str],
    key_responsibilities: list[str],
    salary_range: str,
    resume_skills: list[str],
    total_years_experience: Optional[int],
    overall_score: float,
    missing_required: list[str],
    missing_preferred: list[str],
    bedrock_client: Optional[BedrockClient] = None,
) -> tuple[LLMInsights, list[str]]:
    """Generate career insights via a single Bedrock LLM call.

    Creates a fresh BedrockClient with temperature=0.3 if none is
    injected.  On failure, returns an empty LLMInsights and the error.

    Args:
        (same as build_comparison_messages, plus bedrock_client)

    Returns:
        Tuple of (LLMInsights, errors).
        errors is an empty list on success, or contains the error message.
    """
    if bedrock_client is None:
        client = BedrockClient()
        client.temperature = 0.3
    else:
        client = bedrock_client

    messages = build_comparison_messages(
        job_title=job_title,
        company_name=company_name,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        key_responsibilities=key_responsibilities,
        salary_range=salary_range,
        resume_skills=resume_skills,
        total_years_experience=total_years_experience,
        overall_score=overall_score,
        missing_required=missing_required,
        missing_preferred=missing_preferred,
    )

    try:
        raw_json = client.invoke_for_json(messages)
        insights = LLMInsights.model_validate(raw_json)
        logger.info(
            "LLM insights generated: %d recommendations, %d questions",
            len(insights.upskilling_recommendations),
            len(insights.interview_questions),
        )
        return insights, []

    except BedrockLLMError as exc:
        error_msg = f"LLM insight generation failed: {exc}"
        logger.error(error_msg)
        return LLMInsights(), [error_msg]

    except Exception as exc:
        error_msg = f"LLM response validation failed: {exc}"
        logger.error(error_msg)
        return LLMInsights(), [error_msg]

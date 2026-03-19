"""
Deterministic scoring functions (Layer 4).

Computes skill match score, experience score, education match, and
overall score using rule-based formulas. No LLM calls.
"""

from __future__ import annotations

import re
from typing import Optional

from comparison_pipeline.models import SkillMatch


def compute_skill_score(
    required_matches: list[SkillMatch],
    preferred_matches: list[SkillMatch],
) -> float:
    """Compute weighted skill match score (0-100).

    When both required and preferred are present:
      score = avg_required * 0.70 * 100 + avg_preferred * 0.30 * 100

    When preferred is empty, required gets full weight:
      score = avg_required * 100

    When required is empty, returns 0.0.

    Args:
        required_matches:  SkillMatch results for required JD skills.
        preferred_matches: SkillMatch results for preferred JD skills.

    Returns:
        Skill score as a percentage (0-100), rounded to 1 decimal.
    """
    if not required_matches:
        return 0.0

    avg_required = sum(m.score for m in required_matches) / len(required_matches)

    if not preferred_matches:
        return round(avg_required * 100, 1)

    avg_preferred = sum(m.score for m in preferred_matches) / len(preferred_matches)
    score = avg_required * 0.70 * 100 + avg_preferred * 0.30 * 100
    return round(score, 1)


def compute_experience_score(
    candidate_years: Optional[int],
    required_years: Optional[int],
    resume_experience_count: int,
    errors: list[str],
) -> Optional[float]:
    """Compute experience match score (0-100) or None.

    Returns None when the JD does not specify a years requirement.
    When the candidate's experience is unknown, estimates from the
    number of resume experience entries and appends a note to errors.

    Fallback estimation:
      0 entries -> 0 years
      1 entry   -> 1 year
      2+ entries -> 3 years

    Args:
        candidate_years:        total_years_experience from CandidateProfile.
        required_years:         years_experience_required from JobRequirements.
        resume_experience_count: len(candidate_profile.resume_experience).
        errors:                 Mutable error list to append fallback notes.

    Returns:
        Score 0-100, or None if required_years is None.
    """
    if required_years is None:
        return None

    if required_years <= 0:
        return 100.0

    effective_years = candidate_years
    if effective_years is None:
        if resume_experience_count == 0:
            effective_years = 0
        elif resume_experience_count == 1:
            effective_years = 1
        else:
            effective_years = 3

        errors.append(
            f"Experience estimated from resume entries "
            f"({resume_experience_count} roles -> ~{effective_years} years estimate)"
        )

    score = min(effective_years / required_years, 1.0) * 100
    return round(score, 1)


def check_education_match(
    education_requirements: list[str],
    candidate_education: list[str],
) -> bool:
    """Check whether the JD education requirements overlap with the resume.

    Uses keyword intersection: combines all JD education strings into one
    text and all candidate education strings into another, then extracts
    meaningful words (4+ characters, alpha only) using regex and returns
    True if the two sets share at least one word.

    Args:
        education_requirements: From JobRequirements.education_requirements.
        candidate_education:    From CandidateProfile.education.

    Returns:
        True if there is at least one meaningful keyword in common.
    """
    if not education_requirements or not candidate_education:
        return False

    req_text = " ".join(education_requirements).lower()
    edu_text = " ".join(candidate_education).lower()

    req_words = set(re.findall(r'\b[a-z]{4,}\b', req_text))
    edu_words = set(re.findall(r'\b[a-z]{4,}\b', edu_text))

    return len(req_words.intersection(edu_words)) > 0


def compute_overall_score(
    skill_score: float,
    experience_score: Optional[float],
) -> float:
    """Compute the final overall match score (0-100).

    Formula:
      overall = skill_score * 0.80 + (experience_score or 0) * 0.20

    Args:
        skill_score:      From compute_skill_score() (0-100).
        experience_score: From compute_experience_score() (0-100 or None).

    Returns:
        Overall score rounded to 1 decimal place.
    """
    exp = experience_score if experience_score is not None else 0.0
    return round(skill_score * 0.80 + exp * 0.20, 1)

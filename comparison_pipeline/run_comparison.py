"""
Comparison pipeline entry point (Task 3).

Orchestrates all five layers in sequence:
  Layer 1  Normalize skills (rule-based)
  Layer 2  Ontology matching (rule-based)
  Layer 3  Semantic similarity (embedding-based)
  Layer 4  Deterministic scoring
  Layer 5  LLM career insights (single Bedrock call)

Never raises — errors are accumulated in ComparisonResult.errors.
"""

import logging
from typing import Optional

from extraction_pipeline.models import ExtractionState
from extraction_pipeline.llm_client import BedrockClient

from comparison_pipeline.models import ComparisonResult, SkillMatch
from comparison_pipeline.normalizer import normalize_skill, normalize_skill_list
from comparison_pipeline.ontology import ontology_match
from comparison_pipeline.similarity import compute_best_similarity, apply_similarity_threshold
from comparison_pipeline.scorer import (
    compute_skill_score,
    compute_experience_score,
    check_education_match,
    compute_overall_score,
)
from comparison_pipeline.llm_layer import generate_llm_insights

logger = logging.getLogger(__name__)


def _match_skills(
    jd_skills: list[str],
    normalized_resume: list[str],
    errors: list[str],
    similarity_model=None,
) -> list[SkillMatch]:
    """Run a list of JD skills through all matching layers.

    For each skill:
      1. Normalize it.
      2. Try ontology match (exact / alias / related).
      3. If unmatched, try semantic similarity.
      4. Record the result as a SkillMatch.

    Args:
        jd_skills:        Raw skill strings from the JD.
        normalized_resume: Pre-normalized resume skill list.
        errors:           Mutable error list for semantic layer issues.
        similarity_model: Optional injected model for DI/testing.

    Returns:
        List of SkillMatch objects, one per JD skill.
    """
    matches: list[SkillMatch] = []

    for raw_skill in jd_skills:
        norm_skill = normalize_skill(raw_skill)

        if not norm_skill:
            continue

        match_type, score, matched_to = ontology_match(norm_skill, normalized_resume)

        if match_type != "none":
            matches.append(SkillMatch(
                skill=norm_skill,
                match_type=match_type,
                score=score,
                matched_to=matched_to,
            ))
            continue

        raw_sim, sim_match = compute_best_similarity(
            norm_skill, normalized_resume, model=similarity_model,
        )
        confidence = apply_similarity_threshold(raw_sim)

        if confidence > 0.0:
            matches.append(SkillMatch(
                skill=norm_skill,
                match_type="semantic",
                score=confidence,
                matched_to=sim_match,
            ))
        else:
            matches.append(SkillMatch(
                skill=norm_skill,
                match_type="none",
                score=0.0,
                matched_to=None,
            ))

    return matches


def run_comparison(
    extraction_state: ExtractionState,
    bedrock_client: Optional[BedrockClient] = None,
    similarity_model=None,
) -> ComparisonResult:
    """Run the full comparison pipeline (Task 3).

    Consumes an ExtractionState from Task 2 and produces a
    ComparisonResult with deterministic scores and LLM insights.

    Never raises.  If inputs are missing or the LLM fails, partial
    results are returned with errors populated.

    Args:
        extraction_state: Output from Task 2's run_extraction().
        bedrock_client:   Optional BedrockClient for DI/testing.
        similarity_model: Optional sentence-transformers model for DI/testing.

    Returns:
        ComparisonResult ready for Task 4 (FastAPI).
    """
    result = ComparisonResult()

    jr = extraction_state.job_requirements
    cp = extraction_state.candidate_profile

    if jr is None:
        result.errors.append("No job requirements available from extraction")
        logger.error("Task 3 aborted: no job requirements")
        return result

    if cp is None:
        result.errors.append("No candidate profile available from extraction")
        logger.error("Task 3 aborted: no candidate profile")
        return result

    # ── Layer 1: Normalize ─────────────────────────────────────────────
    normalized_resume = normalize_skill_list(cp.resume_skills)

    if not jr.required_skills:
        result.errors.append("No required skills in job description")

    # ── Layers 2-3: Match ──────────────────────────────────────────────
    required_matches = _match_skills(
        jr.required_skills, normalized_resume, result.errors, similarity_model,
    )
    preferred_matches = _match_skills(
        jr.preferred_skills, normalized_resume, result.errors, similarity_model,
    )

    result.required_skill_matches = required_matches
    result.preferred_skill_matches = preferred_matches

    result.missing_required_skills = [
        m.skill for m in required_matches if m.score == 0.0
    ]
    result.missing_preferred_skills = [
        m.skill for m in preferred_matches if m.score == 0.0
    ]

    # ── Layer 4: Score ─────────────────────────────────────────────────
    result.skill_score = compute_skill_score(required_matches, preferred_matches)

    result.experience_score = compute_experience_score(
        candidate_years=cp.total_years_experience,
        required_years=jr.years_experience_required,
        resume_experience_count=len(cp.resume_experience),
        errors=result.errors,
    )

    result.education_matched = check_education_match(
        jr.education_requirements, cp.education,
    )

    result.overall_score = compute_overall_score(
        result.skill_score, result.experience_score,
    )

    logger.info(
        "Scores computed: skill=%.1f, experience=%s, overall=%.1f",
        result.skill_score,
        f"{result.experience_score:.1f}" if result.experience_score is not None else "N/A",
        result.overall_score,
    )

    # ── Layer 5: LLM Insights ─────────────────────────────────────────
    insights, llm_errors = generate_llm_insights(
        job_title=jr.job_title,
        company_name=jr.company_name,
        required_skills=jr.required_skills,
        preferred_skills=jr.preferred_skills,
        key_responsibilities=jr.key_responsibilities,
        salary_range=jr.salary_range,
        resume_skills=cp.resume_skills,
        total_years_experience=cp.total_years_experience,
        overall_score=result.overall_score,
        missing_required=result.missing_required_skills,
        missing_preferred=result.missing_preferred_skills,
        bedrock_client=bedrock_client,
    )

    result.errors.extend(llm_errors)

    result.strengths_summary = insights.strengths_summary
    result.gaps_summary = insights.gaps_summary
    result.upskilling_recommendations = insights.upskilling_recommendations
    result.interview_questions = insights.interview_questions
    result.salary_insight = insights.salary_insight

    logger.info("Task 3 comparison pipeline complete (errors: %d)", len(result.errors))
    return result

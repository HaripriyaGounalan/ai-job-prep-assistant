"""Tests for deterministic scoring functions (Layer 4)."""

import pytest

from comparison_pipeline.models import SkillMatch
from comparison_pipeline.scorer import (
    compute_skill_score,
    compute_experience_score,
    check_education_match,
    compute_overall_score,
)


def _match(skill: str, score: float, match_type: str = "exact") -> SkillMatch:
    return SkillMatch(skill=skill, match_type=match_type, score=score)


class TestComputeSkillScore:
    def test_all_exact_matches(self):
        required = [_match("python", 1.0), _match("java", 1.0)]
        score = compute_skill_score(required, [])
        assert score == 100.0

    def test_all_missing(self):
        required = [_match("rust", 0.0, "none"), _match("go", 0.0, "none")]
        score = compute_skill_score(required, [])
        assert score == 0.0

    def test_mixed_scores(self):
        required = [
            _match("python", 1.0),
            _match("java", 1.0),
            _match("c", 0.0, "none"),
            _match("c++", 0.0, "none"),
            _match("machine learning", 0.75, "related"),
            _match("deep learning", 0.75, "related"),
        ]
        score = compute_skill_score(required, [])
        expected = (3.5 / 6) * 100
        assert abs(score - round(expected, 1)) < 0.1

    def test_with_preferred(self):
        required = [_match("python", 1.0)]
        preferred = [_match("docker", 1.0), _match("k8s", 0.0, "none")]
        score = compute_skill_score(required, preferred)
        expected = 1.0 * 0.70 * 100 + 0.5 * 0.30 * 100
        assert abs(score - round(expected, 1)) < 0.1

    def test_empty_preferred_full_weight_to_required(self):
        required = [_match("python", 1.0), _match("java", 0.0, "none")]
        score = compute_skill_score(required, [])
        assert score == 50.0

    def test_empty_required(self):
        score = compute_skill_score([], [_match("docker", 1.0)])
        assert score == 0.0


class TestComputeExperienceScore:
    def test_exact_match(self):
        errors = []
        score = compute_experience_score(5, 5, 3, errors)
        assert score == 100.0
        assert errors == []

    def test_exceeds_required(self):
        errors = []
        score = compute_experience_score(10, 5, 4, errors)
        assert score == 100.0

    def test_below_required(self):
        errors = []
        score = compute_experience_score(2, 5, 2, errors)
        assert score == 40.0

    def test_none_candidate_fallback_zero_entries(self):
        errors = []
        score = compute_experience_score(None, 3, 0, errors)
        assert score == 0.0
        assert len(errors) == 1
        assert "0 roles" in errors[0]

    def test_none_candidate_fallback_one_entry(self):
        errors = []
        score = compute_experience_score(None, 3, 1, errors)
        expected = (1 / 3) * 100
        assert abs(score - round(expected, 1)) < 0.1
        assert "1 roles" in errors[0]

    def test_none_candidate_fallback_two_plus_entries(self):
        errors = []
        score = compute_experience_score(None, 3, 4, errors)
        assert score == 100.0
        assert "4 roles" in errors[0]
        assert "~3 years" in errors[0]

    def test_none_required_returns_none(self):
        errors = []
        score = compute_experience_score(5, None, 3, errors)
        assert score is None
        assert errors == []

    def test_both_none(self):
        errors = []
        score = compute_experience_score(None, None, 0, errors)
        assert score is None


class TestCheckEducationMatch:
    def test_match_found(self):
        reqs = ["BS in Computer Science or equivalent"]
        edu = ["BS Computer Science, Stanford University, 2016"]
        assert check_education_match(reqs, edu) is True

    def test_no_match(self):
        reqs = ["PhD in Physics"]
        edu = ["BS Computer Science, MIT, 2018"]
        assert check_education_match(reqs, edu) is False

    def test_case_insensitive(self):
        reqs = ["bachelor's degree in computer science"]
        edu = ["Bachelor's Degree in Computer Science, MIT, 2018"]
        assert check_education_match(reqs, edu) is True

    def test_empty_requirements(self):
        assert check_education_match([], ["BS CS"]) is False

    def test_empty_education(self):
        assert check_education_match(["BS CS"], []) is False


class TestComputeOverallScore:
    def test_with_experience(self):
        score = compute_overall_score(80.0, 100.0)
        assert score == 84.0

    def test_without_experience(self):
        score = compute_overall_score(80.0, None)
        assert score == 64.0

    def test_zero_scores(self):
        assert compute_overall_score(0.0, 0.0) == 0.0
        assert compute_overall_score(0.0, None) == 0.0

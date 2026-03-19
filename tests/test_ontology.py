"""Tests for the skill ontology matching (Layer 2)."""

import pytest

from comparison_pipeline.ontology import ontology_match, SKILL_ONTOLOGY


class TestOntologyMatch:
    def test_exact_match(self):
        match_type, score, matched_to = ontology_match(
            "python", ["python", "java", "go"]
        )
        assert match_type == "exact"
        assert score == 1.0
        assert matched_to == "python"

    def test_alias_match(self):
        match_type, score, matched_to = ontology_match(
            "c++", ["cpp", "java", "python"]
        )
        assert match_type == "alias"
        assert score == 1.0
        assert matched_to == "cpp"

    def test_related_match(self):
        match_type, score, matched_to = ontology_match(
            "machine learning", ["tensorflow", "pandas", "react"]
        )
        assert match_type == "related"
        assert score == 0.75
        assert matched_to == "tensorflow"

    def test_no_match(self):
        match_type, score, matched_to = ontology_match(
            "rust", ["python", "java", "go"]
        )
        assert match_type == "none"
        assert score == 0.0
        assert matched_to is None

    def test_skill_not_in_ontology(self):
        match_type, score, matched_to = ontology_match(
            "figma", ["sketch", "adobe xd"]
        )
        assert match_type == "none"
        assert score == 0.0
        assert matched_to is None

    def test_multiple_related_returns_first(self):
        match_type, score, matched_to = ontology_match(
            "deep learning", ["neural networks", "tensorflow", "keras"]
        )
        assert match_type == "related"
        assert score == 0.75
        assert matched_to is not None

    def test_empty_resume_skills(self):
        match_type, score, matched_to = ontology_match("python", [])
        assert match_type == "none"
        assert score == 0.0
        assert matched_to is None

    def test_related_match_score_value(self):
        _, score, _ = ontology_match(
            "kubernetes", ["docker", "nginx"]
        )
        assert score == 0.75

    def test_alias_match_score_value(self):
        _, score, _ = ontology_match(
            "c#", ["csharp", "java"]
        )
        assert score == 1.0


class TestOntologyIntegrity:
    def test_minimum_entry_count(self):
        assert len(SKILL_ONTOLOGY) >= 20

    def test_all_entries_have_required_keys(self):
        for name, entry in SKILL_ONTOLOGY.items():
            assert "aliases" in entry, f"{name} missing 'aliases'"
            assert "category" in entry, f"{name} missing 'category'"
            assert "related" in entry, f"{name} missing 'related'"

    def test_no_aws_alias_in_amazon_web_services(self):
        entry = SKILL_ONTOLOGY.get("amazon web services")
        assert entry is not None
        assert "aws" not in entry["aliases"], (
            "Redundant: 'aws' alias handled by normalizer"
        )

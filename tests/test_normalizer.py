"""Tests for the skill normalizer (Layer 1)."""

import pytest

from comparison_pipeline.normalizer import (
    normalize_skill,
    normalize_skill_list,
    SKILL_ALIASES,
)


class TestNormalizeSkill:
    def test_lowercase(self):
        assert normalize_skill("Python") == "python"
        assert normalize_skill("JAVA") == "java"

    def test_strip_whitespace(self):
        assert normalize_skill("  React.js  ") == "react"
        assert normalize_skill("\tPython\n") == "python"

    def test_alias_resolution(self):
        assert normalize_skill("reactjs") == "react"
        assert normalize_skill("k8s") == "kubernetes"
        assert normalize_skill("K8S") == "kubernetes"
        assert normalize_skill("sklearn") == "scikit-learn"

    def test_multi_word_alias(self):
        assert normalize_skill("gen ai") == "generative ai"
        assert normalize_skill("Gen AI") == "generative ai"
        assert normalize_skill("ci cd") == "ci/cd"

    def test_unknown_skill_passthrough(self):
        assert normalize_skill("SomeNewTool") == "somenewtool"
        assert normalize_skill("Figma") == "figma"

    def test_empty_string(self):
        assert normalize_skill("") == ""

    def test_special_chars_preserved(self):
        assert normalize_skill("C++") == "c++"
        assert normalize_skill("C#") == "c#"
        assert normalize_skill(".NET") == ".net"

    def test_collapse_internal_whitespace(self):
        assert normalize_skill("machine   learning") == "machine learning"
        assert normalize_skill("gen   ai") == "generative ai"

    def test_chained_alias_not_double_applied(self):
        assert normalize_skill("py") == "python"
        assert normalize_skill("JS") == "javascript"


class TestNormalizeSkillList:
    def test_normalize_and_dedup(self):
        result = normalize_skill_list(["Python", "python", "PYTHON"])
        assert result == ["python"]

    def test_empty_list(self):
        assert normalize_skill_list([]) == []

    def test_preserves_order_of_first_occurrence(self):
        result = normalize_skill_list(["Java", "Python", "JAVA", "Go"])
        assert result == ["java", "python", "go"]

    def test_removes_empty_strings(self):
        result = normalize_skill_list(["Python", "", "  ", "Java"])
        assert result == ["python", "java"]

    def test_alias_dedup(self):
        result = normalize_skill_list(["React.js", "ReactJS", "react"])
        assert result == ["react"]


class TestSkillAliasesIntegrity:
    def test_minimum_alias_count(self):
        assert len(SKILL_ALIASES) >= 40

    def test_all_values_are_lowercase(self):
        for key, value in SKILL_ALIASES.items():
            assert value == value.lower(), f"Alias value '{value}' for key '{key}' is not lowercase"

    def test_all_keys_are_lowercase(self):
        for key in SKILL_ALIASES:
            assert key == key.lower(), f"Alias key '{key}' is not lowercase"

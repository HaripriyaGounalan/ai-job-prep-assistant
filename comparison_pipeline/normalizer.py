"""
Skill normalization utilities (Layer 1).

Normalizes raw skill strings from both JD and resume into canonical
form before any matching takes place. This is a pure rule-based layer
with no LLM calls.

Pipeline per skill:
  1. Lowercase
  2. Strip leading/trailing whitespace
  3. Collapse internal whitespace
  4. Apply SKILL_ALIASES to unify common variants
"""

import re


SKILL_ALIASES: dict[str, str] = {
    # JavaScript ecosystem
    "react.js": "react",
    "reactjs": "react",
    "react js": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "vue js": "vue",
    "angular.js": "angular",
    "angularjs": "angular",
    "angular js": "angular",
    "next.js": "nextjs",
    "nextjs": "nextjs",
    "next js": "nextjs",
    "node.js": "node.js",
    "nodejs": "node.js",
    "node js": "node.js",
    "express.js": "express",
    "expressjs": "express",
    "js": "javascript",
    "es6": "javascript",
    "ecmascript": "javascript",
    "ts": "typescript",

    # Python ecosystem
    "py": "python",
    "python3": "python",
    "python 3": "python",
    "scikit learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "sk-learn": "scikit-learn",

    # AI / ML
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "tf": "tensorflow",
    "torch": "pytorch",
    "genai": "generative ai",
    "gen ai": "generative ai",
    "llm": "large language models",
    "llms": "large language models",

    # Cloud / DevOps
    "k8s": "kubernetes",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "google cloud": "google cloud platform",
    "cicd": "ci/cd",
    "ci cd": "ci/cd",

    # Databases
    "postgres": "postgresql",
    "mongo": "mongodb",
    "mssql": "sql server",
    "ms sql": "sql server",

    # General
    "oop": "object-oriented programming",
    "oops": "object-oriented programming",
    "dsa": "data structures and algorithms",
}


def normalize_skill(skill: str) -> str:
    """Normalize a single skill string to canonical form.

    Steps:
      1. Lowercase
      2. Strip outer whitespace
      3. Collapse runs of internal whitespace to a single space
      4. Look up in SKILL_ALIASES; return canonical if found

    Args:
        skill: Raw skill string (e.g. "React.js", "  K8S  ").

    Returns:
        Normalized canonical skill string.
    """
    if not skill:
        return ""

    result = skill.lower().strip()
    result = re.sub(r"\s+", " ", result)

    return SKILL_ALIASES.get(result, result)


def normalize_skill_list(skills: list[str]) -> list[str]:
    """Normalize a list of skills, removing duplicates and empties.

    Preserves insertion order of first occurrence.

    Args:
        skills: Raw skill strings from JD or resume.

    Returns:
        Deduplicated list of normalized skill strings.
    """
    seen: set[str] = set()
    normalized: list[str] = []

    for skill in skills:
        canonical = normalize_skill(skill)
        if canonical and canonical not in seen:
            seen.add(canonical)
            normalized.append(canonical)

    return normalized

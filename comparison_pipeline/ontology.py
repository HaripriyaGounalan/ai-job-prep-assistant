"""
Skill ontology for semantic-category matching (Layer 2).

Defines a dictionary of canonical skills with their aliases, category,
and related skills. Used after Layer 1 normalization to detect alias
matches (full credit) and related-skill matches (partial credit)
before falling back to embedding-based similarity.

Match types:
  exact   — skill is directly in the resume skills set         (1.0)
  alias   — an ontology alias of the skill is in resume        (1.0)
  related — a related skill from the ontology is in resume     (0.75)
  none    — no match found in the ontology                     (0.0)
"""

SKILL_ONTOLOGY: dict[str, dict] = {
    "python": {
        "aliases": [],
        "category": "programming language",
        "related": ["flask", "django", "fastapi", "pandas", "numpy", "scikit-learn"],
    },
    "javascript": {
        "aliases": [],
        "category": "programming language",
        "related": ["typescript", "react", "node.js", "angular", "vue"],
    },
    "typescript": {
        "aliases": [],
        "category": "programming language",
        "related": ["javascript", "react", "angular", "node.js"],
    },
    "java": {
        "aliases": [],
        "category": "programming language",
        "related": ["spring", "maven", "gradle", "kotlin"],
    },
    "c++": {
        "aliases": ["cpp"],
        "category": "programming language",
        "related": ["c", "systems programming"],
    },
    "c": {
        "aliases": [],
        "category": "programming language",
        "related": ["c++", "systems programming"],
    },
    "c#": {
        "aliases": ["csharp", "c sharp"],
        "category": "programming language",
        "related": [".net", "asp.net", "unity"],
    },
    "machine learning": {
        "aliases": [],
        "category": "ai/ml concept",
        "related": [
            "deep learning", "scikit-learn", "tensorflow", "pytorch",
            "neural networks", "data science", "keras", "numpy", "pandas",
        ],
    },
    "deep learning": {
        "aliases": [],
        "category": "ai/ml concept",
        "related": [
            "machine learning", "neural networks", "tensorflow", "pytorch",
            "keras", "cnn", "rnn", "transformers",
        ],
    },
    "natural language processing": {
        "aliases": [],
        "category": "ai/ml concept",
        "related": ["machine learning", "transformers", "spacy", "text mining"],
    },
    "computer vision": {
        "aliases": [],
        "category": "ai/ml concept",
        "related": ["deep learning", "cnn", "opencv", "image processing", "tensorflow"],
    },
    "tensorflow": {
        "aliases": [],
        "category": "ml framework",
        "related": ["keras", "deep learning", "machine learning", "neural networks", "pytorch"],
    },
    "pytorch": {
        "aliases": [],
        "category": "ml framework",
        "related": ["tensorflow", "deep learning", "machine learning", "neural networks", "keras"],
    },
    "keras": {
        "aliases": [],
        "category": "ml framework",
        "related": ["tensorflow", "deep learning", "neural networks", "pytorch"],
    },
    "scikit-learn": {
        "aliases": [],
        "category": "ml library",
        "related": ["machine learning", "python", "pandas", "numpy", "data science"],
    },
    "react": {
        "aliases": [],
        "category": "frontend framework",
        "related": ["javascript", "redux", "nextjs", "html", "css", "typescript"],
    },
    "angular": {
        "aliases": [],
        "category": "frontend framework",
        "related": ["javascript", "typescript", "html", "css", "rxjs"],
    },
    "node.js": {
        "aliases": [],
        "category": "backend runtime",
        "related": ["javascript", "express", "typescript"],
    },
    "kubernetes": {
        "aliases": [],
        "category": "devops/cloud",
        "related": ["docker", "containerization", "microservices", "ci/cd"],
    },
    "docker": {
        "aliases": [],
        "category": "devops/cloud",
        "related": ["kubernetes", "containerization", "microservices", "ci/cd"],
    },
    "amazon web services": {
        "aliases": [],
        "category": "cloud platform",
        "related": ["s3", "ec2", "lambda", "cloud computing"],
    },
    "sql": {
        "aliases": [],
        "category": "database",
        "related": ["postgresql", "mysql", "sql server", "database"],
    },
    "postgresql": {
        "aliases": [],
        "category": "database",
        "related": ["sql", "mysql", "database"],
    },
    "mongodb": {
        "aliases": [],
        "category": "database",
        "related": ["nosql", "database"],
    },
    "generative ai": {
        "aliases": [],
        "category": "ai/ml concept",
        "related": ["large language models", "transformers", "deep learning"],
    },
    "git": {
        "aliases": [],
        "category": "version control",
        "related": ["github", "gitlab", "ci/cd"],
    },
}


def ontology_match(
    skill: str,
    resume_skills: list[str],
) -> tuple[str, float, str | None]:
    """Check the ontology for an alias or related-skill match.

    Assumes both ``skill`` and ``resume_skills`` are already normalized
    via Layer 1 (lowercase, alias-resolved).

    Matching priority:
      1. Exact — skill string is directly in resume_skills.
      2. Alias — an ontology alias of the skill appears in resume_skills.
      3. Related — a related skill from the ontology appears in resume_skills.
      4. None — no match found.

    Args:
        skill:         Normalized JD skill to look up.
        resume_skills: Normalized list of resume skills to match against.

    Returns:
        Tuple of (match_type, score, matched_to):
          match_type: "exact" | "alias" | "related" | "none"
          score:      1.0 for exact/alias, 0.75 for related, 0.0 for none
          matched_to: The resume skill string that matched, or None.
    """
    if not resume_skills:
        return ("none", 0.0, None)

    resume_set = set(resume_skills)

    if skill in resume_set:
        return ("exact", 1.0, skill)

    entry = SKILL_ONTOLOGY.get(skill)
    if entry is None:
        return ("none", 0.0, None)

    for alias in entry["aliases"]:
        if alias in resume_set:
            return ("alias", 1.0, alias)

    for related in entry["related"]:
        if related in resume_set:
            return ("related", 0.75, related)

    return ("none", 0.0, None)

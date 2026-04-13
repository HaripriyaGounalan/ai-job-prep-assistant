import type { ComparisonResult } from "@/lib/types"

export const demoResult: ComparisonResult = {
  overall_score: 78,
  skill_score: 74,
  experience_score: 92,
  education_matched: true,
  required_skill_matches: [
    { skill: "python", match_type: "exact", score: 1, matched_to: "python" },
    { skill: "aws", match_type: "exact", score: 1, matched_to: "aws" },
    {
      skill: "machine learning",
      match_type: "exact",
      score: 1,
      matched_to: "machine learning",
    },
    {
      skill: "langgraph",
      match_type: "related",
      score: 0.78,
      matched_to: "langchain",
    },
    { skill: "docker", match_type: "none", score: 0, matched_to: null },
  ],
  preferred_skill_matches: [
    { skill: "pytorch", match_type: "exact", score: 1, matched_to: "pytorch" },
    { skill: "fastapi", match_type: "exact", score: 1, matched_to: "fastapi" },
    { skill: "terraform", match_type: "none", score: 0, matched_to: null },
    {
      skill: "mentorship",
      match_type: "related",
      score: 0.72,
      matched_to: "team leadership",
    },
  ],
  missing_required_skills: ["docker"],
  missing_preferred_skills: ["terraform"],
  strengths_summary:
    "The candidate shows strong alignment across core ML engineering requirements, especially Python, AWS, and model development experience. Their previous backend delivery work suggests they can contribute quickly in a production-focused team.",
  gaps_summary:
    "The most important short-term gap is infrastructure packaging and deployment depth. Strengthening Docker and infrastructure-as-code knowledge would make the profile more convincing for end-to-end platform ownership.",
  upskilling_recommendations: [
    {
      skill: "Docker",
      reason: "Container fluency closes a core deployment gap and makes backend services easier to ship and test.",
      resource: "Docker Docs: Get Started Workshop",
    },
    {
      skill: "Terraform",
      reason: "Infrastructure-as-code experience strengthens cloud credibility for platform-heavy ML roles.",
      resource: "HashiCorp Learn: Terraform on AWS",
    },
    {
      skill: "LangGraph",
      reason: "A deeper graph orchestration story would directly support agentic workflow discussions in interviews.",
      resource: "LangGraph documentation and quickstart examples",
    },
  ],
  interview_questions: [
    {
      question:
        "Walk us through a machine learning system you moved from experimentation into a production-ready workflow.",
      category: "technical",
    },
    {
      question:
        "How would you design a safe polling loop between a frontend client and an asynchronous backend job service?",
      category: "technical",
    },
    {
      question:
        "Tell us about a time you had to explain a model tradeoff to someone outside the engineering team.",
      category: "behavioral",
    },
    {
      question:
        "What signals would you monitor after releasing a new resume matching pipeline to production?",
      category: "technical",
    },
    {
      question:
        "Describe a project where you noticed a tooling gap and proactively created a better workflow for the team.",
      category: "behavioral",
    },
  ],
  salary_insight:
    "For North American ML platform roles with this profile, the market story reads strongest in the mid-to-senior band once deployment tooling depth is clearer.",
  errors: [
    "Preview data shown until you upload a real resume and job description.",
  ],
}

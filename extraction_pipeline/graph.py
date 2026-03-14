"""
LangGraph extraction workflow.

Defines a stateful graph with two parallel extraction nodes:
  1. extract_job_requirements  — parses the job description
  2. extract_candidate_profile — parses the resume

Both run off the same state and can execute in parallel (they read
different fields and write to different keys). The graph finishes
with a finalize node that sets the status.

Architecture:
    ┌─────────┐
    │  START   │
    └────┬─────┘
         │
    ┌────▼─────┐     ┌──────────────────┐
    │ extract  │     │    extract        │
    │ job reqs │     │ candidate profile │
    └────┬─────┘     └────────┬──────────┘
         │                    │
         └───────┬────────────┘
            ┌────▼─────┐
            │ finalize │
            └────┬─────┘
            ┌────▼─────┐
            │   END    │
            └──────────┘

LangGraph's StateGraph manages the merge of partial state updates
from each node automatically.
"""

import logging
import operator
from typing import Any, Annotated, Optional, TypedDict

from extraction_pipeline.models import (
    JobRequirements,
    CandidateProfile,
    ExtractionState,
)
from extraction_pipeline.nodes import (
    extract_job_requirements,
    extract_candidate_profile,
)
from extraction_pipeline.llm_client import BedrockClient

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LangGraph TypedDict State
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class GraphState(TypedDict, total=False):
    """
    State schema for the extraction graph.

    LangGraph uses this to know which keys exist and how to merge
    updates from parallel nodes. The `errors` key uses operator.add
    so parallel nodes can both append errors without overwriting.
    """
    resume_text: str
    job_description_text: str
    job_requirements: Optional[JobRequirements]
    candidate_profile: Optional[CandidateProfile]
    errors: Annotated[list[str], operator.add]
    status: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Node wrappers (bind the LLM client)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _make_jd_node(llm_client: BedrockClient | None = None):
    """Create a JD extraction node, optionally with an injected client."""
    def node(state: dict[str, Any]) -> dict[str, Any]:
        return extract_job_requirements(state, llm_client)
    return node


def _make_resume_node(llm_client: BedrockClient | None = None):
    """Create a resume extraction node, optionally with an injected client."""
    def node(state: dict[str, Any]) -> dict[str, Any]:
        return extract_candidate_profile(state, llm_client)
    return node


def _finalize_node(state: dict[str, Any]) -> dict[str, Any]:
    """Set the final status based on whether extractions succeeded."""
    errors = state.get("errors", [])
    has_jd = state.get("job_requirements") is not None
    has_resume = state.get("candidate_profile") is not None

    if has_jd and has_resume:
        status = "completed"
    elif has_jd or has_resume:
        status = "partial"
    else:
        status = "failed"

    if errors:
        logger.warning("Extraction finished with %d error(s)", len(errors))

    logger.info("Extraction pipeline status: %s", status)
    return {"status": status}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Graph builder
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_extraction_graph(llm_client: BedrockClient | None = None):
    """
    Build and compile the LangGraph extraction workflow.

    Args:
        llm_client: Optional Bedrock client for dependency injection.

    Returns:
        A compiled LangGraph StateGraph, ready to invoke.
    """
    from langgraph.graph import StateGraph, START, END

    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("extract_job", _make_jd_node(llm_client))
    graph.add_node("extract_resume", _make_resume_node(llm_client))
    graph.add_node("finalize", _finalize_node)

    # Wire edges: START fans out to both extraction nodes in parallel
    graph.add_edge(START, "extract_job")
    graph.add_edge(START, "extract_resume")

    # Both extraction nodes converge into finalize
    graph.add_edge("extract_job", "finalize")
    graph.add_edge("extract_resume", "finalize")

    # Finalize → END
    graph.add_edge("finalize", END)

    return graph.compile()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Convenience runner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_extraction(
    resume_text: str,
    job_description_text: str,
    llm_client: BedrockClient | None = None,
) -> ExtractionState:
    """
    Run the full extraction pipeline.

    This is the main entry point for Task 2. Takes raw text from
    Task 1's OCR pipeline and returns structured extractions.

    Args:
        resume_text:          Cleaned resume text from OCR.
        job_description_text: Cleaned JD text from OCR.
        llm_client:           Optional Bedrock client for DI/testing.

    Returns:
        ExtractionState with populated job_requirements and candidate_profile.
    """
    graph = build_extraction_graph(llm_client)

    initial_state: GraphState = {
        "resume_text": resume_text,
        "job_description_text": job_description_text,
        "errors": [],
        "status": "running",
    }

    result = graph.invoke(initial_state)

    # Convert to our Pydantic state model for a clean return type
    return ExtractionState(
        resume_text=result.get("resume_text", ""),
        job_description_text=result.get("job_description_text", ""),
        job_requirements=result.get("job_requirements"),
        candidate_profile=result.get("candidate_profile"),
        errors=result.get("errors", []),
        status=result.get("status", "unknown"),
    )
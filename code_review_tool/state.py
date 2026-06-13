"""
state.py — Shared state schema, reducers, and Pydantic output models.

Import this in nodes.py and in the notebook instead of redefining inline.
"""
import operator
from typing import TypedDict, Annotated, Optional, List

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Reducer: sums token usage dicts across parallel nodes
# ------------------------------------------------------------------
def merge_usage(a: dict, b: dict) -> dict:
    return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}


# ------------------------------------------------------------------
# Pydantic output models
# ------------------------------------------------------------------
class SimpleReviewOutput(BaseModel):
    confidence:      int = Field(description="Confidence score 0-100 that the change is safe to merge")
    findings:        str = Field(description="Summary of key findings")
    recommendations: str = Field(description="Additional recommendations or observations")


class FixItem(BaseModel):
    """A single actionable fix item returned by the Tech Lead agent."""
    issue:       str = Field(description="The specific problem that must be fixed")
    solution:    str = Field(description="The recommended fix or approach")
    explanation: str = Field(description="Why this must be fixed and the risk if not addressed")


class SummarizeFindingsOutput(BaseModel):
    confidence:      int           = Field(description="Confidence score 0-100 that the change is safe to merge")
    findings:        str           = Field(description="Summary of key findings from both quality and security analyses")
    fix:             List[FixItem] = Field(description="Items the author MUST fix before merge")
    recommendations: str           = Field(description="Additional recommendations or observations")


# ------------------------------------------------------------------
# Shared state schema
# ------------------------------------------------------------------
class PRReviewState(TypedDict):
    """
    Shared state passed through the entire Code Review Tool graph.

    Fields:
        pr_file_path      : path to the PR diff file (caller must supply)
        pr_content        : raw diff text (populated by read_pr)
        review_type       : routing decision — 'simple', 'full', or 'error'
        quality_findings  : Senior Developer output (full path only)
        security_findings : Security Engineer output (full path only)
        summary           : Tech Lead synthesis as JSON string (full path only)
        simple_review     : Simple LLM review as JSON string (simple path only)
        final_decision    : APPROVED / REQUEST CHANGES / REJECT verdict
        errors            : append-only list of errors (reducer: operator.add)
        tokens_used       : cumulative token counts (reducer: merge_usage)
        messages          : append-only execution log (reducer: operator.add)
    """
    pr_file_path:      str
    pr_content:        str
    review_type:       str
    quality_findings:  Optional[str]
    security_findings: Optional[str]
    summary:           Optional[str]
    simple_review:     Optional[str]
    final_decision:    Optional[str]
    errors:            Annotated[list, operator.add]
    tokens_used:       Annotated[dict, merge_usage]
    messages:          Annotated[list, operator.add]

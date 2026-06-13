"""
nodes.py — All LangGraph node functions for the Code Review Tool.

Usage:
    from nodes import (
        read_pr_file, route_review_type, routing_edge,
        simple_review_node, quality_analysis_node, security_review_node,
        aggregate_node, output_guardrail, blocked_review_node,
        report_guardrail, summarize_findings_node,
        final_decision_node, return_final_answer, full_review_start
    )
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from state import (
    PRReviewState,
    SimpleReviewOutput,
    QualityJudgeOutput,
    SummarizeFindingsOutput,
    merge_usage,
)

load_dotenv(Path(__file__).parent / ".env")

NOTEBOOK_DIR = Path(__file__).parent

llm       = ChatOpenAI(model="gpt-4o",      temperature=0)
judge_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ------------------------------------------------------------------
# read_pr_file — I/O node
# ------------------------------------------------------------------
def read_pr_file(state: PRReviewState) -> dict:
    path = Path(state["pr_file_path"])
    if not path.is_absolute():
        path = NOTEBOOK_DIR / path
    try:
        content = path.read_text()
        return {
            "pr_content": content,
            "messages": [f"[read_pr] Loaded: {path.name} ({len(content)} chars)"],
        }
    except FileNotFoundError:
        msg = f"PR file not found: {path}"
        return {"errors": [msg], "messages": [f"[read_pr] ERROR: {msg}"]}
    except Exception as e:
        msg = f"Failed to read PR file: {e}"
        return {"errors": [msg], "messages": [f"[read_pr] ERROR: {msg}"]}


# ------------------------------------------------------------------
# route_review_type — LLM router node
# ------------------------------------------------------------------
def route_review_type(state: PRReviewState) -> dict:
    if state.get("errors"):
        return {
            "review_type": "error",
            "messages": ["[router] Upstream error — routing to error handler"],
        }

    system_prompt = """You are a senior engineering manager triaging pull requests.

Given a code diff, classify it as either:
- 'simple'  : only minor/cosmetic changes (import aliases, whitespace, comments, variable renames with no logic change)
- 'full'    : contains logic changes, authentication code, security-sensitive operations,
              new functions, database queries, or anything requiring deep review

Respond with ONLY one word: simple or full. No explanation."""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"PR Diff:\n\n{state['pr_content']}"),
        ])
        decision = response.content.strip().lower()
        usage = response.usage_metadata or {}
    except Exception as e:
        decision = "full"
        usage = {}

    if decision not in ("simple", "full"):
        review_type = "full"
    else:
        review_type = decision

    return {
        "review_type": review_type,
        "tokens_used": {
            "input_tokens":  usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens":  usage.get("total_tokens", 0),
        },
        "messages": [f"[router] Review type: {review_type}"],
    }


def routing_edge(state: PRReviewState) -> str:
    """Conditional edge — returns 'simple', 'full', or 'error'."""
    return state["review_type"]


# ------------------------------------------------------------------
# simple_review_node — lightweight LLM review
# ------------------------------------------------------------------
def simple_review_node(state: PRReviewState) -> dict:
    structured_llm = llm.with_structured_output(SimpleReviewOutput, include_raw=True)
    system_prompt = """You are a code reviewer. The change is minor and low-risk.
Review the PR diff and return a structured assessment with:
- confidence: integer 0-100 representing how confident you are the change is safe to merge
- findings: a concise summary of what changed and whether it is correct and safe
- recommendations: any style, convention notes, or suggestions for improvement"""

    try:
        raw_result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"PR Diff:\n\n{state['pr_content']}"),
        ])
        review_dict = raw_result["parsed"].model_dump()
        usage = raw_result["raw"].usage_metadata or {}
    except Exception as e:
        review_dict = {"confidence": 0, "findings": f"[ERROR] {e}", "recommendations": ""}
        usage = {}

    return {
        "simple_review": json.dumps(review_dict),
        "tokens_used": {
            "input_tokens":  usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens":  usage.get("total_tokens", 0),
        },
        "messages": [f"[simple_review] complete (confidence: {review_dict.get('confidence')})"],
    }


# ------------------------------------------------------------------
# quality_analysis_node — Senior Developer agent
# ------------------------------------------------------------------
def quality_analysis_node(state: PRReviewState) -> dict:
    retry = state.get("quality_retry_count", 0)
    if retry > 0:
        system_prompt = """You are a Senior Developer performing a rigorous code quality review.
A previous review of this PR was rated insufficient. Be more thorough this time.

Analyse the PR diff and provide a detailed report covering:

1. STYLE ISSUES
   - Naming conventions, formatting, code organisation
   - PEP8 / language-standard violations

2. POTENTIAL BUGS
   - Logic errors, edge cases not handled, incorrect assumptions
   - Resource leaks, exception handling gaps

3. SEVERITY CLASSIFICATION
   - List each issue as CRITICAL, MAJOR, or MINOR
   - Critical = must fix before merge. Minor = nice-to-have.

Be specific. Reference line numbers or code snippets. Do not omit any issues."""
    else:
        system_prompt = """You are a Senior Developer performing a code quality review.

Analyse the PR diff and provide a structured report covering:

1. STYLE ISSUES
   - Naming conventions, formatting, code organisation
   - PEP8 / language-standard violations

2. POTENTIAL BUGS
   - Logic errors, edge cases not handled, incorrect assumptions
   - Resource leaks, exception handling gaps

3. SEVERITY CLASSIFICATION
   - List each issue as CRITICAL, MAJOR, or MINOR
   - Critical = must fix before merge. Minor = nice-to-have.

Be specific. Reference line numbers or code snippets where relevant."""

    if retry > 0:
        print(f"🔄 Quality Analysis retry {retry}/2 — using stricter prompt")

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"PR Diff to review:\n\n{state['pr_content']}"),
        ])
        content = response.content
        usage = response.usage_metadata or {}
    except Exception as e:
        content = f"[ERROR] LLM call failed: {e}"
        usage = {}

    return {
        "quality_findings": content,
        "tokens_used": {
            "input_tokens":  usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens":  usage.get("total_tokens", 0),
        },
        "messages": [f"[quality_analysis] complete ({len(content)} chars){' (retry)' if retry > 0 else ''}"],
    }


# ------------------------------------------------------------------
# security_review_node — Security Engineer agent
# ------------------------------------------------------------------
def security_review_node(state: PRReviewState) -> dict:
    system_prompt = """You are a Security Engineer performing a security review of a code change.

Analyse the PR diff and provide a structured security report covering:

1. VULNERABILITIES FOUND
   - Injection attacks (SQL, command, XSS)
   - Authentication / authorisation flaws
   - Sensitive data exposure (logging PII, plaintext secrets)
   - Insecure cryptography or hashing
   - Timing attacks and race conditions

2. RISK LEVELS
   - Rate each finding as HIGH, MEDIUM, or LOW risk
   - Explain the attack vector briefly

3. BLOCKING ISSUES
   - List any issues that MUST be fixed before this PR can merge
   - Conclude with: BLOCKING or NON-BLOCKING

Be precise. Reference specific lines or patterns in the diff."""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"PR Diff to review:\n\n{state['pr_content']}"),
        ])
        content = response.content
        usage = response.usage_metadata or {}
    except Exception as e:
        content = f"[ERROR] LLM call failed: {e}\n\nBLOCKING"
        usage = {}

    return {
        "security_findings": content,
        "tokens_used": {
            "input_tokens":  usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens":  usage.get("total_tokens", 0),
        },
        "messages": [f"[security_review] complete ({len(content)} chars)"],
    }


# ------------------------------------------------------------------
# quality_judge_node — LLM-as-Judge quality gate (gpt-4o-mini)
# ------------------------------------------------------------------
def quality_judge_node(state: PRReviewState) -> dict:
    structured_llm = judge_llm.with_structured_output(QualityJudgeOutput, include_raw=True)
    system_prompt = """You are a code review quality assessor.

Rate the thoroughness of the following code quality analysis on a scale of 1-10:
- 8-10: Comprehensive — covers style, bugs, severity levels, specific line references
- 5-7:  Adequate — covers main issues but lacks specificity or misses some areas
- 1-4:  Insufficient — too brief, vague, or misses obvious issues

Return a score (int 1-10) and a one-sentence reason."""

    try:
        raw_result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Quality analysis to evaluate:\n\n{state.get('quality_findings', '')}"),
        ])
        judge_out = raw_result["parsed"]
        usage = raw_result["raw"].usage_metadata or {}
        score  = judge_out.score
        reason = judge_out.reason
    except Exception as e:
        score  = 8   # default to proceed on error
        reason = f"[ERROR] Judge failed: {e} — defaulting to proceed"
        usage  = {}

    retry_count     = state.get("quality_retry_count", 0)
    new_retry_count = retry_count + 1 if score < 7 else retry_count

    if score >= 7:
        verdict = f"score={score}/10 — passed"
    elif new_retry_count <= 2:
        verdict = f"score={score}/10 — retry {new_retry_count}/2"
    else:
        verdict = f"score={score}/10 — retry cap reached, proceeding"

    print(f"⚖️  Quality Judge: {verdict}")

    return {
        "judge_score":           score,
        "judge_reason":          reason,
        "quality_retry_count":   new_retry_count,
        "tokens_used": {
            "input_tokens":  usage.get("input_tokens",  0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens":  usage.get("total_tokens",  0),
        },
        "messages": [f"[quality_judge] {verdict} — {reason[:80]}"],
    }


def quality_judge_edge(state: PRReviewState) -> str:
    """Routes to 'retry' (re-run quality_analysis) or 'proceed' (continue to aggregate)."""
    score       = state.get("judge_score") or 10
    retry_count = state.get("quality_retry_count") or 0
    if score < 7 and retry_count <= 2:
        return "retry"
    return "proceed"


# ------------------------------------------------------------------
# aggregate_node — fan-in join point (no-op)
# ------------------------------------------------------------------
def aggregate_node(state: PRReviewState) -> dict:
    return {}


# ------------------------------------------------------------------
# Guardrail edge functions
# ------------------------------------------------------------------
def output_guardrail(state: PRReviewState) -> str:
    findings = state.get("security_findings", "")
    if "BLOCKING" in findings.upper() and "NON-BLOCKING" not in findings.upper():
        return "block"
    return "proceed"


def report_guardrail(state: PRReviewState) -> str:
    return "complete"


# ------------------------------------------------------------------
# blocked_review_node — hard stop when guardrail fires
# ------------------------------------------------------------------
def blocked_review_node(state: PRReviewState) -> dict:
    verdict = (
        "REJECT\n\n"
        "This PR has been BLOCKED by the security output guardrail.\n"
        "Critical security issues were detected that must be resolved before merge.\n\n"
        f"Security Findings:\n{state.get('security_findings', '')}"
    )
    return {
        "summary": verdict,
        "messages": ["[blocked] Review halted by output guardrail — REJECT"],
    }


# ------------------------------------------------------------------
# summarize_findings_node — Tech Lead synthesis
# ------------------------------------------------------------------
def summarize_findings_node(state: PRReviewState) -> dict:
    structured_llm = llm.with_structured_output(SummarizeFindingsOutput, include_raw=True)
    system_prompt = """You are the Tech Lead making the final code review decision.

You have received reports from two reviewers. Synthesise them into a structured review:
- confidence: integer 0-100 reflecting overall confidence that the PR is safe to merge as-is
- findings: a 2-3 sentence executive summary of what the PR does and the overall quality/security posture
- fix: a list of specific, actionable items the author MUST address before merge (each item: issue, solution, explanation)
- recommendations: any additional observations or nice-to-have improvements"""

    user_message = (
        f"QUALITY ANALYSIS (Senior Developer):\n{state.get('quality_findings', 'No quality findings.')}"
        f"\n\n---\n\nSECURITY REVIEW (Security Engineer):\n{state.get('security_findings', 'No security findings.')}"
    )

    try:
        raw_result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ])
        summary_dict = raw_result["parsed"].model_dump()
        usage = raw_result["raw"].usage_metadata or {}
    except Exception as e:
        summary_dict = {"confidence": 0, "findings": f"[ERROR] {e}", "fix": [], "recommendations": ""}
        usage = {}

    return {
        "summary": json.dumps(summary_dict),
        "tokens_used": {
            "input_tokens":  usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens":  usage.get("total_tokens", 0),
        },
        "messages": [f"[tech_lead_summary] complete (confidence: {summary_dict.get('confidence')})"],
    }


# ------------------------------------------------------------------
# final_decision_node — extracts APPROVED / REQUEST CHANGES / REJECT
# ------------------------------------------------------------------
def final_decision_node(state: PRReviewState) -> dict:
    review_type = state.get("review_type", "unknown")
    if review_type == "simple":
        review_json = state.get("simple_review", "{}")
        label = "Simple Review"
    else:
        review_json = state.get("summary", "{}")
        label = "Full Code Review Tool"

    system_prompt = """You are a tech lead making the final merge decision on a pull request.

Given the review results below, output exactly one of:
  APPROVED          — safe to merge as-is
  REQUEST CHANGES   — mergeable after the listed fixes are applied
  REJECT            — critical issues; must not merge

Follow with 1-2 sentences explaining your reasoning."""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Review result ({label}):\n{review_json}"),
        ])
        decision_text = response.content
        usage = response.usage_metadata or {}
    except Exception as e:
        decision_text = f"REJECT\n\n[ERROR] Could not make final decision: {e}"
        usage = {}

    verdict = "UNKNOWN"
    for keyword in ("APPROVED", "REQUEST CHANGES", "REJECT"):
        if keyword in decision_text.upper():
            verdict = keyword
            break

    return {
        "final_decision": f"[{label}] {decision_text}",
        "tokens_used": {
            "input_tokens":  usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens":  usage.get("total_tokens", 0),
        },
        "messages": [f"[final_decision] {verdict}"],
    }


# ------------------------------------------------------------------
# return_final_answer — terminal display node
# ------------------------------------------------------------------
def return_final_answer(state: PRReviewState) -> dict:
    if state.get("errors"):
        for err in state["errors"]:
            print(f"❌ {err}")
    answer = state.get("final_decision") or "No decision reached."
    print("\n" + "=" * 60)
    print("FINAL ANSWER")
    print("=" * 60)
    print(answer)
    return {}


# ------------------------------------------------------------------
# full_review_start — fan-out trigger (no-op)
# ------------------------------------------------------------------
def full_review_start(state: PRReviewState) -> dict:
    return {}

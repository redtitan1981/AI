"""
test_nodes.py — Pytest test suite for the Code Review Tool.

Runs all node and reducer tests without graph compilation or LLM calls.
Each node is a pure function (state: dict) -> dict, so tests call them directly.

Usage:
    pytest test_nodes.py -v
"""
import pytest
from pathlib import Path

from state import FixItem, SimpleReviewOutput, SummarizeFindingsOutput, QualityJudgeOutput, merge_usage
from nodes import read_pr_file, routing_edge, output_guardrail, quality_judge_edge


# ---------------------------------------------------------------------------
# Shared base state (minimal valid PRReviewState)
# ---------------------------------------------------------------------------
BASE = {
    "pr_file_path": "",
    "pr_content": "",
    "review_type": "",
    "quality_findings": None,
    "security_findings": None,
    "summary": None,
    "simple_review": None,
    "final_decision": None,
    "quality_retry_count": 0,
    "judge_score": None,
    "judge_reason": None,
    "errors": [],
    "tokens_used": {},
    "messages": [],
}


# ---------------------------------------------------------------------------
# read_pr_file
# ---------------------------------------------------------------------------
class TestReadPrFile:
    def test_valid_file_populates_pr_content(self):
        result = read_pr_file({**BASE, "pr_file_path": "files/code_changes_simple.txt"})
        assert result.get("pr_content"), "pr_content should be non-empty"
        assert not result.get("errors"), "no errors expected for valid file"

    def test_missing_file_sets_errors(self):
        result = read_pr_file({**BASE, "pr_file_path": "files/does_not_exist.txt"})
        assert result.get("errors"), "errors should be set for missing file"
        assert "pr_content" not in result, "pr_content must not be set on error"

    def test_valid_file_returns_message(self):
        result = read_pr_file({**BASE, "pr_file_path": "files/code_changes_simple.txt"})
        assert result.get("messages"), "messages should be populated"


# ---------------------------------------------------------------------------
# routing_edge
# ---------------------------------------------------------------------------
class TestRoutingEdge:
    @pytest.mark.parametrize("review_type", ["simple", "full", "error"])
    def test_returns_correct_label(self, review_type):
        assert routing_edge({**BASE, "review_type": review_type}) == review_type


# ---------------------------------------------------------------------------
# output_guardrail
# ---------------------------------------------------------------------------
class TestOutputGuardrail:
    def test_blocking_returns_block(self):
        result = output_guardrail({**BASE, "security_findings": "SQL injection found. BLOCKING"})
        assert result == "block"

    def test_non_blocking_returns_proceed(self):
        result = output_guardrail({**BASE, "security_findings": "Minor issues only. NON-BLOCKING"})
        assert result == "proceed"

    def test_no_findings_returns_proceed(self):
        result = output_guardrail({**BASE, "security_findings": "No issues found."})
        assert result == "proceed"

    def test_empty_findings_returns_proceed(self):
        result = output_guardrail({**BASE, "security_findings": ""})
        assert result == "proceed"

    def test_non_blocking_keyword_takes_precedence(self):
        # "BLOCKING" appears inside "NON-BLOCKING" — should still proceed
        result = output_guardrail({**BASE, "security_findings": "All findings are NON-BLOCKING."})
        assert result == "proceed"


# ---------------------------------------------------------------------------
# merge_usage reducer
# ---------------------------------------------------------------------------
class TestMergeUsage:
    def test_sums_token_counts(self):
        a = {"input_tokens": 100, "output_tokens": 50,  "total_tokens": 150}
        b = {"input_tokens": 200, "output_tokens": 100, "total_tokens": 300}
        assert merge_usage(a, b) == {"input_tokens": 300, "output_tokens": 150, "total_tokens": 450}

    def test_handles_missing_keys_in_first(self):
        result = merge_usage({}, {"input_tokens": 50, "total_tokens": 50})
        assert result == {"input_tokens": 50, "total_tokens": 50}

    def test_handles_missing_keys_in_second(self):
        result = merge_usage({"input_tokens": 100}, {})
        assert result == {"input_tokens": 100}

    def test_empty_dicts(self):
        assert merge_usage({}, {}) == {}


# ---------------------------------------------------------------------------
# Pydantic output models
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# quality_judge_edge
# ---------------------------------------------------------------------------
class TestQualityJudgeEdge:
    def test_high_score_proceeds(self):
        assert quality_judge_edge({**BASE, "judge_score": 8, "quality_retry_count": 0}) == "proceed"

    def test_perfect_score_proceeds(self):
        assert quality_judge_edge({**BASE, "judge_score": 10, "quality_retry_count": 0}) == "proceed"

    def test_threshold_score_proceeds(self):
        assert quality_judge_edge({**BASE, "judge_score": 7, "quality_retry_count": 0}) == "proceed"

    def test_low_score_retries_when_under_cap(self):
        assert quality_judge_edge({**BASE, "judge_score": 4, "quality_retry_count": 1}) == "retry"

    def test_low_score_proceeds_when_cap_reached(self):
        assert quality_judge_edge({**BASE, "judge_score": 4, "quality_retry_count": 3}) == "proceed"

    def test_no_score_defaults_to_proceed(self):
        assert quality_judge_edge({**BASE, "judge_score": None, "quality_retry_count": 0}) == "proceed"


class TestPydanticModels:
    def test_fix_item_accepts_valid_fields(self):
        item = FixItem(
            issue="SQL injection in login query",
            solution="Use parameterised queries",
            explanation="Prevents arbitrary SQL execution by attackers",
        )
        assert item.issue == "SQL injection in login query"

    def test_fix_item_requires_all_fields(self):
        with pytest.raises(Exception):
            FixItem(issue="missing solution and explanation")

    def test_simple_review_output_valid(self):
        review = SimpleReviewOutput(confidence=85, findings="Minor rename", recommendations="None")
        assert review.confidence == 85

    def test_quality_judge_output_valid(self):
        judge = QualityJudgeOutput(score=8, reason="Comprehensive with line references")
        assert judge.score == 8

    def test_summarize_findings_output_with_fix_list(self):
        fix = FixItem(issue="X", solution="Y", explanation="Z")
        summary = SummarizeFindingsOutput(
            confidence=70,
            findings="Two issues found.",
            fix=[fix],
            recommendations="Add tests.",
        )
        assert len(summary.fix) == 1
        assert summary.fix[0].issue == "X"

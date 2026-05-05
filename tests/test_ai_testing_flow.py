from __future__ import annotations

import json

from orchestrator.ai_testing_flow import (
    run_failure_to_bug_report_flow,
    run_mobile_failure_to_bug_report_flow,
    run_requirement_to_script_flow,
)
from orchestrator.mobile_failure_classifier import MOBILE_DRIVER_ERROR
from orchestrator.root_cause_analysis import ENVIRONMENT_ISSUE, PRODUCT_BUG


def test_requirement_text_generates_normalized_requirement_test_cases_and_script():
    result = run_requirement_to_script_flow(
        """
# Login Requirement
Preconditions:
- User has a valid account
Business Flow:
- Enter username and password
- Submit login request
Acceptance Criteria:
- Valid credentials redirect the user to the dashboard.
""",
        source_id="REQ-LOGIN-001",
        source_name="auth.md",
    )

    assert result["normalized_requirement"]["requirement_id"] == "REQ-LOGIN-001"
    assert result["test_cases"]
    assert result["generated_script"]["script_type"] == "api_pytest"
    assert result["metadata"]["flow_type"] == "requirement_to_script"
    assert result["metadata"]["test_case_count"] == len(result["test_cases"])
    assert "def test_" in result["generated_script"]["script"]


def test_sparse_requirement_still_produces_safe_fallback_outputs():
    result = run_requirement_to_script_flow("", source_name="empty.md")

    assert result["normalized_requirement"]["title"] == "Untitled Requirement"
    assert result["test_cases"][0]["test_type"] == "fallback"
    assert result["warnings"]
    assert "missing_empty_input" in result["warnings"]
    assert "fallback_test_case_generated" in result["warnings"]
    assert len(result["generated_script"]["generated_test_names"]) == 1


def test_api_failure_context_produces_rca_and_bug_report():
    result = run_failure_to_bug_report_flow(
        failure_context={
            "test_name": "test_login_api",
            "source_file": "tests/test_login_api.py",
            "environment": "staging",
            "api_status_code": 503,
            "api_response_text": "service temporarily unavailable",
            "error_message": "AssertionError: expected 200, got 503",
        },
        evidence={"response_excerpt": "service temporarily unavailable"},
    )

    assert result["root_cause"]["root_cause_type"] == PRODUCT_BUG
    assert result["bug_report"]["root_cause_type"] == PRODUCT_BUG
    assert result["bug_report"]["severity"] == "High"
    assert result["metadata"]["flow_type"] == "failure_to_bug_report"
    assert result["metadata"]["has_evidence"] is True


def test_mobile_failed_artifact_produces_evidence_mobile_failure_rca_and_bug_report():
    result = run_mobile_failure_to_bug_report_flow(
        {
            "run_id": "run-driver",
            "passed": False,
            "stop_reason": "execution_error",
            "visited_screens": [],
            "executed_actions": [],
            "coverage_score": 0.0,
            "policy_shape": "nested",
            "error": "WebDriverException: Driver does not support opening detail screen.",
        },
        environment={"name": "android-emulator"},
    )

    assert result["mobile_evidence"]["run_id"] == "run-driver"
    assert result["mobile_failure"]["failure_type"] == MOBILE_DRIVER_ERROR
    assert result["root_cause"]["root_cause_type"] == ENVIRONMENT_ISSUE
    assert result["bug_report"]["root_cause_type"] == ENVIRONMENT_ISSUE
    assert "mobile-failure-signal" in result["bug_report"]["labels"]


def test_flow_outputs_are_json_serializable():
    requirement_flow = run_requirement_to_script_flow("# Search Requirement")
    failure_flow = run_failure_to_bug_report_flow(
        failure_context={
            "error_message": "requests.exceptions.ConnectTimeout: connect timeout",
            "pytest_log": "Temporary failure in name resolution",
            "environment": "ci",
        }
    )
    mobile_flow = run_mobile_failure_to_bug_report_flow(
        {
            "plugin": "mobile_exploration",
            "status": "failed",
            "run_id": "run-policy",
            "summary": {
                "stop_reason": "no_valid_action",
                "coverage_score": 0.4,
                "policy_shape": "nested",
                "visited_screen_count": 2,
                "executed_action_count": 1,
            },
            "artifact": {
                "run_id": "run-policy",
                "passed": False,
                "stop_reason": "no_valid_action",
                "visited_screens": ["AUTH_LOGIN", "CONTENT_LIST"],
                "executed_actions": ["submit_login"],
                "coverage_score": 0.4,
                "policy_shape": "nested",
                "started_at": "2026-01-01T00:00:00Z",
                "finished_at": "2026-01-01T00:00:01Z",
                "duration_ms": 1000,
                "error": "AssertionError: Unsupported navigation action: unsupported_recovery",
            },
        }
    )

    assert json.loads(json.dumps(requirement_flow)) == requirement_flow
    assert json.loads(json.dumps(failure_flow)) == failure_flow
    assert json.loads(json.dumps(mobile_flow)) == mobile_flow

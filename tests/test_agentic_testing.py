from __future__ import annotations

import json

from orchestrator.agentic_testing import (
    ANALYZE_FAILURE,
    ANALYZE_MOBILE_FAILURE,
    GENERATE_BUG_REPORT,
    GENERATE_SCRIPT,
    GENERATE_TEST_CASES,
    INGEST_REQUIREMENT,
    SKIP_WITH_REASON,
    SUGGEST_LOCATOR_HEALING,
    run_agentic_testing,
)
from orchestrator.mobile_failure_classifier import MOBILE_DRIVER_ERROR
from orchestrator.root_cause_analysis import ENVIRONMENT_ISSUE, PRODUCT_BUG, TEST_SCRIPT_ISSUE


def test_requirement_input_selects_and_generates_requirement_to_script_flow():
    result = run_agentic_testing(
        requirement_text="""
# Login Requirement
Business Flow:
- Enter username and password
- Submit login request
Acceptance Criteria:
- Valid credentials redirect the user to the dashboard.
""",
        source_id="REQ-LOGIN-001",
        mode="draft_artifacts",
    )

    assert result["status"] == "completed"
    assert result["selected_actions"] == [
        INGEST_REQUIREMENT,
        GENERATE_TEST_CASES,
        GENERATE_SCRIPT,
    ]
    assert result["artifacts"]["requirement_to_script"]["normalized_requirement"]["requirement_id"] == "REQ-LOGIN-001"
    assert result["artifacts"]["requirement_to_script"]["test_cases"]


def test_failure_input_selects_rca_and_bug_report():
    result = run_agentic_testing(
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

    assert ANALYZE_FAILURE in result["selected_actions"]
    assert GENERATE_BUG_REPORT in result["selected_actions"]
    assert result["artifacts"]["failure_to_bug_report"]["root_cause"]["root_cause_type"] == PRODUCT_BUG
    assert result["artifacts"]["failure_to_bug_report"]["bug_report"]["severity"] == "High"


def test_mobile_artifact_input_selects_mobile_evidence_failure_rca_and_bug_report():
    result = run_agentic_testing(
        mobile_artifact={
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

    assert ANALYZE_MOBILE_FAILURE in result["selected_actions"]
    assert ANALYZE_FAILURE in result["selected_actions"]
    assert GENERATE_BUG_REPORT in result["selected_actions"]
    assert result["artifacts"]["mobile_failure_to_bug_report"]["mobile_failure"]["failure_type"] == MOBILE_DRIVER_ERROR
    assert result["artifacts"]["mobile_failure_to_bug_report"]["root_cause"]["root_cause_type"] == ENVIRONMENT_ISSUE


def test_locator_payload_adds_self_healing_action_and_enriches_failure_analysis():
    result = run_agentic_testing(
        failure_context={
            "test_name": "test_login_button",
            "source_file": "tests/ui/test_login.py",
            "environment": "qa",
            "error_message": "Element not found while clicking the login button",
        },
        locator_failure_payload={
            "failed_locator": 'page.locator(".submit")',
            "error_message": "Element not found",
            "accessible_role": "button",
            "visible_text": "Sign in",
        },
    )

    assert SUGGEST_LOCATOR_HEALING in result["selected_actions"]
    assert result["artifacts"]["locator_healing"]["healing_applicable"] is True
    assert result["artifacts"]["failure_to_bug_report"]["root_cause"]["root_cause_type"] == TEST_SCRIPT_ISSUE


def test_plan_only_does_not_run_artifact_generation():
    result = run_agentic_testing(
        requirement_text="# Search Requirement",
        mode="plan_only",
    )

    assert result["status"] == "planned"
    assert result["artifacts"] == {}
    assert result["selected_actions"] == [
        INGEST_REQUIREMENT,
        GENERATE_TEST_CASES,
        GENERATE_SCRIPT,
    ]
    assert all(trace["executed"] is False for trace in result["decision_trace"])


def test_no_input_returns_skip_with_reason():
    result = run_agentic_testing()

    assert result["status"] == "skipped"
    assert result["selected_actions"] == [SKIP_WITH_REASON]
    assert result["artifacts"] == {}
    assert "no_actionable_input" in result["warnings"]


def test_output_is_json_serializable():
    result = run_agentic_testing(
        requirement_text="# Checkout Requirement",
        failure_context={
            "error_message": "AssertionError: expected 200, got 503",
            "api_status_code": 503,
        },
        locator_failure_payload={
            "failed_locator": 'page.locator("#checkout")',
            "error_message": "Element not found",
            "visible_text": "Checkout",
            "accessible_role": "button",
        },
    )

    assert json.loads(json.dumps(result)) == result

from __future__ import annotations

import json

from orchestrator.bug_report_generator import generate_bug_report
from orchestrator.locator_self_healing import suggest_locator_healing
from orchestrator.root_cause_analysis import (
    ENVIRONMENT_ISSUE,
    PRODUCT_BUG,
    TEST_SCRIPT_ISSUE,
    analyze_root_cause,
)


def test_product_bug_report_from_rca():
    rca_result = analyze_root_cause(
        {
            "api_status_code": 503,
            "api_response_text": "service temporarily unavailable",
            "error_message": "AssertionError: expected 200, got 503",
        }
    )

    result = generate_bug_report(
        {
            "test_name": "test_login_api",
            "source_file": "tests/test_login_api.py",
            "environment": "staging",
            "failure_context": {
                "error_message": "AssertionError: expected 200, got 503",
                "api_status_code": 503,
                "api_response_text": "service temporarily unavailable",
            },
            "rca_result": rca_result,
            "evidence": {"run_id": "RUN-123", "artifact_path": "artifacts/run-123.json"},
        }
    )

    assert result["root_cause_type"] == PRODUCT_BUG
    assert result["severity"] == "High"
    assert result["priority"] == "High"
    assert result["title"] == "[High][PRODUCT_BUG] test_login_api failure in staging"
    assert "application-side defect" in result["suspected_root_cause"]
    assert "root-cause-product-bug" in result["labels"]


def test_test_script_issue_report_from_locator_healing_rca():
    locator_result = suggest_locator_healing(
        {
            "failed_locator": 'page.locator(".submit")',
            "error_message": "Element not found",
            "accessible_role": "button",
            "visible_text": "Sign in",
        }
    )
    rca_result = analyze_root_cause({"locator_healing_result": locator_result})

    result = generate_bug_report(
        {
            "test_name": "test_login_button",
            "source_file": "tests/ui/test_login.py",
            "environment": {"name": "qa", "browser": "chromium"},
            "failure_context": {
                "error_message": "Element not found while clicking the login button",
                "locator_healing_result": locator_result,
            },
            "rca_result": rca_result,
            "evidence": {"locator_healing_result": locator_result},
        }
    )

    assert result["root_cause_type"] == TEST_SCRIPT_ISSUE
    assert result["severity"] == "Medium"
    assert result["priority"] == "Medium"
    assert "locator issue" in result["suspected_root_cause"]
    assert "locator-self-healing-signal" in result["labels"]


def test_environment_issue_report():
    rca_result = analyze_root_cause(
        {
            "error_message": "requests.exceptions.ConnectTimeout: connect timeout",
            "pytest_log": "Temporary failure in name resolution while reaching upstream service",
        }
    )

    result = generate_bug_report(
        {
            "test_name": "test_search_api",
            "environment": "ci",
            "failure_context": {
                "error_message": "requests.exceptions.ConnectTimeout: connect timeout",
            },
            "rca_result": rca_result,
            "evidence": {"pytest_log": "Temporary failure in name resolution"},
        }
    )

    assert result["root_cause_type"] == ENVIRONMENT_ISSUE
    assert result["severity"] == "Medium"
    assert result["priority"] == "Medium"
    assert "environment" in result["suspected_root_cause"].lower()


def test_sparse_input_fallback_is_safe():
    result = generate_bug_report({})

    assert result["root_cause_type"] == "UNKNOWN"
    assert result["severity"] == "Low"
    assert result["priority"] == "Low"
    assert result["steps_to_reproduce"]
    assert result["expected_result"]
    assert result["actual_result"]


def test_markdown_contains_required_sections():
    result = generate_bug_report(
        {
            "test_name": "test_checkout_api",
            "environment": "staging",
            "rca_result": {
                "root_cause_type": "PRODUCT_BUG",
                "severity": "high",
                "reason": "Checkout returned a 500 response.",
                "suggested_action": "Inspect backend checkout logs.",
                "signals": {"api_status_code": 500},
            },
        }
    )

    markdown = result["markdown"]

    assert "# Bug Title" in markdown
    assert "## Environment" in markdown
    assert "## Steps to Reproduce" in markdown
    assert "## Expected Result" in markdown
    assert "## Actual Result" in markdown
    assert "## Evidence" in markdown
    assert "## Suspected Root Cause" in markdown
    assert "## Suggested Action" in markdown


def test_output_is_json_serializable():
    rca_result = analyze_root_cause(
        {
            "api_status_code": 500,
            "api_response_text": "internal server error",
            "seen_count": 4,
        }
    )

    result = generate_bug_report(
        {
            "test_name": "test_known_backend_defect",
            "environment": {"name": "prod-shadow", "region": "ap-southeast-1"},
            "failure_context": {"api_status_code": 500},
            "rca_result": rca_result,
            "evidence": {"response_excerpt": "internal server error"},
        }
    )

    assert json.loads(json.dumps(result)) == result

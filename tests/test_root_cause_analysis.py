from __future__ import annotations

from orchestrator.locator_self_healing import suggest_locator_healing
from orchestrator.root_cause_analysis import (
    ENVIRONMENT_ISSUE,
    FLAKY_TEST,
    KNOWN_BACKEND_DEFECT,
    PRODUCT_BUG,
    TEST_DATA_ISSUE,
    TEST_SCRIPT_ISSUE,
    UNKNOWN,
    analyze_root_cause,
)


def test_locator_self_healing_result_maps_to_test_script_issue():
    locator_result = suggest_locator_healing(
        {
            "failed_locator": 'page.locator(".submit")',
            "error_message": "Element not found",
            "accessible_role": "button",
            "visible_text": "Sign in",
        }
    )

    result = analyze_root_cause({"locator_healing_result": locator_result})

    assert result["root_cause_type"] == TEST_SCRIPT_ISSUE
    assert result["likely_owner"] == "qa_automation"
    assert result["confidence"] >= 0.82


def test_5xx_api_failure_maps_to_product_bug():
    result = analyze_root_cause(
        {
            "api_status_code": 503,
            "api_response_text": "service temporarily unavailable",
            "error_message": "AssertionError: expected 200, got 503",
        }
    )

    assert result["root_cause_type"] == PRODUCT_BUG
    assert result["likely_owner"] == "backend_team"
    assert result["severity"] == "high"


def test_repeated_5xx_maps_to_known_backend_defect():
    result = analyze_root_cause(
        {
            "api_status_code": 500,
            "api_response_text": "internal server error",
            "seen_count": 4,
        }
    )

    assert result["root_cause_type"] == KNOWN_BACKEND_DEFECT
    assert result["likely_owner"] == "backend_team"


def test_network_timeout_maps_to_environment_issue():
    result = analyze_root_cause(
        {
            "error_message": "requests.exceptions.ConnectTimeout: connect timeout",
            "pytest_log": "Temporary failure in name resolution while reaching upstream service",
        }
    )

    assert result["root_cause_type"] == ENVIRONMENT_ISSUE
    assert result["likely_owner"] == "qa_infra"
    assert result["severity"] == "high"


def test_auth_or_test_data_issue_maps_to_test_data_issue():
    result = analyze_root_cause(
        {
            "api_status_code": 401,
            "api_response_text": "Unauthorized: token missing for seeded test account",
            "error_message": "Expected 200 but got 401",
        }
    )

    assert result["root_cause_type"] == TEST_DATA_ISSUE
    assert result["likely_owner"] == "qa_automation"


def test_flaky_score_maps_to_flaky_test():
    result = analyze_root_cause(
        {
            "error_message": "AssertionError: response body mismatch",
            "flaky_score": 0.91,
        }
    )

    assert result["root_cause_type"] == FLAKY_TEST
    assert result["likely_owner"] == "qa_automation"


def test_mobile_failure_signals_classify_correctly():
    result = analyze_root_cause(
        {
            "mobile_failure_type": "MOBILE_POLICY_UNSUPPORTED_ACTION",
            "evidence_summary": {"stop_reason": "no_valid_action"},
            "error_message": "unsupported action selected by policy",
        }
    )

    assert result["root_cause_type"] == TEST_SCRIPT_ISSUE
    assert result["likely_owner"] == "qa_policy"


def test_sparse_unknown_fallback():
    result = analyze_root_cause({})

    assert result["root_cause_type"] == UNKNOWN
    assert result["likely_owner"] == "qa_platform"
    assert result["confidence"] <= 0.3

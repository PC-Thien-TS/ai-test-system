from __future__ import annotations

from orchestrator.locator_self_healing import (
    LOCATOR_AMBIGUOUS,
    LOCATOR_NOT_FOUND,
    LOCATOR_NOT_VISIBLE,
    NON_LOCATOR_FAILURE,
    UNKNOWN,
    suggest_locator_healing,
)


def test_missing_locator_element_not_found_classification():
    result = suggest_locator_healing(
        {
            "failed_locator": 'page.locator("#missing-login-button")',
            "error_message": "Timeout exceeded while waiting for locator('#missing-login-button')",
        }
    )

    assert result["failure_type"] == LOCATOR_NOT_FOUND
    assert result["healing_applicable"] is False
    assert result["original_locator"] == 'page.locator("#missing-login-button")'


def test_role_and_text_candidate_generation():
    result = suggest_locator_healing(
        {
            "failed_locator": 'page.locator(".submit")',
            "error_message": "Element not found",
            "accessible_role": "button",
            "visible_text": "Sign in",
        }
    )

    assert result["failure_type"] == LOCATOR_NOT_FOUND
    assert result["healing_applicable"] is True
    assert result["recommended_locator"] == 'page.get_by_role("button", name="Sign in")'
    assert any(candidate["strategy"] == "get_by_role" for candidate in result["candidate_locators"])


def test_label_based_candidate_generation():
    result = suggest_locator_healing(
        {
            "failed_locator": 'page.locator("input[name=email]")',
            "error_message": "No such element: unable to locate element",
            "nearby_text": "Email address",
        }
    )

    assert result["failure_type"] == LOCATOR_NOT_FOUND
    assert result["healing_applicable"] is True
    assert any(candidate["locator"] == 'page.get_by_label("Email address")' for candidate in result["candidate_locators"])


def test_test_id_extraction_from_dom_snapshot():
    result = suggest_locator_healing(
        {
            "failed_locator": 'page.locator(".login-button")',
            "error_message": "Element not found",
            "dom_snapshot": '<button data-testid="login-submit">Sign in</button><div test-id="secondary-action"></div>',
            "visible_text": "Sign in",
            "test_name": "test_login_submit",
        }
    )

    assert result["healing_applicable"] is True
    assert any(candidate["strategy"] == "get_by_test_id" for candidate in result["candidate_locators"])
    assert 'page.get_by_test_id("login-submit")' in [candidate["locator"] for candidate in result["candidate_locators"]]


def test_non_locator_failure_returns_not_applicable():
    result = suggest_locator_healing(
        {
            "failed_locator": 'page.locator("#login")',
            "error_message": "AssertionError: Expected status code 200 but got 500",
        }
    )

    assert result["failure_type"] == NON_LOCATOR_FAILURE
    assert result["healing_applicable"] is False
    assert result["candidate_locators"] == []


def test_sparse_input_fallback_is_safe():
    result = suggest_locator_healing({})

    assert result["failure_type"] == UNKNOWN
    assert result["healing_applicable"] is False
    assert result["candidate_locators"] == []
    assert result["recommended_locator"] == ""

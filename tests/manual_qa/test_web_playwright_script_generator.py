from __future__ import annotations

import pytest

from orchestrator.manual_qa.models import ManualTestCase, WebPlaywrightReadiness
from orchestrator.manual_qa.web_playwright_script_generator import WebPlaywrightScriptGenerator


def _web_case(
    *,
    test_case_id: str = "TC-901",
    title: str = "Login page submit flow",
    steps: list[str] | None = None,
    expected_result: str = "User should see dashboard and URL contains /dashboard.",
) -> ManualTestCase:
    return ManualTestCase(
        test_case_id=test_case_id,
        requirement_ids=["REQ-901"],
        module="Portal UI",
        title=title,
        steps=steps
        or [
            "Navigate to /login page.",
            "Fill data-testid=login-email with valid email.",
            "Fill data-testid=login-password with valid password.",
            "Click button text sign in.",
        ],
        expected_result=expected_result,
        priority="High",
        test_type="Positive",
    )


def _readiness(
    *,
    test_case_id: str = "TC-901",
    readiness_status: str = "Ready",
    page_url: str = "/login",
    selector_hints: list[str] | None = None,
    action_hints: list[str] | None = None,
    assertion_hints: list[str] | None = None,
) -> WebPlaywrightReadiness:
    return WebPlaywrightReadiness(
        readiness_id="WPREAD-001",
        test_case_id=test_case_id,
        requirement_ids=["REQ-901"],
        module="Portal UI",
        title="Login page submit flow",
        readiness_status=readiness_status,
        readiness_score=85,
        page_url=page_url,
        selector_hints=selector_hints
        if selector_hints is not None
        else ["data-testid=login-email", "data-testid=login-password", "button text sign in"],
        action_hints=action_hints if action_hints is not None else ["fill", "click"],
        assertion_hints=assertion_hints if assertion_hints is not None else ["url contains"],
        strengths=["Selectors present"],
        suggested_next_step="Proceed to Playwright script draft generation",
    )


def test_generates_playwright_draft_for_clear_web_ui_case():
    generator = WebPlaywrightScriptGenerator()

    draft = generator.generate_web_playwright_script_draft(_web_case(), readiness=_readiness())

    assert draft.framework == "playwright-python"
    assert draft.language == "python"
    assert draft.metadata["page_url"] == "/login"
    assert "from playwright.sync_api import Page, expect" in draft.script_content
    assert 'page.goto(f"{BASE_URL}/login")' in draft.script_content
    assert 'page.get_by_test_id("login-email").fill("TODO_VALUE")' in draft.script_content
    assert "expect(page).to_have_url" in draft.script_content


def test_uses_todo_page_url_and_warning_when_url_missing():
    generator = WebPlaywrightScriptGenerator()

    draft = generator.generate_web_playwright_script_draft(
        _web_case(steps=["Fill field label Email.", "Click button text sign in."]),
        readiness=_readiness(page_url=""),
    )

    assert draft.metadata["page_url"] == "/TODO_PAGE_URL"
    assert any("Page URL not detected" in item for item in draft.warnings)
    assert "/TODO_PAGE_URL" in draft.script_content


def test_uses_todo_selector_and_warning_when_selector_missing():
    generator = WebPlaywrightScriptGenerator()

    draft = generator.generate_web_playwright_script_draft(
        _web_case(
            steps=[
                "Navigate to /login page.",
                "Submit the form.",
            ],
            expected_result="User should see dashboard and URL contains /dashboard.",
        ),
        readiness=_readiness(selector_hints=[]),
    )

    assert draft.metadata["selector_hints"] == ["TODO_SELECTOR"]
    assert any("Selector hints not detected" in item for item in draft.warnings)
    assert 'page.locator("TODO_SELECTOR")' in draft.script_content


def test_uses_todo_assertion_and_warning_when_assertion_missing():
    generator = WebPlaywrightScriptGenerator()

    draft = generator.generate_web_playwright_script_draft(
        _web_case(
            steps=["Navigate to /login page.", "Click button text sign in."],
            expected_result="User completes the flow.",
        ),
        readiness=_readiness(assertion_hints=[]),
    )

    assert any("Assertion hints not detected" in item for item in draft.warnings)
    assert "# TODO: refine assertion from expected result." in draft.script_content


def test_rejects_not_suitable_readiness():
    generator = WebPlaywrightScriptGenerator()

    with pytest.raises(ValueError, match="not suitable"):
        generator.generate_web_playwright_script_draft(
            _web_case(),
            readiness=_readiness(readiness_status="Not Suitable"),
        )


def test_preserves_test_case_id_and_requirement_ids():
    generator = WebPlaywrightScriptGenerator()
    test_case = ManualTestCase(
        test_case_id="TC-990",
        requirement_ids=["REQ-100", "REQ-101"],
        module="Portal UI",
        title="Dashboard navigation",
        steps=["Navigate to /dashboard page.", "Click #save-button."],
        expected_result="Element visible.",
    )
    readiness = WebPlaywrightReadiness(
        readiness_id="WPREAD-123",
        test_case_id="TC-990",
        requirement_ids=["REQ-100", "REQ-101"],
        module="Portal UI",
        title="Dashboard navigation",
        readiness_status="Ready",
        readiness_score=80,
        page_url="/dashboard",
        selector_hints=["#save-button"],
        action_hints=["click"],
        assertion_hints=["element visible"],
    )

    draft = generator.generate_web_playwright_script_draft(test_case, readiness=readiness)

    assert draft.test_case_id == "TC-990"
    assert draft.requirement_ids == ["REQ-100", "REQ-101"]
    assert draft.readiness_id == "WPREAD-123"


def test_generated_script_includes_draft_only_not_executed_warning():
    generator = WebPlaywrightScriptGenerator()

    draft = generator.generate_web_playwright_script_draft(_web_case(), readiness=_readiness())

    assert "Draft only. Not executed / not verified." in draft.script_content
    assert "Manual QA Playwright draft only. Not executed by the generator." in draft.script_content


def test_generated_script_is_deterministic():
    test_case = _web_case()
    readiness = _readiness()

    draft_one = WebPlaywrightScriptGenerator().generate_web_playwright_script_draft(test_case, readiness=readiness)
    draft_two = WebPlaywrightScriptGenerator().generate_web_playwright_script_draft(test_case, readiness=readiness)

    assert draft_one.to_dict() == draft_two.to_dict()


def test_batch_generation_preserves_input_order_for_eligible_cases():
    generator = WebPlaywrightScriptGenerator()
    cases = [
        _web_case(test_case_id="TC-910", title="Login page submit flow"),
        _web_case(
            test_case_id="TC-911",
            title="Search page filter flow",
            steps=[
                "Navigate to /search page.",
                "Fill field label Search with valid text.",
                "Click button text search.",
            ],
            expected_result="User should see results and URL contains /search.",
        ),
    ]
    readiness_items = [
        _readiness(test_case_id="TC-910"),
        _readiness(
            test_case_id="TC-911",
            page_url="/search",
            selector_hints=["field label search", "button text search"],
        ),
    ]

    drafts = generator.generate_web_playwright_script_drafts(cases, readiness_items=readiness_items)

    assert [item.test_case_id for item in drafts] == ["TC-910", "TC-911"]


def test_no_playwright_execution_or_browser_launch_occurs():
    generator = WebPlaywrightScriptGenerator()

    draft = generator.generate_web_playwright_script_draft(_web_case(), readiness=_readiness())

    assert draft.status == "Draft"
    assert "playwright.sync_api" in draft.script_content
    assert "browser.launch" not in draft.script_content
    assert "sync_playwright()" not in draft.script_content

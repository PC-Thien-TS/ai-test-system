from __future__ import annotations

from orchestrator.manual_qa.models import WebPlaywrightScriptDraft
from orchestrator.manual_qa.web_playwright_script_generator import WebPlaywrightScriptGenerator
from orchestrator.manual_qa.web_playwright_validation_service import WebPlaywrightValidationService
from tests.manual_qa.test_web_playwright_script_generator import _readiness, _web_case


def _draft(
    script_content: str,
    *,
    draft_id: str = "WEB-DRAFT-001",
    file_name: str = "test_demo.py",
) -> WebPlaywrightScriptDraft:
    return WebPlaywrightScriptDraft(
        draft_id=draft_id,
        test_case_id="TC-001",
        requirement_ids=["REQ-001"],
        module="Portal UI",
        title="Web draft",
        readiness_id="WPREAD-001",
        file_name=file_name,
        script_content=script_content,
    )


def _generated_draft() -> WebPlaywrightScriptDraft:
    return WebPlaywrightScriptGenerator().generate_web_playwright_script_draft(
        _web_case(),
        readiness=_readiness(),
    )


def test_validates_syntactically_valid_playwright_draft():
    service = WebPlaywrightValidationService()

    result = service.validate_web_playwright_script_draft(_generated_draft())

    assert result.is_valid is True
    assert result.syntax_valid is True
    assert result.has_playwright_import is True
    assert result.has_test_function is True


def test_detects_syntax_error():
    service = WebPlaywrightValidationService()
    draft = _draft("def test_bad(:\n    pass\n")

    result = service.validate_web_playwright_script_draft(draft)

    assert result.is_valid is False
    assert result.syntax_valid is False
    assert any(issue.issue_type == "syntax_error" for issue in result.issues)


def test_detects_missing_draft_marker():
    service = WebPlaywrightValidationService()
    draft = _draft(
        'import os\nfrom playwright.sync_api import Page, expect\nBASE_URL = "x"\n\ndef test_ok(page: Page):\n    page.goto(BASE_URL)\n    expect(page).to_have_url(BASE_URL)\n'
    )

    result = service.validate_web_playwright_script_draft(draft)

    assert result.is_valid is False
    assert any(issue.issue_type == "missing_draft_marker" for issue in result.issues)


def test_detects_missing_no_execution_marker():
    service = WebPlaywrightValidationService()
    draft = _draft(
        'import os\nfrom playwright.sync_api import Page, expect\nBASE_URL = "x"\n\ndef test_ok(page: Page):\n    """Draft only."""\n    page.goto(BASE_URL)\n    expect(page).to_have_url(BASE_URL)\n'
    )

    result = service.validate_web_playwright_script_draft(draft)

    assert result.is_valid is False
    assert any(issue.issue_type == "missing_no_execution_marker" for issue in result.issues)


def test_detects_missing_playwright_import():
    service = WebPlaywrightValidationService()
    draft = _draft(
        'import os\nBASE_URL = "x"\n\ndef test_ok(page):\n    """Draft only. Not executed."""\n    page.goto(BASE_URL)\n    expect(page).to_have_url(BASE_URL)\n'
    )

    result = service.validate_web_playwright_script_draft(draft)

    assert result.is_valid is False
    assert any(issue.issue_type == "missing_playwright_import" for issue in result.issues)


def test_detects_missing_test_function():
    service = WebPlaywrightValidationService()
    draft = _draft(
        'import os\nfrom playwright.sync_api import Page, expect\nBASE_URL = "x"\npage.goto(BASE_URL)\n'
    )

    result = service.validate_web_playwright_script_draft(draft)

    assert result.is_valid is False
    assert any(issue.issue_type == "missing_test_function" for issue in result.issues)


def test_detects_missing_page_goto():
    service = WebPlaywrightValidationService()
    draft = _draft(
        'import os\nfrom playwright.sync_api import Page, expect\nBASE_URL = "x"\n\ndef test_ok(page: Page):\n    """Draft only. Not executed."""\n    expect(page).to_have_url(BASE_URL)\n'
    )

    result = service.validate_web_playwright_script_draft(draft)

    assert any(issue.issue_type == "missing_page_goto" for issue in result.issues)


def test_detects_todo_page_url_as_warning():
    service = WebPlaywrightValidationService()
    draft = _generated_draft()
    draft.script_content = draft.script_content.replace('/login', '/TODO_PAGE_URL')

    result = service.validate_web_playwright_script_draft(draft)

    assert result.has_todo_page_url is True
    assert any(issue.issue_type == "todo_page_url" for issue in result.issues)


def test_detects_todo_selector_as_warning():
    service = WebPlaywrightValidationService()
    draft = _generated_draft()
    draft.script_content = draft.script_content.replace('page.get_by_test_id("login-email")', 'page.locator("TODO_SELECTOR")')

    result = service.validate_web_playwright_script_draft(draft)

    assert result.has_todo_selector is True
    assert any(issue.issue_type == "todo_selector" for issue in result.issues)


def test_detects_todo_assertion_as_warning():
    service = WebPlaywrightValidationService()
    draft = _draft(
        'import os\nfrom playwright.sync_api import Page, expect\nBASE_URL = "x"\n\ndef test_ok(page: Page):\n    """Draft only. Not executed."""\n    page.goto(BASE_URL)\n    page.locator("TODO_SELECTOR").click()\n    # TODO: refine assertion from expected result.\n'
    )

    result = service.validate_web_playwright_script_draft(draft)

    assert result.has_todo_assertion is True
    assert any(issue.issue_type == "todo_assertion" for issue in result.issues)


def test_detects_missing_assertion_or_todo_marker():
    service = WebPlaywrightValidationService()
    draft = _draft(
        'import os\nfrom playwright.sync_api import Page, expect\nBASE_URL = "x"\n\ndef test_ok(page: Page):\n    """Draft only. Not executed."""\n    page.goto(BASE_URL)\n    page.locator("#login").click()\n'
    )

    result = service.validate_web_playwright_script_draft(draft)

    assert any(issue.issue_type == "missing_assertion_or_todo" for issue in result.issues)


def test_does_not_execute_script_content_or_launch_browser():
    service = WebPlaywrightValidationService()
    draft = _draft(
        "import os\nfrom playwright.sync_api import Page, expect\nBASE_URL='x'\n\n"
        "def test_side_effect(page: Page):\n"
        "    '''Draft only. Not executed.'''\n"
        "    page.goto(BASE_URL)\n"
        "    expect(page).to_have_url(BASE_URL)\n"
    )

    result = service.validate_web_playwright_script_draft(draft)

    assert result.is_valid is True
    assert result.has_playwright_import is True


def test_batch_validation_preserves_input_order():
    service = WebPlaywrightValidationService()
    drafts = [
        _generated_draft(),
        _draft(
            'import os\nfrom playwright.sync_api import Page, expect\nBASE_URL = "x"\n\ndef test_other(page: Page):\n    """Draft only. Not executed."""\n    page.goto(BASE_URL)\n    page.locator("#save").click()\n    expect(page).to_have_url(BASE_URL)\n',
            draft_id="WEB-DRAFT-002",
            file_name="test_other.py",
        ),
    ]

    results = service.validate_web_playwright_script_drafts(drafts)

    assert [item.draft_id for item in results] == ["WEB-DRAFT-001", "WEB-DRAFT-002"]

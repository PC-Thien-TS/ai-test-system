from __future__ import annotations

from orchestrator.manual_qa.models import WebPlaywrightScriptDraft
from orchestrator.manual_qa.web_playwright_packaging_service import WebPlaywrightPackagingService
from orchestrator.manual_qa.web_playwright_validation_service import WebPlaywrightValidationService


def _draft(draft_id: str, file_name: str, script_content: str) -> WebPlaywrightScriptDraft:
    return WebPlaywrightScriptDraft(
        draft_id=draft_id,
        test_case_id=f"TC-{draft_id[-3:]}",
        requirement_ids=["REQ-001"],
        module="Portal UI",
        title="Draft",
        file_name=file_name,
        script_content=script_content,
    )


def _valid_script() -> str:
    return (
        'import os\nfrom playwright.sync_api import Page, expect\nBASE_URL = os.getenv("WEB_BASE_URL", "http://localhost")\n\n'
        'def test_ok(page: Page):\n'
        '    """Draft only. Not executed."""\n'
        '    page.goto(BASE_URL)\n'
        '    page.locator("#login").click()\n'
        '    expect(page).to_have_url(BASE_URL)\n'
    )


def test_builds_package_manifest_from_drafts_and_validation_results():
    validator = WebPlaywrightValidationService()
    packager = WebPlaywrightPackagingService()
    drafts = [_draft("WEB-DRAFT-001", "test_one.py", _valid_script())]
    results = validator.validate_web_playwright_script_drafts(drafts)

    manifest = packager.build_web_playwright_package(
        drafts,
        results,
        validation_report_files=["script_drafts/web_playwright/web_playwright_validation.json"],
    )

    assert manifest.package_name == "web-playwright-script-drafts"
    assert manifest.draft_count == 1
    assert manifest.draft_files == ["test_one.py"]
    assert manifest.validation_report_files == ["script_drafts/web_playwright/web_playwright_validation.json"]


def test_counts_valid_invalid_warnings_correctly():
    validator = WebPlaywrightValidationService()
    packager = WebPlaywrightPackagingService()
    drafts = [
        _draft("WEB-DRAFT-001", "test_one.py", _valid_script()),
        _draft(
            "WEB-DRAFT-002",
            "test_two.py",
            _valid_script().replace('page.locator("#login")', 'page.locator("TODO_SELECTOR")'),
        ),
        _draft("WEB-DRAFT-003", "test_three.py", "def test_bad(:\n    pass\n"),
    ]
    results = validator.validate_web_playwright_script_drafts(drafts)

    manifest = packager.build_web_playwright_package(drafts, results)

    assert manifest.valid_count == 2
    assert manifest.invalid_count == 1
    assert manifest.warning_count >= 1


def test_status_ready_for_review_when_no_errors_or_warnings():
    validator = WebPlaywrightValidationService()
    packager = WebPlaywrightPackagingService()
    drafts = [_draft("WEB-DRAFT-001", "test_one.py", _valid_script())]
    results = validator.validate_web_playwright_script_drafts(drafts)

    manifest = packager.build_web_playwright_package(drafts, results)

    assert manifest.status == "Ready for Review"


def test_status_needs_attention_when_warnings_exist():
    validator = WebPlaywrightValidationService()
    packager = WebPlaywrightPackagingService()
    drafts = [
        _draft(
            "WEB-DRAFT-001",
            "test_one.py",
            _valid_script().replace('page.locator("#login")', 'page.locator("TODO_SELECTOR")'),
        )
    ]
    results = validator.validate_web_playwright_script_drafts(drafts)

    manifest = packager.build_web_playwright_package(drafts, results)

    assert manifest.status == "Needs Attention"


def test_status_invalid_when_errors_exist():
    validator = WebPlaywrightValidationService()
    packager = WebPlaywrightPackagingService()
    drafts = [_draft("WEB-DRAFT-001", "test_bad.py", "def test_bad(:\n    pass\n")]
    results = validator.validate_web_playwright_script_drafts(drafts)

    manifest = packager.build_web_playwright_package(drafts, results)

    assert manifest.status == "Invalid"


def test_does_not_zip_or_execute_files():
    validator = WebPlaywrightValidationService()
    packager = WebPlaywrightPackagingService()
    drafts = [_draft("WEB-DRAFT-001", "test_one.py", _valid_script())]
    results = validator.validate_web_playwright_script_drafts(drafts)

    manifest = packager.build_web_playwright_package(drafts, results)

    assert ".zip" not in "".join(manifest.draft_files)
    assert manifest.metadata["all_syntax_valid"] is True

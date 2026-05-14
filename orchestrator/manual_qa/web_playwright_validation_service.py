"""Static validation for Web Playwright script draft artifacts."""

from __future__ import annotations

import ast
import re
from datetime import datetime, timedelta
from typing import Sequence

from orchestrator.manual_qa.models import (
    WebPlaywrightScriptDraft,
    WebPlaywrightValidationIssue,
    WebPlaywrightValidationResult,
)


class WebPlaywrightValidationService:
    """Validate generated Web Playwright drafts without executing them."""

    _BASE_TIME = datetime(2024, 1, 13, 0, 0, 0)
    _ACTION_PATTERN = re.compile(
        r"\.(click|fill|select_option|check|uncheck|hover|set_input_files)\s*\("
    )

    def __init__(self) -> None:
        self._next_validation_number = 1
        self._next_issue_number = 1
        self._next_timestamp_offset = 0

    def validate_web_playwright_script_draft(
        self,
        draft: WebPlaywrightScriptDraft,
    ) -> WebPlaywrightValidationResult:
        content = draft.script_content or ""
        issues: list[WebPlaywrightValidationIssue] = []

        syntax_valid = True
        try:
            ast.parse(content)
        except SyntaxError as exc:
            syntax_valid = False
            issues.append(
                self._issue(
                    draft,
                    severity="Error",
                    issue_type="syntax_error",
                    message=f"Python syntax error: {exc.msg}",
                    recommendation="Fix the generated Playwright draft syntax before review or packaging.",
                    metadata={"line": exc.lineno, "offset": exc.offset},
                )
            )

        has_draft_warning = self._contains_any(
            content,
            ("draft only", "manual qa playwright script draft", "manual qa playwright draft only"),
        )
        if not has_draft_warning:
            issues.append(
                self._issue(
                    draft,
                    severity="Error",
                    issue_type="missing_draft_marker",
                    message="Draft marker is missing from the Playwright draft content.",
                    recommendation="Add an explicit Draft only marker to prevent misuse.",
                )
            )

        has_no_execution_marker = self._contains_any(content, ("not executed", "not verified"))
        if not has_no_execution_marker:
            issues.append(
                self._issue(
                    draft,
                    severity="Error",
                    issue_type="missing_no_execution_marker",
                    message="No explicit no-execution marker was found in the Playwright draft.",
                    recommendation="Add a Not executed marker to clarify that the draft has not been run.",
                )
            )

        has_playwright_import = bool(
            re.search(
                r"from\s+playwright\.sync_api\s+import\s+.*Page.*expect|from\s+playwright\.sync_api\s+import\s+.*expect.*Page",
                content,
            )
        )
        if not has_playwright_import:
            issues.append(
                self._issue(
                    draft,
                    severity="Error",
                    issue_type="missing_playwright_import",
                    message="The draft does not include the expected Playwright import.",
                    recommendation="Add a safe Playwright sync API import such as `from playwright.sync_api import Page, expect`.",
                )
            )

        has_test_function = bool(re.search(r"def\s+test_[a-z0-9_]+\s*\([^)]*\)\s*:", content))
        if not has_test_function:
            issues.append(
                self._issue(
                    draft,
                    severity="Error",
                    issue_type="missing_test_function",
                    message="No pytest-style Playwright test function was detected.",
                    recommendation="Add at least one `def test_*` function before packaging.",
                )
            )

        has_page_goto = "page.goto(" in content
        if not has_page_goto:
            issues.append(
                self._issue(
                    draft,
                    severity="Error",
                    issue_type="missing_page_goto",
                    message="No `page.goto(...)` navigation step was detected.",
                    recommendation="Add `page.goto(...)` or an explicit TODO page navigation marker before packaging.",
                )
            )

        has_locator_or_todo = bool(
            re.search(r"page\.(get_by_test_id|get_by_role|get_by_label|locator)\(", content)
            or "TODO_SELECTOR" in content
        )
        if not has_locator_or_todo:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="missing_locator_or_todo",
                    message="No locator usage or TODO selector marker was detected.",
                    recommendation="Add a stable locator or TODO selector placeholder before packaging.",
                )
            )

        has_action_or_todo = bool(self._ACTION_PATTERN.search(content) or "TODO: identify the submit control" in content)
        if not has_action_or_todo:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="missing_action_or_todo",
                    message="No supported Playwright action or TODO action marker was detected.",
                    recommendation="Add an interaction call such as click/fill/select_option or a TODO action marker.",
                )
            )

        has_assertion_or_todo = bool("expect(" in content or "TODO: refine assertion" in content)
        if not has_assertion_or_todo:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="missing_assertion_or_todo",
                    message="No assertion or TODO assertion marker was detected.",
                    recommendation="Add an `expect(...)` assertion or explicit TODO assertion marker.",
                )
            )

        has_todo_page_url = "TODO_PAGE_URL" in content
        if has_todo_page_url:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="todo_page_url",
                    message="The draft still contains a TODO page URL placeholder.",
                    recommendation="Replace the TODO page URL with a real route before review.",
                )
            )

        has_todo_selector = "TODO_SELECTOR" in content
        if has_todo_selector:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="todo_selector",
                    message="The draft still contains a TODO selector placeholder.",
                    recommendation="Replace the TODO selector with a stable locator before review.",
                )
            )

        has_todo_assertion = "TODO: refine assertion" in content or "TODO_ASSERTION_URL" in content
        if has_todo_assertion:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="todo_assertion",
                    message="The draft still contains a TODO assertion placeholder.",
                    recommendation="Replace the TODO assertion with a concrete expected UI check before review.",
                )
            )

        has_base_url = "BASE_URL" in content
        if not has_base_url:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="missing_base_url",
                    message="BASE_URL variable was not detected in the Playwright draft.",
                    recommendation="Add BASE_URL configuration so the draft stays environment-agnostic.",
                )
            )

        error_count = len([item for item in issues if item.severity == "Error"])
        warning_count = len([item for item in issues if item.severity == "Warning"])
        is_valid = (
            syntax_valid
            and has_draft_warning
            and has_no_execution_marker
            and has_playwright_import
            and has_test_function
        )

        result = WebPlaywrightValidationResult(
            validation_id=f"WPVAL-{self._next_validation_number:03d}",
            draft_id=draft.draft_id,
            test_case_id=draft.test_case_id,
            file_name=draft.file_name,
            is_valid=is_valid,
            syntax_valid=syntax_valid,
            has_draft_warning=has_draft_warning,
            has_no_execution_marker=has_no_execution_marker,
            has_playwright_import=has_playwright_import,
            has_test_function=has_test_function,
            has_page_goto=has_page_goto,
            has_locator_or_todo=has_locator_or_todo,
            has_action_or_todo=has_action_or_todo,
            has_assertion_or_todo=has_assertion_or_todo,
            has_todo_page_url=has_todo_page_url,
            has_todo_selector=has_todo_selector,
            has_todo_assertion=has_todo_assertion,
            issues=issues,
            metadata={
                "warning_count": warning_count,
                "error_count": error_count,
                "base_url_detected": has_base_url,
            },
            created_at=self._next_timestamp(),
        )
        self._next_validation_number += 1
        return result

    def validate_web_playwright_script_drafts(
        self,
        drafts: Sequence[WebPlaywrightScriptDraft],
    ) -> list[WebPlaywrightValidationResult]:
        return [self.validate_web_playwright_script_draft(draft) for draft in drafts]

    def _issue(
        self,
        draft: WebPlaywrightScriptDraft,
        *,
        severity: str,
        issue_type: str,
        message: str,
        recommendation: str,
        metadata: dict | None = None,
    ) -> WebPlaywrightValidationIssue:
        issue = WebPlaywrightValidationIssue(
            issue_id=f"WPVI-{self._next_issue_number:03d}",
            draft_id=draft.draft_id,
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            metadata=dict(metadata or {}),
        )
        self._next_issue_number += 1
        return issue

    def _contains_any(self, content: str, phrases: Sequence[str]) -> bool:
        lowered = content.lower()
        return any(phrase.lower() in lowered for phrase in phrases)

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_WEB_PLAYWRIGHT_VALIDATION_SERVICE = WebPlaywrightValidationService()


def validate_web_playwright_script_draft(
    draft: WebPlaywrightScriptDraft,
) -> WebPlaywrightValidationResult:
    """Convenience wrapper for validating a single Web Playwright draft artifact."""

    return _DEFAULT_WEB_PLAYWRIGHT_VALIDATION_SERVICE.validate_web_playwright_script_draft(draft)


def validate_web_playwright_script_drafts(
    drafts: Sequence[WebPlaywrightScriptDraft],
) -> list[WebPlaywrightValidationResult]:
    """Convenience wrapper for validating Web Playwright draft artifacts in input order."""

    return _DEFAULT_WEB_PLAYWRIGHT_VALIDATION_SERVICE.validate_web_playwright_script_drafts(drafts)

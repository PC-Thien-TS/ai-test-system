"""Static validation for API script draft artifacts."""

from __future__ import annotations

import ast
import re
from datetime import datetime, timedelta
from typing import Sequence

from orchestrator.manual_qa.models import (
    APIScriptValidationIssue,
    APIScriptValidationResult,
    APITestScriptDraft,
)


class APIScriptValidationService:
    """Validate generated API drafts without executing them."""

    _BASE_TIME = datetime(2024, 1, 9, 0, 0, 0)

    def __init__(self) -> None:
        self._next_validation_number = 1
        self._next_issue_number = 1
        self._next_timestamp_offset = 0

    def validate_api_script_draft(self, draft: APITestScriptDraft) -> APIScriptValidationResult:
        content = draft.script_content or ""
        issues: list[APIScriptValidationIssue] = []

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
                    recommendation="Fix the generated script syntax before review or packaging.",
                    metadata={"line": exc.lineno, "offset": exc.offset},
                )
            )

        has_draft_warning = self._contains_any(content, ("draft only", "manual qa api script draft"))
        if not has_draft_warning:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="missing_draft_marker",
                    message="Draft marker is missing from the script content.",
                    recommendation="Add an explicit Draft only marker to prevent misuse.",
                )
            )

        has_no_execution_marker = self._contains_any(content, ("not executed", "not verified"))
        if not has_no_execution_marker:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="missing_no_execution_marker",
                    message="No explicit no-execution marker was found.",
                    recommendation="Add a Not executed marker to clarify that the draft has not been run.",
                )
            )

        has_status_assertion = bool(
            re.search(r"assert\s+response\.status_code\s*==\s*(200|201|204|400|401|403|404|409|422|500)\b", content)
        )
        if not has_status_assertion:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="missing_status_assertion",
                    message="No explicit response.status_code assertion was found.",
                    recommendation="Add a concrete status code assertion to the draft.",
                )
            )

        has_requests_usage = bool(re.search(r"\bimport\s+requests\b|\brequests\.", content))
        if not has_requests_usage:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="missing_requests_usage",
                    message="The script does not appear to import or use requests.",
                    recommendation="Add requests import and request invocation to match the pytest-requests draft pattern.",
                )
            )

        has_todo_endpoint = "TODO_ENDPOINT" in content
        if has_todo_endpoint:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="todo_endpoint",
                    message="The draft still contains a TODO endpoint placeholder.",
                    recommendation="Replace the TODO endpoint with a real API path before review.",
                )
            )

        has_todo_payload = bool(
            re.search(r'TODO["\']?\s*:\s*["\']payload["\']|TODO payload|TODO_payload', content, re.IGNORECASE)
        )
        if has_todo_payload:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="todo_payload",
                    message="The draft still contains a TODO payload placeholder or hint.",
                    recommendation="Replace the payload placeholder with concrete request data before review.",
                )
            )

        has_base_url = "BASE_URL" in content
        if not has_base_url:
            issues.append(
                self._issue(
                    draft,
                    severity="Warning",
                    issue_type="missing_base_url",
                    message="BASE_URL variable was not detected in the draft.",
                    recommendation="Add BASE_URL configuration so the draft stays environment-agnostic.",
                )
            )

        has_test_function = bool(re.search(r"def\s+test_[a-z0-9_]+\s*\(", content))
        if not has_test_function:
            issues.append(
                self._issue(
                    draft,
                    severity="Error",
                    issue_type="missing_test_function",
                    message="No pytest-style test function was detected.",
                    recommendation="Add at least one def test_* function before packaging.",
                )
            )

        is_valid = syntax_valid and has_test_function
        warning_count = len([item for item in issues if item.severity == "Warning"])
        error_count = len([item for item in issues if item.severity == "Error"])

        result = APIScriptValidationResult(
            validation_id=f"APIVAL-{self._next_validation_number:03d}",
            draft_id=draft.draft_id,
            test_case_id=draft.test_case_id,
            file_name=draft.file_name,
            is_valid=is_valid,
            syntax_valid=syntax_valid,
            has_draft_warning=has_draft_warning,
            has_no_execution_marker=has_no_execution_marker,
            has_status_assertion=has_status_assertion,
            has_todo_endpoint=has_todo_endpoint,
            has_todo_payload=has_todo_payload,
            issues=issues,
            metadata={
                "warning_count": warning_count,
                "error_count": error_count,
                "requests_usage_detected": has_requests_usage,
                "base_url_detected": has_base_url,
                "test_function_detected": has_test_function,
            },
            created_at=self._next_timestamp(),
        )
        self._next_validation_number += 1
        return result

    def validate_api_script_drafts(
        self,
        drafts: Sequence[APITestScriptDraft],
    ) -> list[APIScriptValidationResult]:
        return [self.validate_api_script_draft(draft) for draft in drafts]

    def _issue(
        self,
        draft: APITestScriptDraft,
        *,
        severity: str,
        issue_type: str,
        message: str,
        recommendation: str,
        metadata: dict | None = None,
    ) -> APIScriptValidationIssue:
        issue = APIScriptValidationIssue(
            issue_id=f"APIVI-{self._next_issue_number:03d}",
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


_DEFAULT_API_SCRIPT_VALIDATION_SERVICE = APIScriptValidationService()


def validate_api_script_draft(draft: APITestScriptDraft) -> APIScriptValidationResult:
    """Convenience wrapper for validating a single API draft artifact."""

    return _DEFAULT_API_SCRIPT_VALIDATION_SERVICE.validate_api_script_draft(draft)


def validate_api_script_drafts(drafts: Sequence[APITestScriptDraft]) -> list[APIScriptValidationResult]:
    """Convenience wrapper for validating API draft artifacts in input order."""

    return _DEFAULT_API_SCRIPT_VALIDATION_SERVICE.validate_api_script_drafts(drafts)

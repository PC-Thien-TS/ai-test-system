"""Metadata-only packaging for validated Web Playwright draft artifacts."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence

from orchestrator.manual_qa.models import (
    WebPlaywrightPackageManifest,
    WebPlaywrightScriptDraft,
    WebPlaywrightValidationIssue,
    WebPlaywrightValidationResult,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


class WebPlaywrightPackagingService:
    """Build deterministic package metadata without zipping or executing drafts."""

    _BASE_TIME = datetime(2024, 1, 14, 0, 0, 0)

    def __init__(self) -> None:
        self._next_package_number = 1
        self._next_timestamp_offset = 0
        self._workspace_service = ManualQAWorkspaceService()

    def build_web_playwright_package(
        self,
        drafts: Sequence[WebPlaywrightScriptDraft],
        validation_results: Sequence[WebPlaywrightValidationResult],
        *,
        package_name: str = "web-playwright-script-drafts",
        validation_report_files: Sequence[str] | None = None,
        metadata: dict | None = None,
    ) -> WebPlaywrightPackageManifest:
        valid_count = len([item for item in validation_results if item.is_valid])
        invalid_count = len(validation_results) - valid_count
        warning_count = sum(
            1 for item in validation_results for issue in item.issues if issue.severity == "Warning"
        )
        has_error_issues = any(
            issue.severity == "Error" for item in validation_results for issue in item.issues
        )
        all_syntax_valid = all(item.syntax_valid for item in validation_results) if validation_results else True

        if has_error_issues or not all_syntax_valid:
            status = "Invalid"
        elif warning_count > 0:
            status = "Needs Attention"
        else:
            status = "Ready for Review"

        manifest = WebPlaywrightPackageManifest(
            package_id=f"WPPKG-{self._next_package_number:03d}",
            package_name=package_name,
            draft_count=len(drafts),
            valid_count=valid_count,
            invalid_count=invalid_count,
            warning_count=warning_count,
            draft_files=[draft.file_name for draft in drafts],
            validation_report_files=list(validation_report_files or []),
            generated_at=self._next_timestamp(),
            status=status,
            metadata={
                "all_syntax_valid": all_syntax_valid,
                "error_issue_count": sum(
                    1 for item in validation_results for issue in item.issues if issue.severity == "Error"
                ),
                **dict(metadata or {}),
            },
        )
        self._next_package_number += 1
        return manifest

    def build_web_playwright_package_from_workspace(
        self,
        workspace_path: str | Path,
        *,
        package_name: str = "web-playwright-script-drafts",
        validation_report_files: Sequence[str] | None = None,
        metadata: dict | None = None,
    ) -> WebPlaywrightPackageManifest:
        workspace = Path(workspace_path)
        draft_path = workspace / "script_drafts" / "web_playwright" / "web_playwright_script_drafts.json"
        validation_path = workspace / "script_drafts" / "web_playwright" / "web_playwright_validation.json"
        drafts_payload = self._workspace_service.read_json(draft_path)
        validations_payload = self._workspace_service.read_json(validation_path)
        drafts = [WebPlaywrightScriptDraft(**item) for item in drafts_payload if isinstance(item, dict)]
        results = [
            WebPlaywrightValidationResult(
                **{
                    **item,
                    "issues": [
                        WebPlaywrightValidationIssue(**issue)
                        for issue in item.get("issues", [])
                        if isinstance(issue, dict)
                    ],
                }
            )
            for item in validations_payload
            if isinstance(item, dict)
        ]
        return self.build_web_playwright_package(
            drafts,
            results,
            package_name=package_name,
            validation_report_files=validation_report_files,
            metadata=metadata,
        )

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_WEB_PLAYWRIGHT_PACKAGING_SERVICE = WebPlaywrightPackagingService()


def build_web_playwright_package(
    drafts: Sequence[WebPlaywrightScriptDraft],
    validation_results: Sequence[WebPlaywrightValidationResult],
    *,
    package_name: str = "web-playwright-script-drafts",
    validation_report_files: Sequence[str] | None = None,
    metadata: dict | None = None,
) -> WebPlaywrightPackageManifest:
    """Convenience wrapper for building Web Playwright draft package metadata."""

    return _DEFAULT_WEB_PLAYWRIGHT_PACKAGING_SERVICE.build_web_playwright_package(
        drafts,
        validation_results,
        package_name=package_name,
        validation_report_files=validation_report_files,
        metadata=metadata,
    )


def build_web_playwright_package_from_workspace(
    workspace_path: str | Path,
    *,
    package_name: str = "web-playwright-script-drafts",
    validation_report_files: Sequence[str] | None = None,
    metadata: dict | None = None,
) -> WebPlaywrightPackageManifest:
    """Convenience wrapper for building package metadata from workspace artifacts."""

    return _DEFAULT_WEB_PLAYWRIGHT_PACKAGING_SERVICE.build_web_playwright_package_from_workspace(
        workspace_path,
        package_name=package_name,
        validation_report_files=validation_report_files,
        metadata=metadata,
    )

"""Unified offline dashboard summary for Manual QA draft packages."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from orchestrator.manual_qa.models import (
    DraftPackageGroupSummary,
    UnifiedDraftPackageSummary,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


class UnifiedDraftPackageDashboardService:
    """Summarize API and Web draft package manifests without executing drafts."""

    _BASE_TIME = datetime(2024, 1, 15, 0, 0, 0)
    _KNOWN_STATUSES = {"Ready for Review", "Needs Attention", "Invalid"}

    def __init__(self) -> None:
        self._workspace_service = ManualQAWorkspaceService()
        self._next_timestamp_offset = 0

    def summarize_draft_packages(self, workspace_path: str | Path) -> UnifiedDraftPackageSummary:
        workspace = Path(workspace_path)
        api_group = self.summarize_api_package(workspace)
        web_group = self.summarize_web_playwright_package(workspace)
        groups = [api_group, web_group]

        overall_status = self._derive_overall_status(groups)
        summary = UnifiedDraftPackageSummary(
            summary_id="DRAFT-SUM-001",
            workspace_path=str(workspace),
            total_groups=len(groups),
            total_drafts=sum(group.draft_count for group in groups),
            total_valid=sum(group.valid_count for group in groups),
            total_invalid=sum(group.invalid_count for group in groups),
            total_warnings=sum(group.warning_count for group in groups),
            ready_groups=len([group for group in groups if group.status == "Ready for Review"]),
            needs_attention_groups=len([group for group in groups if group.status == "Needs Attention"]),
            invalid_groups=len([group for group in groups if group.status == "Invalid"]),
            missing_groups=len([group for group in groups if group.missing]),
            groups=groups,
            overall_status=overall_status,
            recommended_next_step=self._recommended_next_step(overall_status),
            created_at=self._next_timestamp(),
            metadata={
                "available_group_types": [
                    group.group_type for group in groups if not group.missing
                ],
            },
        )
        return summary

    def summarize_api_package(self, workspace_path: str | Path) -> DraftPackageGroupSummary:
        return self._summarize_group(
            workspace_path,
            group_id="DRAFT-GROUP-API",
            group_type="api",
            manifest_relative_path="script_drafts/api/api_script_package_manifest.json",
            validation_relative_path="script_drafts/api/api_script_validation.json",
        )

    def summarize_web_playwright_package(self, workspace_path: str | Path) -> DraftPackageGroupSummary:
        return self._summarize_group(
            workspace_path,
            group_id="DRAFT-GROUP-WEB-PLAYWRIGHT",
            group_type="web_playwright",
            manifest_relative_path="script_drafts/web_playwright/web_playwright_package_manifest.json",
            validation_relative_path="script_drafts/web_playwright/web_playwright_validation.json",
        )

    def _summarize_group(
        self,
        workspace_path: str | Path,
        *,
        group_id: str,
        group_type: str,
        manifest_relative_path: str,
        validation_relative_path: str,
    ) -> DraftPackageGroupSummary:
        workspace = Path(workspace_path)
        manifest_path = workspace / Path(manifest_relative_path)
        validation_path = workspace / Path(validation_relative_path)
        notes: list[str] = []

        if not manifest_path.exists():
            notes.append("Draft package manifest is missing.")
            if validation_path.exists():
                notes.append("Validation metadata exists without a package manifest.")
            return DraftPackageGroupSummary(
                group_id=group_id,
                group_type=group_type,
                manifest_path=manifest_relative_path,
                validation_path=validation_relative_path,
                status="Missing",
                missing=True,
                notes=notes,
                metadata={
                    "manifest_exists": False,
                    "validation_exists": validation_path.exists(),
                },
                created_at=self._next_timestamp(),
            )

        manifest_payload = self._read_json_dict(manifest_path)
        validation_items = self._read_json_list(validation_path)
        manifest_status = str(manifest_payload.get("status", "") or "").strip()
        status = manifest_status

        if manifest_status not in self._KNOWN_STATUSES:
            status = "Needs Attention"
            notes.append(f"Unknown manifest status: {manifest_status or 'empty'}")

        draft_count = self._as_int(manifest_payload.get("draft_count"))
        valid_count = self._as_int(manifest_payload.get("valid_count"))
        invalid_count = self._as_int(manifest_payload.get("invalid_count"))
        warning_count = self._as_int(manifest_payload.get("warning_count"))

        ready_for_review_count, needs_attention_count, invalid_item_count = self._item_status_counts(
            validation_items,
            group_status=status,
            draft_count=draft_count,
            valid_count=valid_count,
            invalid_count=invalid_count,
            warning_count=warning_count,
        )

        if validation_path.exists():
            warning_issue_count = 0
            error_issue_count = 0
            for item in validation_items:
                for issue in item.get("issues", []):
                    severity = str(issue.get("severity", "")).strip().lower()
                    if severity == "warning":
                        warning_issue_count += 1
                    if severity == "error":
                        error_issue_count += 1
            if warning_issue_count > 0:
                notes.append(f"Validation metadata includes {warning_issue_count} warning issue(s).")
            if error_issue_count > 0:
                notes.append(f"Validation metadata includes {error_issue_count} error issue(s).")
        else:
            notes.append("Validation metadata file is missing.")

        return DraftPackageGroupSummary(
            group_id=group_id,
            group_type=group_type,
            manifest_path=manifest_relative_path,
            validation_path=validation_relative_path,
            status=status,
            draft_count=draft_count,
            valid_count=valid_count,
            invalid_count=invalid_count,
            warning_count=warning_count,
            ready_for_review_count=ready_for_review_count,
            needs_attention_count=needs_attention_count,
            invalid_item_count=invalid_item_count,
            missing=False,
            notes=notes,
            metadata={
                "manifest_exists": True,
                "validation_exists": validation_path.exists(),
                "manifest_status_raw": manifest_status,
                "validation_item_count": len(validation_items),
                "package_id": str(manifest_payload.get("package_id", "")),
                "package_name": str(manifest_payload.get("package_name", "")),
            },
            created_at=self._next_timestamp(),
        )

    def _derive_overall_status(self, groups: list[DraftPackageGroupSummary]) -> str:
        available_groups = [group for group in groups if not group.missing]
        if not available_groups:
            return "Missing"
        if any(group.status == "Invalid" for group in groups):
            return "Invalid"
        if any(group.status == "Needs Attention" for group in groups):
            return "Needs Attention"
        if any(group.missing for group in groups):
            return "Needs Attention"
        return "Ready for Review"

    def _recommended_next_step(self, status: str) -> str:
        if status == "Ready for Review":
            return "Review drafts manually before sandbox execution design"
        if status == "Needs Attention":
            return "Resolve warnings and TODOs before execution planning"
        if status == "Invalid":
            return "Fix invalid draft packages before continuing"
        return "Generate and validate API/Web draft packages first"

    def _item_status_counts(
        self,
        validation_items: list[dict[str, Any]],
        *,
        group_status: str,
        draft_count: int,
        valid_count: int,
        invalid_count: int,
        warning_count: int,
    ) -> tuple[int, int, int]:
        if validation_items:
            ready_for_review_count = 0
            needs_attention_count = 0
            invalid_item_count = 0
            for item in validation_items:
                issues = item.get("issues", [])
                has_error = any(
                    str(issue.get("severity", "")).strip().lower() == "error"
                    for issue in issues
                    if isinstance(issue, dict)
                )
                has_warning = any(
                    str(issue.get("severity", "")).strip().lower() == "warning"
                    for issue in issues
                    if isinstance(issue, dict)
                )
                is_valid = bool(item.get("is_valid", False))
                todo_flags = [
                    key for key, value in item.items()
                    if key.startswith("has_todo_") and bool(value)
                ]
                if not is_valid or has_error:
                    invalid_item_count += 1
                elif has_warning or todo_flags:
                    needs_attention_count += 1
                else:
                    ready_for_review_count += 1
            return ready_for_review_count, needs_attention_count, invalid_item_count

        if group_status == "Ready for Review":
            return valid_count, 0, 0
        if group_status == "Invalid":
            return 0, 0, invalid_count or draft_count
        if group_status == "Needs Attention":
            fallback_attention = draft_count if draft_count > 0 else warning_count
            return 0, fallback_attention, invalid_count
        return 0, 0, 0

    def _read_json_dict(self, path: Path) -> dict[str, Any]:
        payload = self._workspace_service.read_json(path)
        return payload if isinstance(payload, dict) else {}

    def _read_json_list(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        payload = self._workspace_service.read_json(path)
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]

    def _as_int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


def summarize_draft_packages(workspace_path: str | Path) -> UnifiedDraftPackageSummary:
    """Convenience wrapper for the unified draft package summary."""

    return UnifiedDraftPackageDashboardService().summarize_draft_packages(workspace_path)


def summarize_api_package(workspace_path: str | Path) -> DraftPackageGroupSummary:
    """Convenience wrapper for summarizing the API draft package."""

    return UnifiedDraftPackageDashboardService().summarize_api_package(workspace_path)


def summarize_web_playwright_package(workspace_path: str | Path) -> DraftPackageGroupSummary:
    """Convenience wrapper for summarizing the Web Playwright draft package."""

    return UnifiedDraftPackageDashboardService().summarize_web_playwright_package(workspace_path)

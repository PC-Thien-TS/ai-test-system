from __future__ import annotations

import json
from pathlib import Path

from orchestrator.manual_qa.draft_package_dashboard_service import (
    summarize_draft_packages,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _api_manifest(status: str, *, warning_count: int = 0, invalid_count: int = 0) -> dict[str, object]:
    return {
        "package_id": "APIPKG-001",
        "package_name": "api-script-drafts",
        "draft_count": 1,
        "valid_count": 0 if invalid_count else 1,
        "invalid_count": invalid_count,
        "warning_count": warning_count,
        "draft_files": ["test_api_tc_001.py"],
        "validation_report_files": ["script_drafts/api/api_script_validation.json"],
        "generated_at": "2024-01-10T00:00:00Z",
        "status": status,
        "metadata": {},
    }


def _web_manifest(status: str, *, warning_count: int = 0, invalid_count: int = 0) -> dict[str, object]:
    return {
        "package_id": "WPPKG-001",
        "package_name": "web-playwright-script-drafts",
        "draft_count": 1,
        "valid_count": 0 if invalid_count else 1,
        "invalid_count": invalid_count,
        "warning_count": warning_count,
        "draft_files": ["test_web_tc_001.py"],
        "validation_report_files": ["script_drafts/web_playwright/web_playwright_validation.json"],
        "generated_at": "2024-01-14T00:00:00Z",
        "status": status,
        "metadata": {},
    }


def _api_validation(*, is_valid: bool, issues: list[dict[str, str]] | None = None) -> list[dict[str, object]]:
    return [
        {
            "validation_id": "APIVAL-001",
            "draft_id": "API-DRAFT-001",
            "test_case_id": "TC-900",
            "file_name": "test_api_tc_001.py",
            "is_valid": is_valid,
            "syntax_valid": True,
            "has_draft_warning": True,
            "has_no_execution_marker": True,
            "has_status_assertion": True,
            "has_todo_endpoint": False,
            "has_todo_payload": False,
            "issues": issues or [],
            "metadata": {},
            "created_at": "2024-01-09T00:00:00Z",
        }
    ]


def _web_validation(*, is_valid: bool, issues: list[dict[str, str]] | None = None) -> list[dict[str, object]]:
    return [
        {
            "validation_id": "WPVAL-001",
            "draft_id": "WEB-DRAFT-001",
            "test_case_id": "TC-901",
            "file_name": "test_web_tc_001.py",
            "is_valid": is_valid,
            "syntax_valid": True,
            "has_draft_warning": True,
            "has_no_execution_marker": True,
            "has_playwright_import": True,
            "has_test_function": True,
            "has_page_goto": True,
            "has_locator_or_todo": True,
            "has_action_or_todo": True,
            "has_assertion_or_todo": True,
            "has_todo_page_url": False,
            "has_todo_selector": False,
            "has_todo_assertion": False,
            "issues": issues or [],
            "metadata": {},
            "created_at": "2024-01-13T00:00:00Z",
        }
    ]


def test_summary_when_no_manifests_exist_returns_missing(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    summary = summarize_draft_packages(workspace)

    assert summary.overall_status == "Missing"
    assert summary.missing_groups == 2
    assert summary.total_drafts == 0
    assert summary.recommended_next_step == "Generate and validate API/Web draft packages first"


def test_summary_with_api_ready_only_marks_web_group_missing(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_json(
        workspace / "script_drafts" / "api" / "api_script_package_manifest.json",
        _api_manifest("Ready for Review"),
    )
    _write_json(
        workspace / "script_drafts" / "api" / "api_script_validation.json",
        _api_validation(is_valid=True),
    )

    summary = summarize_draft_packages(workspace)
    groups = {group.group_type: group for group in summary.groups}

    assert groups["api"].status == "Ready for Review"
    assert groups["web_playwright"].status == "Missing"
    assert summary.overall_status == "Needs Attention"
    assert summary.total_drafts == 1
    assert summary.total_valid == 1


def test_summary_with_web_playwright_ready_only_marks_api_group_missing(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_json(
        workspace / "script_drafts" / "web_playwright" / "web_playwright_package_manifest.json",
        _web_manifest("Ready for Review"),
    )
    _write_json(
        workspace / "script_drafts" / "web_playwright" / "web_playwright_validation.json",
        _web_validation(is_valid=True),
    )

    summary = summarize_draft_packages(workspace)
    groups = {group.group_type: group for group in summary.groups}

    assert groups["web_playwright"].status == "Ready for Review"
    assert groups["api"].status == "Missing"
    assert summary.overall_status == "Needs Attention"
    assert summary.total_drafts == 1
    assert summary.total_valid == 1


def test_summary_with_api_needs_attention_uses_manifest_status(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_json(
        workspace / "script_drafts" / "api" / "api_script_package_manifest.json",
        _api_manifest("Needs Attention", warning_count=2),
    )
    _write_json(
        workspace / "script_drafts" / "api" / "api_script_validation.json",
        _api_validation(
            is_valid=True,
            issues=[
                {
                    "issue_id": "APIVAL-ISSUE-001",
                    "draft_id": "API-DRAFT-001",
                    "severity": "Warning",
                    "issue_type": "todo_payload",
                    "message": "TODO payload placeholder remains.",
                    "recommendation": "Replace TODO payload before execution planning.",
                    "metadata": {},
                }
            ],
        ),
    )

    summary = summarize_draft_packages(workspace)
    api_group = {group.group_type: group for group in summary.groups}["api"]

    assert api_group.status == "Needs Attention"
    assert api_group.warning_count == 2
    assert any("warning issue" in note.lower() for note in api_group.notes)
    assert summary.overall_status == "Needs Attention"


def test_summary_with_web_playwright_invalid_marks_overall_invalid(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_json(
        workspace / "script_drafts" / "web_playwright" / "web_playwright_package_manifest.json",
        _web_manifest("Invalid", invalid_count=1),
    )
    _write_json(
        workspace / "script_drafts" / "web_playwright" / "web_playwright_validation.json",
        _web_validation(
            is_valid=False,
            issues=[
                {
                    "issue_id": "WPVAL-ISSUE-001",
                    "draft_id": "WEB-DRAFT-001",
                    "severity": "Error",
                    "issue_type": "syntax_error",
                    "message": "Draft has a syntax error.",
                    "recommendation": "Fix syntax before continuing.",
                    "metadata": {},
                }
            ],
        ),
    )

    summary = summarize_draft_packages(workspace)
    web_group = {group.group_type: group for group in summary.groups}["web_playwright"]

    assert web_group.status == "Invalid"
    assert web_group.invalid_item_count == 1
    assert summary.overall_status == "Invalid"


def test_summary_with_both_api_and_web_ready_returns_ready_for_review(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_json(
        workspace / "script_drafts" / "api" / "api_script_package_manifest.json",
        _api_manifest("Ready for Review"),
    )
    _write_json(
        workspace / "script_drafts" / "api" / "api_script_validation.json",
        _api_validation(is_valid=True),
    )
    _write_json(
        workspace / "script_drafts" / "web_playwright" / "web_playwright_package_manifest.json",
        _web_manifest("Ready for Review"),
    )
    _write_json(
        workspace / "script_drafts" / "web_playwright" / "web_playwright_validation.json",
        _web_validation(is_valid=True),
    )

    summary = summarize_draft_packages(workspace)

    assert summary.overall_status == "Ready for Review"
    assert summary.ready_groups == 2
    assert summary.missing_groups == 0
    assert summary.total_drafts == 2


def test_summary_with_one_ready_and_one_missing_returns_needs_attention(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_json(
        workspace / "script_drafts" / "api" / "api_script_package_manifest.json",
        _api_manifest("Ready for Review"),
    )

    summary = summarize_draft_packages(workspace)

    assert summary.overall_status == "Needs Attention"
    assert summary.ready_groups == 1
    assert summary.missing_groups == 1


def test_unknown_manifest_status_becomes_needs_attention(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_json(
        workspace / "script_drafts" / "api" / "api_script_package_manifest.json",
        _api_manifest("Unknown Future Status"),
    )

    summary = summarize_draft_packages(workspace)
    api_group = {group.group_type: group for group in summary.groups}["api"]

    assert api_group.status == "Needs Attention"
    assert any("unknown manifest status" in note.lower() for note in api_group.notes)


def test_recommended_next_step_matches_status(tmp_path):
    workspace_missing = ManualQAWorkspaceService().create_workspace(tmp_path / "missing_demo")
    missing_summary = summarize_draft_packages(workspace_missing)

    workspace_invalid = ManualQAWorkspaceService().create_workspace(tmp_path / "invalid_demo")
    _write_json(
        workspace_invalid / "script_drafts" / "web_playwright" / "web_playwright_package_manifest.json",
        _web_manifest("Invalid", invalid_count=1),
    )
    invalid_summary = summarize_draft_packages(workspace_invalid)

    workspace_ready = ManualQAWorkspaceService().create_workspace(tmp_path / "ready_demo")
    _write_json(
        workspace_ready / "script_drafts" / "api" / "api_script_package_manifest.json",
        _api_manifest("Ready for Review"),
    )
    _write_json(
        workspace_ready / "script_drafts" / "api" / "api_script_validation.json",
        _api_validation(is_valid=True),
    )
    _write_json(
        workspace_ready / "script_drafts" / "web_playwright" / "web_playwright_package_manifest.json",
        _web_manifest("Ready for Review"),
    )
    _write_json(
        workspace_ready / "script_drafts" / "web_playwright" / "web_playwright_validation.json",
        _web_validation(is_valid=True),
    )
    ready_summary = summarize_draft_packages(workspace_ready)

    assert missing_summary.recommended_next_step == "Generate and validate API/Web draft packages first"
    assert invalid_summary.recommended_next_step == "Fix invalid draft packages before continuing"
    assert ready_summary.recommended_next_step == "Review drafts manually before sandbox execution design"


def test_summary_does_not_read_or_execute_draft_scripts(tmp_path, monkeypatch):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_json(
        workspace / "script_drafts" / "api" / "api_script_package_manifest.json",
        _api_manifest("Ready for Review"),
    )
    _write_json(
        workspace / "script_drafts" / "api" / "api_script_validation.json",
        _api_validation(is_valid=True),
    )
    api_script_path = workspace / "script_drafts" / "api" / "test_api_tc_001.py"
    api_script_path.write_text("raise RuntimeError('should never be read or executed')", encoding="utf-8")

    original_read_text = Path.read_text

    def _guarded_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.suffix == ".py":
            raise AssertionError("Draft scripts must not be read during summary generation.")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _guarded_read_text)

    summary = summarize_draft_packages(workspace)

    assert summary.total_drafts == 1
    assert summary.overall_status == "Needs Attention"

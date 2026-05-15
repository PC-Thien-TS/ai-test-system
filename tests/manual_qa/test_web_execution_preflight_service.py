from __future__ import annotations

import json
import webbrowser
from pathlib import Path

from orchestrator.manual_qa.web_execution_preflight_service import (
    build_web_execution_plan_from_workspace,
)
from orchestrator.manual_qa.web_execution_safety_service import (
    create_default_web_execution_safety_policy,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_web_artifacts(
    workspace: Path,
    *,
    base_url: str = "http://localhost:3000",
    page_url: str = "/login",
    selector_hint: str = "data-testid=login-email",
    package_status: str = "Ready for Review",
    validation_is_valid: bool = True,
    validation_flags: dict[str, bool] | None = None,
    title: str = "Portal login draft",
    extra_script_lines: list[str] | None = None,
) -> None:
    draft_dir = workspace / "script_drafts" / "web_playwright"
    script_lines = [
        "import os",
        "from playwright.sync_api import Page, expect",
        "",
        f'BASE_URL = os.getenv("WEB_BASE_URL", "{base_url}")',
        "",
        "def test_web_draft(page: Page):",
        f'    page.goto(BASE_URL + "{page_url}")',
        f'    page.locator("{selector_hint}").click()',
    ]
    script_lines.extend(extra_script_lines or [])
    script_lines.append("")
    script_content = "\n".join(script_lines)
    _write_json(
        draft_dir / "web_playwright_script_drafts.json",
        [
            {
                "draft_id": "WEB-DRAFT-001",
                "test_case_id": "TC-901",
                "requirement_ids": ["REQ-901"],
                "module": "Portal UI",
                "title": title,
                "readiness_id": "WPREAD-001",
                "framework": "playwright-python",
                "language": "python",
                "file_name": "test_web_tc_001.py",
                "script_content": script_content,
                "status": "Draft",
                "warnings": [],
                "assumptions": [],
                "metadata": {
                    "page_url": page_url,
                    "selector_hints": [selector_hint],
                    "base_url_env_var": "WEB_BASE_URL",
                },
                "created_at": "2024-01-12T00:00:00Z",
            }
        ],
    )
    _write_json(
        draft_dir / "web_playwright_package_manifest.json",
        {
            "package_id": "WPPKG-001",
            "package_name": "web-playwright-script-drafts",
            "draft_count": 1,
            "valid_count": 1 if validation_is_valid else 0,
            "invalid_count": 0 if validation_is_valid else 1,
            "warning_count": 0,
            "draft_files": ["test_web_tc_001.py"],
            "validation_report_files": ["script_drafts/web_playwright/web_playwright_validation.json"],
            "generated_at": "2024-01-14T00:00:00Z",
            "status": package_status,
            "metadata": {},
        },
    )
    validation_payload = {
        "validation_id": "WPVAL-001",
        "draft_id": "WEB-DRAFT-001",
        "test_case_id": "TC-901",
        "file_name": "test_web_tc_001.py",
        "is_valid": validation_is_valid,
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
        "issues": [],
        "metadata": {},
        "created_at": "2024-01-13T00:00:00Z",
    }
    validation_payload.update(validation_flags or {})
    _write_json(draft_dir / "web_playwright_validation.json", [validation_payload])


def test_missing_packages_returns_missing_web_draft_packages_plan(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    plan = build_web_execution_plan_from_workspace(workspace)

    assert plan.overall_decision == "Missing Web Draft Packages"
    assert plan.total_targets == 0


def test_valid_web_package_under_default_policy_returns_dry_run_or_needs_approval(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_web_artifacts(workspace)

    plan = build_web_execution_plan_from_workspace(workspace)

    assert plan.total_targets == 1
    assert plan.preflight_results[0].decision in {"Dry Run Only", "Needs Human Approval"}


def test_invalid_package_returns_blocked_or_needs_attention(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_web_artifacts(workspace, package_status="Invalid", validation_is_valid=False)

    plan = build_web_execution_plan_from_workspace(workspace)

    assert plan.preflight_results[0].decision in {"Blocked", "Needs Human Approval", "Dry Run Only"}
    assert plan.overall_decision == "Blocked"


def test_production_url_creates_critical_issue(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_web_artifacts(workspace, base_url="https://production.example.com")

    plan = build_web_execution_plan_from_workspace(workspace)
    issues = plan.preflight_results[0].issues

    assert any(issue.issue_type == "blocked_base_url" and issue.severity == "Critical" for issue in issues)
    assert plan.preflight_results[0].risk_level == "Critical"


def test_todo_selector_needs_attention(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_web_artifacts(
        workspace,
        selector_hint="TODO_SELECTOR",
        package_status="Needs Attention",
        validation_flags={"has_todo_selector": True},
    )

    plan = build_web_execution_plan_from_workspace(workspace)
    issues = plan.preflight_results[0].issues

    assert any(issue.issue_type in {"todo_selector", "package_needs_attention"} for issue in issues)


def test_todo_page_url_needs_attention(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_web_artifacts(
        workspace,
        page_url="/TODO_PAGE_URL",
        validation_flags={"has_todo_page_url": True},
    )

    plan = build_web_execution_plan_from_workspace(workspace)

    assert any(issue.issue_type == "todo_page_url" for issue in plan.preflight_results[0].issues)


def test_captcha_or_otp_is_critical_or_blocked(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_web_artifacts(
        workspace,
        title="Checkout captcha and OTP flow",
        extra_script_lines=['    page.get_by_text("Enter OTP").click()'],
    )

    plan = build_web_execution_plan_from_workspace(workspace)

    assert any(issue.issue_type == "captcha_or_otp_blocked" for issue in plan.preflight_results[0].issues)
    assert plan.preflight_results[0].risk_level == "Critical"


def test_file_upload_download_is_high_unless_policy_allows(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_web_artifacts(
        workspace,
        title="Document upload and download flow",
        extra_script_lines=[
            '    page.locator("input[type=file]").set_input_files("TODO_FILE")',
            '    page.get_by_text("Download file").click()',
        ],
    )

    plan = build_web_execution_plan_from_workspace(workspace)

    assert any(issue.issue_type == "file_upload_not_allowed" for issue in plan.preflight_results[0].issues)
    assert any(issue.issue_type == "file_download_not_allowed" for issue in plan.preflight_results[0].issues)
    assert plan.preflight_results[0].risk_level in {"High", "Critical"}


def test_browser_execution_disabled_by_policy_creates_issue(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_web_artifacts(workspace)
    policy = create_default_web_execution_safety_policy()

    plan = build_web_execution_plan_from_workspace(workspace, policy=policy)

    assert any(issue.issue_type == "browser_execution_disabled_by_policy" for issue in plan.preflight_results[0].issues)


def test_plan_does_not_execute_scripts_or_launch_browser(tmp_path, monkeypatch):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_web_artifacts(workspace)
    (workspace / "script_drafts" / "web_playwright" / "test_web_tc_001.py").write_text(
        "raise RuntimeError('should not run')",
        encoding="utf-8",
    )

    original_read_text = Path.read_text

    def _guarded_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.suffix == ".py":
            raise AssertionError("Generated Playwright scripts must not be read or executed during web preflight.")
        return original_read_text(self, *args, **kwargs)

    def _blocked_browser(*args: object, **kwargs: object) -> object:
        raise AssertionError("Browser launch must not occur during web preflight.")

    monkeypatch.setattr(Path, "read_text", _guarded_read_text)
    monkeypatch.setattr(webbrowser, "open", _blocked_browser)

    plan = build_web_execution_plan_from_workspace(workspace)

    assert plan.total_targets == 1

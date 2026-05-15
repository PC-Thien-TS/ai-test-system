from __future__ import annotations

import json
import socket
import webbrowser
from pathlib import Path

from orchestrator.manual_qa.execution_preflight_service import (
    build_execution_plan_from_workspace,
)
from orchestrator.manual_qa.execution_safety_service import (
    create_default_execution_safety_policy,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_api_artifacts(
    workspace: Path,
    *,
    base_url: str = "http://localhost:8000",
    method: str = "GET",
    endpoint: str = "/api/orders",
    package_status: str = "Ready for Review",
    validation_is_valid: bool = True,
    validation_status_flags: dict[str, bool] | None = None,
) -> None:
    draft_dir = workspace / "script_drafts" / "api"
    script_content = "\n".join(
        [
            "import os",
            "import requests",
            "",
            f'BASE_URL = os.getenv("API_BASE_URL", "{base_url}")',
            "",
            "def test_api_draft():",
            f'    response = requests.{method.lower()}(BASE_URL + "{endpoint}", headers={{}})',
            "    assert response.status_code == 200",
            "",
        ]
    )
    _write_json(
        draft_dir / "api_script_drafts.json",
        [
            {
                "draft_id": "API-DRAFT-001",
                "test_case_id": "TC-900",
                "requirement_ids": ["REQ-900"],
                "module": "Order API",
                "title": "Order API draft",
                "readiness_id": "READ-900",
                "target_type": "api",
                "framework": "pytest-requests",
                "language": "python",
                "file_name": "test_api_tc_001.py",
                "script_content": script_content,
                "status": "Draft",
                "warnings": [],
                "assumptions": [],
                "metadata": {
                    "http_method": method,
                    "endpoint": endpoint,
                    "base_url_env_var": "API_BASE_URL",
                },
                "created_at": "2024-01-08T00:00:00Z",
            }
        ],
    )
    _write_json(
        draft_dir / "api_script_package_manifest.json",
        {
            "package_id": "APIPKG-001",
            "package_name": "api-script-drafts",
            "draft_count": 1,
            "valid_count": 1 if validation_is_valid else 0,
            "invalid_count": 0 if validation_is_valid else 1,
            "warning_count": 0,
            "draft_files": ["test_api_tc_001.py"],
            "validation_report_files": ["script_drafts/api/api_script_validation.json"],
            "generated_at": "2024-01-10T00:00:00Z",
            "status": package_status,
            "metadata": {},
        },
    )
    validation_payload = {
        "validation_id": "APIVAL-001",
        "draft_id": "API-DRAFT-001",
        "test_case_id": "TC-900",
        "file_name": "test_api_tc_001.py",
        "is_valid": validation_is_valid,
        "syntax_valid": True,
        "has_draft_warning": True,
        "has_no_execution_marker": True,
        "has_status_assertion": True,
        "has_todo_endpoint": False,
        "has_todo_payload": False,
        "issues": [],
        "metadata": {},
        "created_at": "2024-01-09T00:00:00Z",
    }
    validation_payload.update(validation_status_flags or {})
    _write_json(draft_dir / "api_script_validation.json", [validation_payload])


def _write_web_artifacts(
    workspace: Path,
    *,
    base_url: str = "http://localhost:3000",
    page_url: str = "/login",
    selector_hint: str = "TODO_SELECTOR",
    package_status: str = "Ready for Review",
    validation_flags: dict[str, bool] | None = None,
) -> None:
    draft_dir = workspace / "script_drafts" / "web_playwright"
    script_content = "\n".join(
        [
            "import os",
            "from playwright.sync_api import Page, expect",
            "",
            f'BASE_URL = os.getenv("WEB_BASE_URL", "{base_url}")',
            "",
            "def test_web_draft(page: Page):",
            f'    page.goto(BASE_URL + "{page_url}")',
            f'    page.locator("{selector_hint}").click()',
            "",
        ]
    )
    _write_json(
        draft_dir / "web_playwright_script_drafts.json",
        [
            {
                "draft_id": "WEB-DRAFT-001",
                "test_case_id": "TC-901",
                "requirement_ids": ["REQ-901"],
                "module": "Portal UI",
                "title": "Portal login draft",
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
            "valid_count": 1,
            "invalid_count": 0,
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
        "is_valid": True,
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


def test_missing_packages_returns_missing_draft_packages_plan(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    plan = build_execution_plan_from_workspace(workspace)

    assert plan.overall_decision == "Missing Draft Packages"
    assert plan.total_targets == 0


def test_valid_api_package_under_default_policy_returns_dry_run_or_needs_approval(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_api_artifacts(workspace)

    plan = build_execution_plan_from_workspace(workspace)

    assert plan.total_targets == 1
    assert plan.preflight_results[0].decision in {"Dry Run Only", "Needs Human Approval"}


def test_invalid_package_returns_blocked_or_needs_attention(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_api_artifacts(workspace, package_status="Invalid", validation_is_valid=False)

    plan = build_execution_plan_from_workspace(workspace)

    assert plan.preflight_results[0].decision in {"Blocked", "Needs Human Approval", "Dry Run Only"}
    assert plan.overall_decision == "Blocked"


def test_production_url_creates_critical_issue(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_api_artifacts(workspace, base_url="https://production.example.com")

    plan = build_execution_plan_from_workspace(workspace)
    issues = plan.preflight_results[0].issues

    assert any(issue.issue_type == "blocked_base_url" and issue.severity == "Critical" for issue in issues)
    assert plan.preflight_results[0].risk_level == "Critical"


def test_delete_method_when_delete_not_allowed_creates_critical_or_high_issue(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_api_artifacts(workspace, method="DELETE", endpoint="/api/users/1")

    plan = build_execution_plan_from_workspace(workspace)
    issues = plan.preflight_results[0].issues

    assert any(issue.issue_type == "delete_method_blocked" for issue in issues)
    assert plan.preflight_results[0].risk_level in {"Critical", "High"}


def test_web_draft_with_todo_selector_needs_attention(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_web_artifacts(
        workspace,
        selector_hint="TODO_SELECTOR",
        package_status="Needs Attention",
        validation_flags={"has_todo_selector": True},
    )

    plan = build_execution_plan_from_workspace(workspace)
    issues = plan.preflight_results[0].issues

    assert any(issue.issue_type in {"critical_todo_present", "package_needs_attention"} for issue in issues)


def test_execution_disabled_by_policy_creates_issue(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_api_artifacts(workspace)
    policy = create_default_execution_safety_policy()

    plan = build_execution_plan_from_workspace(workspace, policy=policy)

    assert any(
        issue.issue_type == "execution_disabled_by_policy"
        for issue in plan.preflight_results[0].issues
    )


def test_plan_does_not_execute_scripts_send_http_requests_or_launch_browser(tmp_path, monkeypatch):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    _write_api_artifacts(workspace)
    (workspace / "script_drafts" / "api" / "test_api_tc_001.py").write_text(
        "raise RuntimeError('should not run')",
        encoding="utf-8",
    )

    original_read_text = Path.read_text

    def _guarded_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.suffix == ".py":
            raise AssertionError("Generated scripts must not be read or executed during preflight.")
        return original_read_text(self, *args, **kwargs)

    def _blocked_connection(*args: object, **kwargs: object) -> object:
        raise AssertionError("Network access must not occur during preflight.")

    def _blocked_browser(*args: object, **kwargs: object) -> object:
        raise AssertionError("Browser launch must not occur during preflight.")

    monkeypatch.setattr(Path, "read_text", _guarded_read_text)
    monkeypatch.setattr(socket, "create_connection", _blocked_connection)
    monkeypatch.setattr(webbrowser, "open", _blocked_browser)

    plan = build_execution_plan_from_workspace(workspace)

    assert plan.total_targets == 1

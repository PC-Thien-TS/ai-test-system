from __future__ import annotations

import json
import sys
from pathlib import Path

from orchestrator.manual_qa.cli import main


def _write_requirements(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "## [REQ-001] Login success",
                "Module: Authentication",
                "Priority: High",
                "Acceptance Criteria:",
                "- User reaches dashboard.",
                "",
                "## [REQ-002] Search works",
                "Module: Search",
                "Priority: Medium",
                "Acceptance Criteria:",
                "- Results are shown for a valid query.",
            ]
        ),
        encoding="utf-8",
    )


def _run_base_cli_workflow(workspace: Path, requirements_path: Path) -> None:
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    assert main(
        [
            "create-project",
            "--workspace",
            str(workspace),
            "--name",
            "Demo Web",
            "--product-type",
            "web",
        ]
    ) == 0
    assert main(
        [
            "import-requirements",
            "--workspace",
            str(workspace),
            "--input",
            str(requirements_path),
        ]
    ) == 0
    assert main(["generate-checklist", "--workspace", str(workspace)]) == 0
    assert main(["generate-testcases", "--workspace", str(workspace)]) == 0
    assert main(
        [
            "create-suite",
            "--workspace",
            str(workspace),
            "--name",
            "smoke",
        ]
    ) == 0
    assert main(
        [
            "create-run",
            "--workspace",
            str(workspace),
            "--suite",
            "suites/smoke.json",
            "--env",
            "staging",
            "--build",
            "v1.0.0",
            "--tester",
            "Thien",
        ]
    ) == 0


def _write_api_testcases(workspace: Path) -> None:
    payload = [
        {
            "test_case_id": "TC-900",
            "requirement_ids": ["REQ-900"],
            "module": "Order API",
            "title": "Create order endpoint returns status code 201",
            "preconditions": [],
            "steps": [
                "Send POST request to /api/orders with valid payload.",
                "Verify response status code is 201.",
            ],
            "expected_result": "Response status code is 201 and order is created.",
            "priority": "High",
            "test_type": "Positive",
            "status": "Not Run",
            "metadata": {"test_data": {"sku": "SKU-001"}},
        }
    ]
    (workspace / "testcases" / "testcases.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _write_web_ui_testcases(workspace: Path) -> None:
    payload = [
        {
            "test_case_id": "TC-901",
            "requirement_ids": ["REQ-901"],
            "module": "Portal UI",
            "title": "Login page submit flow",
            "preconditions": [],
            "steps": [
                "Navigate to /login page.",
                "Fill data-testid=login-email with valid email.",
                "Fill data-testid=login-password with valid password.",
                "Click button text sign in.",
            ],
            "expected_result": "User should see dashboard and URL contains /dashboard.",
            "priority": "High",
            "test_type": "Positive",
            "status": "Not Run",
            "metadata": {},
        }
    ]
    (workspace / "testcases" / "testcases.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _write_api_package_manifest(workspace: Path, *, status: str = "Ready for Review") -> None:
    draft_dir = workspace / "script_drafts" / "api"
    draft_dir.mkdir(parents=True, exist_ok=True)
    (draft_dir / "api_script_package_manifest.json").write_text(
        json.dumps(
            {
                "package_id": "APIPKG-001",
                "package_name": "api-script-drafts",
                "draft_count": 1,
                "valid_count": 1,
                "invalid_count": 0,
                "warning_count": 0,
                "draft_files": ["test_api_tc_001.py"],
                "validation_report_files": ["script_drafts/api/api_script_validation.json"],
                "generated_at": "2024-01-10T00:00:00Z",
                "status": status,
                "metadata": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (draft_dir / "api_script_validation.json").write_text(
        json.dumps(
            [
                {
                    "validation_id": "APIVAL-001",
                    "draft_id": "API-DRAFT-001",
                    "test_case_id": "TC-900",
                    "file_name": "test_api_tc_001.py",
                    "is_valid": True,
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
            ],
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_web_package_manifest(workspace: Path, *, status: str = "Ready for Review") -> None:
    draft_dir = workspace / "script_drafts" / "web_playwright"
    draft_dir.mkdir(parents=True, exist_ok=True)
    (draft_dir / "web_playwright_package_manifest.json").write_text(
        json.dumps(
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
                "status": status,
                "metadata": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (draft_dir / "web_playwright_validation.json").write_text(
        json.dumps(
            [
                {
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
            ],
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_execution_api_draft_package(
    workspace: Path,
    *,
    base_url: str = "http://localhost:8000",
    method: str = "GET",
    endpoint: str = "/api/orders",
    package_status: str = "Ready for Review",
) -> None:
    draft_dir = workspace / "script_drafts" / "api"
    draft_dir.mkdir(parents=True, exist_ok=True)
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
    (draft_dir / "api_script_drafts.json").write_text(
        json.dumps(
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
            indent=2,
        ),
        encoding="utf-8",
    )
    (draft_dir / "api_script_package_manifest.json").write_text(
        json.dumps(
            {
                "package_id": "APIPKG-001",
                "package_name": "api-script-drafts",
                "draft_count": 1,
                "valid_count": 1,
                "invalid_count": 0,
                "warning_count": 0,
                "draft_files": ["test_api_tc_001.py"],
                "validation_report_files": ["script_drafts/api/api_script_validation.json"],
                "generated_at": "2024-01-10T00:00:00Z",
                "status": package_status,
                "metadata": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (draft_dir / "api_script_validation.json").write_text(
        json.dumps(
            [
                {
                    "validation_id": "APIVAL-001",
                    "draft_id": "API-DRAFT-001",
                    "test_case_id": "TC-900",
                    "file_name": "test_api_tc_001.py",
                    "is_valid": True,
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
            ],
            indent=2,
        ),
        encoding="utf-8",
    )


def test_init_workspace_creates_folders(tmp_path):
    workspace = tmp_path / "manual_qa_demo"

    exit_code = main(["init-workspace", "--path", str(workspace)])

    assert exit_code == 0
    assert (workspace / "requirements").exists()
    assert (workspace / "reports").exists()
    assert (workspace / "workspace_manifest.json").exists()


def test_end_to_end_cli_workflow_writes_expected_artifacts(tmp_path):
    workspace = tmp_path / "manual_qa_demo"
    requirements_path = tmp_path / "requirements.md"
    _write_requirements(requirements_path)

    _run_base_cli_workflow(workspace, requirements_path)
    assert (workspace / "project.json").exists()

    normalized_requirements = workspace / "requirements" / "normalized_requirements.json"
    assert normalized_requirements.exists()
    assert (workspace / "checklists" / "checklist.json").exists()
    assert (workspace / "checklists" / "checklist.md").exists()

    testcases_json = workspace / "testcases" / "testcases.json"
    testcases_md = workspace / "testcases" / "testcases.md"
    assert testcases_json.exists()
    assert testcases_md.exists()

    suite_json = workspace / "suites" / "smoke.json"
    assert suite_json.exists()

    run_json = workspace / "runs" / "RUN-001.json"
    assert run_json.exists()

    assert main(
        [
            "update-result",
            "--workspace",
            str(workspace),
            "--run",
            "runs/RUN-001.json",
            "--case",
            "TC-001",
            "--status",
            "Fail",
            "--actual",
            "Login error message is incorrect",
        ]
    ) == 0
    summary_json = workspace / "runs" / "RUN-001-summary.json"
    summary_md = workspace / "runs" / "RUN-001-summary.md"
    assert summary_json.exists()
    assert summary_md.exists()
    updated_run_payload = json.loads(run_json.read_text(encoding="utf-8"))
    assert updated_run_payload["results"][0]["status"] == "Fail"

    assert main(
        [
            "attach-evidence",
            "--workspace",
            str(workspace),
            "--run",
            "runs/RUN-001.json",
            "--case",
            "TC-001",
            "--type",
            "screenshot",
            "--path",
            "evidence/login_error.png",
            "--description",
            "Login error screenshot",
        ]
    ) == 0
    evidence_json = workspace / "evidence" / "EVD-001.json"
    evidence_md = workspace / "evidence" / "EVD-001.md"
    assert evidence_json.exists()
    assert evidence_md.exists()
    run_with_evidence = json.loads(run_json.read_text(encoding="utf-8"))
    assert run_with_evidence["results"][0]["metadata"]["evidence_ids"] == ["EVD-001"]

    assert main(
        [
            "generate-bug",
            "--workspace",
            str(workspace),
            "--run",
            "runs/RUN-001.json",
            "--case",
            "TC-001",
        ]
    ) == 0
    bug_json = workspace / "bugs" / "BUG-001.json"
    bug_md = workspace / "bugs" / "BUG-001.md"
    assert bug_json.exists()
    assert bug_md.exists()

    failure_memory_dir = workspace / "failure_memory"
    failure_record_path = failure_memory_dir / "record.json"
    failure_record_path.write_text(
        json.dumps(
            [
                {
                    "record_id": "FMEM-001",
                    "signature": {
                        "signature_id": "FSIG-001",
                        "fingerprint": "FP-AAAA",
                        "module": "Authentication",
                        "test_case_id": "TC-001",
                        "title": "Login success - positive path",
                        "symptom": "Login intermittently fails",
                        "expected_result": "User reaches dashboard.",
                        "actual_result": "Intermittent login failure.",
                        "environment": "staging",
                        "build": "v1.0.0",
                        "severity": "Major",
                        "priority": "High",
                        "source_bug_id": "BUG-001",
                        "tags": [],
                        "created_at": "2024-01-04T00:00:00Z",
                        "metadata": {},
                    },
                    "occurrence_count": 2,
                    "first_seen": "2024-01-04T00:00:00Z",
                    "last_seen": "2024-01-04T00:01:00Z",
                    "related_bug_ids": ["BUG-001"],
                    "related_run_ids": ["RUN-001"],
                    "related_test_case_ids": ["TC-001"],
                    "notes": [],
                    "metadata": {},
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    assert main(["score-automation", "--workspace", str(workspace)]) == 0
    candidates_json = workspace / "automation_candidates" / "candidates.json"
    candidates_md = workspace / "automation_candidates" / "candidates.md"
    assert candidates_json.exists()
    assert candidates_md.exists()


def test_validate_workspace_succeeds_for_created_workspace(tmp_path):
    workspace = tmp_path / "manual_qa_demo"

    assert main(["init-workspace", "--path", str(workspace)]) == 0

    assert main(["validate-workspace", "--workspace", str(workspace)]) == 0


def test_validate_workspace_fails_for_missing_path_or_invalid_workspace(tmp_path):
    missing_workspace = tmp_path / "missing_workspace"
    invalid_workspace = tmp_path / "invalid_workspace"
    invalid_workspace.mkdir()

    assert main(["validate-workspace", "--workspace", str(missing_workspace)]) == 1
    assert main(["validate-workspace", "--workspace", str(invalid_workspace)]) == 1


def test_workspace_summary_writes_summary_files(tmp_path):
    workspace = tmp_path / "manual_qa_demo"
    requirements_path = tmp_path / "requirements.md"
    _write_requirements(requirements_path)
    _run_base_cli_workflow(workspace, requirements_path)

    exit_code = main(["workspace-summary", "--workspace", str(workspace)])

    assert exit_code == 0
    assert (workspace / "reports" / "workspace_summary.json").exists()
    assert (workspace / "reports" / "workspace_summary.md").exists()


def test_demo_workflow_creates_expected_files(tmp_path):
    workspace = tmp_path / "manual_qa_demo"

    exit_code = main(["demo-workflow", "--workspace", str(workspace)])

    assert exit_code == 0
    assert (workspace / "project.json").exists()
    assert (workspace / "requirements" / "normalized_requirements.json").exists()
    assert (workspace / "checklists" / "checklist.json").exists()
    assert (workspace / "testcases" / "testcases.json").exists()
    assert (workspace / "suites" / "demo-smoke.json").exists()
    assert (workspace / "runs" / "RUN-001.json").exists()
    assert (workspace / "evidence" / "EVD-001.json").exists()
    assert (workspace / "bugs" / "BUG-001.json").exists()
    assert (workspace / "automation_candidates" / "candidates.json").exists()
    assert (workspace / "reports" / "demo_workflow_report.json").exists()
    assert (workspace / "reports" / "demo_workflow_report.md").exists()


def test_script_readiness_command_writes_reports_and_prints_summary(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    requirements_path = tmp_path / "requirements.md"
    _write_requirements(requirements_path)
    _run_base_cli_workflow(workspace, requirements_path)

    exit_code = main(["script-readiness", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (workspace / "reports" / "script_readiness.json").exists()
    assert (workspace / "reports" / "script_readiness.md").exists()
    assert "Script readiness:" in captured.out
    assert "total=" in captured.out


def test_script_readiness_missing_testcases_returns_non_zero(tmp_path):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0

    exit_code = main(["script-readiness", "--workspace", str(workspace)])

    assert exit_code == 1


def test_generate_api_drafts_writes_reports_and_python_draft(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    (workspace / "project.json").write_text(
        json.dumps(
            {
                "project_id": "order-api-demo",
                "name": "Order API Demo",
                "product_type": "api",
                "description": "",
                "owner": "",
                "tags": [],
                "metadata": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_api_testcases(workspace)
    assert main(["script-readiness", "--workspace", str(workspace)]) == 0

    exit_code = main(["generate-api-drafts", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (workspace / "script_drafts" / "api" / "api_script_drafts.json").exists()
    assert (workspace / "script_drafts" / "api" / "api_script_drafts.md").exists()
    python_drafts = list((workspace / "script_drafts" / "api").glob("*.py"))
    assert len(python_drafts) >= 1
    assert "API script drafts:" in captured.out
    assert "generated_drafts=1" in captured.out


def test_generate_api_drafts_handles_no_eligible_cases_clearly(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    requirements_path = tmp_path / "requirements.md"
    _write_requirements(requirements_path)
    _run_base_cli_workflow(workspace, requirements_path)

    exit_code = main(["generate-api-drafts", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (workspace / "script_drafts" / "api" / "api_script_drafts.json").exists()
    assert (workspace / "script_drafts" / "api" / "api_script_drafts.md").exists()
    assert list((workspace / "script_drafts" / "api").glob("*.py")) == []
    assert "generated_drafts=0" in captured.out


def test_validate_api_drafts_writes_validation_and_package_reports(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    (workspace / "project.json").write_text(
        json.dumps(
            {
                "project_id": "order-api-demo",
                "name": "Order API Demo",
                "product_type": "api",
                "description": "",
                "owner": "",
                "tags": [],
                "metadata": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_api_testcases(workspace)
    assert main(["script-readiness", "--workspace", str(workspace)]) == 0
    assert main(["generate-api-drafts", "--workspace", str(workspace)]) == 0

    exit_code = main(["validate-api-drafts", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (workspace / "script_drafts" / "api" / "api_script_validation.json").exists()
    assert (workspace / "script_drafts" / "api" / "api_script_validation.md").exists()
    assert (workspace / "script_drafts" / "api" / "api_script_package_manifest.json").exists()
    assert (workspace / "script_drafts" / "api" / "api_script_package_manifest.md").exists()
    assert "API draft validation:" in captured.out
    assert "package status" not in captured.out.lower() or "status=" in captured.out


def test_validate_api_drafts_handles_missing_drafts_file_clearly(tmp_path):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0

    exit_code = main(["validate-api-drafts", "--workspace", str(workspace)])

    assert exit_code == 1


def test_web_playwright_readiness_writes_reports_and_prints_summary(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    (workspace / "project.json").write_text(
        json.dumps(
            {
                "project_id": "portal-web-demo",
                "name": "Portal Web Demo",
                "product_type": "web",
                "description": "",
                "owner": "",
                "tags": [],
                "metadata": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_web_ui_testcases(workspace)
    assert main(["script-readiness", "--workspace", str(workspace)]) == 0

    exit_code = main(["web-playwright-readiness", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (workspace / "reports" / "web_playwright_readiness.json").exists()
    assert (workspace / "reports" / "web_playwright_readiness.md").exists()
    assert "Web Playwright readiness:" in captured.out
    assert "total_evaluated=1" in captured.out
    assert list(workspace.rglob("*.spec.ts")) == []


def test_web_playwright_readiness_handles_no_eligible_cases_clearly(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    (workspace / "project.json").write_text(
        json.dumps(
            {
                "project_id": "order-api-demo",
                "name": "Order API Demo",
                "product_type": "api",
                "description": "",
                "owner": "",
                "tags": [],
                "metadata": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_api_testcases(workspace)
    assert main(["script-readiness", "--workspace", str(workspace)]) == 0

    exit_code = main(["web-playwright-readiness", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (workspace / "reports" / "web_playwright_readiness.json").exists()
    assert (workspace / "reports" / "web_playwright_readiness.md").exists()
    assert "total_evaluated=0" in captured.out
    assert list(workspace.rglob("*.spec.ts")) == []


def test_generate_web_playwright_drafts_writes_reports_and_python_draft(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    (workspace / "project.json").write_text(
        json.dumps(
            {
                "project_id": "portal-web-demo",
                "name": "Portal Web Demo",
                "product_type": "web",
                "description": "",
                "owner": "",
                "tags": [],
                "metadata": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_web_ui_testcases(workspace)
    assert main(["script-readiness", "--workspace", str(workspace)]) == 0
    assert main(["web-playwright-readiness", "--workspace", str(workspace)]) == 0

    exit_code = main(["generate-web-playwright-drafts", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (workspace / "script_drafts" / "web_playwright" / "web_playwright_script_drafts.json").exists()
    assert (workspace / "script_drafts" / "web_playwright" / "web_playwright_script_drafts.md").exists()
    python_drafts = list((workspace / "script_drafts" / "web_playwright").glob("*.py"))
    assert len(python_drafts) >= 1
    assert "Web Playwright script drafts:" in captured.out
    assert "generated_drafts=1" in captured.out
    assert list(workspace.rglob("*.spec.ts")) == []


def test_generate_web_playwright_drafts_handles_no_eligible_cases_clearly(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    (workspace / "project.json").write_text(
        json.dumps(
            {
                "project_id": "order-api-demo",
                "name": "Order API Demo",
                "product_type": "api",
                "description": "",
                "owner": "",
                "tags": [],
                "metadata": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_api_testcases(workspace)
    assert main(["script-readiness", "--workspace", str(workspace)]) == 0
    assert main(["web-playwright-readiness", "--workspace", str(workspace)]) == 0

    exit_code = main(["generate-web-playwright-drafts", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (workspace / "script_drafts" / "web_playwright" / "web_playwright_script_drafts.json").exists()
    assert (workspace / "script_drafts" / "web_playwright" / "web_playwright_script_drafts.md").exists()
    assert list((workspace / "script_drafts" / "web_playwright").glob("*.py")) == []
    assert "generated_drafts=0" in captured.out


def test_validate_web_playwright_drafts_writes_validation_and_package_reports(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    (workspace / "project.json").write_text(
        json.dumps(
            {
                "project_id": "portal-web-demo",
                "name": "Portal Web Demo",
                "product_type": "web",
                "description": "",
                "owner": "",
                "tags": [],
                "metadata": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_web_ui_testcases(workspace)
    assert main(["script-readiness", "--workspace", str(workspace)]) == 0
    assert main(["web-playwright-readiness", "--workspace", str(workspace)]) == 0
    assert main(["generate-web-playwright-drafts", "--workspace", str(workspace)]) == 0

    exit_code = main(["validate-web-playwright-drafts", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (workspace / "script_drafts" / "web_playwright" / "web_playwright_validation.json").exists()
    assert (workspace / "script_drafts" / "web_playwright" / "web_playwright_validation.md").exists()
    assert (workspace / "script_drafts" / "web_playwright" / "web_playwright_package_manifest.json").exists()
    assert (workspace / "script_drafts" / "web_playwright" / "web_playwright_package_manifest.md").exists()
    assert "Web Playwright draft validation:" in captured.out
    assert "status=" in captured.out
    assert list(workspace.rglob("*.spec.ts")) == []


def test_validate_web_playwright_drafts_handles_missing_drafts_file_clearly(tmp_path):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0

    exit_code = main(["validate-web-playwright-drafts", "--workspace", str(workspace)])

    assert exit_code == 1


def test_draft_package_summary_writes_reports(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    _write_api_package_manifest(workspace)
    _write_web_package_manifest(workspace)

    exit_code = main(["draft-package-summary", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (workspace / "reports" / "draft_package_summary.json").exists()
    assert (workspace / "reports" / "draft_package_summary.md").exists()
    assert "Draft package summary:" in captured.out
    assert "overall_status=Ready for Review" in captured.out


def test_draft_package_summary_handles_missing_manifests_with_missing_status(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0

    exit_code = main(["draft-package-summary", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (workspace / "reports" / "draft_package_summary.json").exists()
    assert (workspace / "reports" / "draft_package_summary.md").exists()
    payload = json.loads((workspace / "reports" / "draft_package_summary.json").read_text(encoding="utf-8"))
    assert payload["overall_status"] == "Missing"
    assert "Generate and validate draft packages first" in captured.out


def test_draft_package_summary_prints_concise_summary(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    _write_api_package_manifest(workspace)

    exit_code = main(["draft-package-summary", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "overall_status=Needs Attention" in captured.out
    assert "total_drafts=1" in captured.out
    assert "total_valid=1" in captured.out
    assert "total_invalid=0" in captured.out
    assert "total_warnings=0" in captured.out
    assert "recommended_next_step=Resolve warnings and TODOs before execution planning" in captured.out


def test_draft_package_summary_does_not_execute_drafts(tmp_path, monkeypatch):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    _write_api_package_manifest(workspace)
    api_script_path = workspace / "script_drafts" / "api" / "test_api_tc_001.py"
    api_script_path.write_text("raise RuntimeError('should never be executed')", encoding="utf-8")

    original_read_text = Path.read_text

    def _guarded_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.suffix == ".py":
            raise AssertionError("Draft script files must not be read by the summary command.")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _guarded_read_text)

    exit_code = main(["draft-package-summary", "--workspace", str(workspace)])

    assert exit_code == 0


def test_execution_preflight_writes_reports(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    _write_execution_api_draft_package(workspace)

    exit_code = main(["execution-preflight", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (workspace / "reports" / "execution_preflight_plan.json").exists()
    assert (workspace / "reports" / "execution_preflight_plan.md").exists()
    assert "Execution preflight:" in captured.out


def test_execution_preflight_handles_missing_packages(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0

    exit_code = main(["execution-preflight", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads((workspace / "reports" / "execution_preflight_plan.json").read_text(encoding="utf-8"))
    assert payload["overall_decision"] == "Missing Draft Packages"
    assert "Generate and validate API/Web draft packages first" in captured.out


def test_execution_preflight_prints_summary(tmp_path, capsys):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    _write_execution_api_draft_package(workspace)

    exit_code = main(["execution-preflight", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "overall_decision=Needs Attention" in captured.out
    assert "total_targets=1" in captured.out
    assert "allowed_count=0" in captured.out
    assert "blocked_count=0" in captured.out
    assert "needs_approval_count=1" in captured.out
    assert "dry_run_only=True" in captured.out


def test_execution_preflight_does_not_execute_drafts(tmp_path, monkeypatch):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0
    _write_execution_api_draft_package(workspace)
    api_script_path = workspace / "script_drafts" / "api" / "test_api_tc_001.py"
    api_script_path.write_text("raise RuntimeError('should never be executed')", encoding="utf-8")

    original_read_text = Path.read_text

    def _guarded_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.suffix == ".py":
            raise AssertionError("Draft script files must not be read by the preflight command.")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _guarded_read_text)

    exit_code = main(["execution-preflight", "--workspace", str(workspace)])

    assert exit_code == 0


def test_invalid_missing_file_returns_non_zero(tmp_path):
    workspace = tmp_path / "manual_qa_demo"
    assert main(["init-workspace", "--path", str(workspace)]) == 0

    exit_code = main(
        [
            "import-requirements",
            "--workspace",
            str(workspace),
            "--input",
            str(tmp_path / "missing.md"),
        ]
    )

    assert exit_code == 1


def test_importing_manual_qa_still_does_not_import_mobile_dependencies():
    import orchestrator.manual_qa as manual_qa

    assert manual_qa is not None
    assert "mobile_appium" not in sys.modules
    assert "appium" not in sys.modules

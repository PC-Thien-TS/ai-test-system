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

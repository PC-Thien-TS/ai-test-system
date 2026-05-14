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


def test_init_workspace_creates_folders(tmp_path):
    workspace = tmp_path / "manual_qa_demo"

    exit_code = main(["init-workspace", "--path", str(workspace)])

    assert exit_code == 0
    assert (workspace / "requirements").exists()
    assert (workspace / "reports").exists()


def test_end_to_end_cli_workflow_writes_expected_artifacts(tmp_path):
    workspace = tmp_path / "manual_qa_demo"
    requirements_path = tmp_path / "requirements.md"
    _write_requirements(requirements_path)

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
    assert (workspace / "project.json").exists()

    assert main(
        [
            "import-requirements",
            "--workspace",
            str(workspace),
            "--input",
            str(requirements_path),
        ]
    ) == 0
    normalized_requirements = workspace / "requirements" / "normalized_requirements.json"
    assert normalized_requirements.exists()

    assert main(["generate-checklist", "--workspace", str(workspace)]) == 0
    assert (workspace / "checklists" / "checklist.json").exists()
    assert (workspace / "checklists" / "checklist.md").exists()

    assert main(["generate-testcases", "--workspace", str(workspace)]) == 0
    testcases_json = workspace / "testcases" / "testcases.json"
    testcases_md = workspace / "testcases" / "testcases.md"
    assert testcases_json.exists()
    assert testcases_md.exists()

    assert main(
        [
            "create-suite",
            "--workspace",
            str(workspace),
            "--name",
            "smoke",
        ]
    ) == 0
    suite_json = workspace / "suites" / "smoke.json"
    assert suite_json.exists()

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
    failure_memory_dir.mkdir(exist_ok=True)
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

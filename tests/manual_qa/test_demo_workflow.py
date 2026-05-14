from __future__ import annotations

from orchestrator.manual_qa.demo_service import run_demo_workflow


def test_run_demo_workflow_completes_end_to_end(tmp_path):
    workspace = tmp_path / "manual_qa_demo"

    result = run_demo_workflow(workspace)

    assert result["project_id"] == "manual-qa-demo"
    assert result["requirement_count"] == 2
    assert result["checklist_count"] == 2
    assert result["test_case_count"] == 3
    assert result["suite_id"] == "SUITE-001"
    assert result["run_id"] == "RUN-001"
    assert result["failed_case_id"] == "TC-001"
    assert result["evidence_id"] == "EVD-001"
    assert result["bug_id"] == "BUG-001"
    assert result["candidate_count"] == 3
    assert result["validation_result"]["is_valid"] is True


def test_run_demo_workflow_creates_expected_artifacts(tmp_path):
    workspace = tmp_path / "manual_qa_demo"

    result = run_demo_workflow(workspace)

    assert (workspace / "project.json").exists()
    assert (workspace / "requirements" / "normalized_requirements.json").exists()
    assert (workspace / "checklists" / "checklist.json").exists()
    assert (workspace / "checklists" / "checklist.md").exists()
    assert (workspace / "testcases" / "testcases.json").exists()
    assert (workspace / "testcases" / "testcases.md").exists()
    assert (workspace / "suites" / "demo-smoke.json").exists()
    assert (workspace / "suites" / "demo-smoke.md").exists()
    assert (workspace / "runs" / "RUN-001.json").exists()
    assert (workspace / "runs" / "RUN-001.md").exists()
    assert (workspace / "runs" / "RUN-001-summary.json").exists()
    assert (workspace / "runs" / "RUN-001-summary.md").exists()
    assert (workspace / "evidence" / "EVD-001.json").exists()
    assert (workspace / "evidence" / "EVD-001.md").exists()
    assert (workspace / "bugs" / "BUG-001.json").exists()
    assert (workspace / "bugs" / "BUG-001.md").exists()
    assert (workspace / "automation_candidates" / "candidates.json").exists()
    assert (workspace / "automation_candidates" / "candidates.md").exists()
    assert (workspace / "reports" / "demo_workflow_report.json").exists()
    assert (workspace / "reports" / "demo_workflow_report.md").exists()
    assert "reports/demo_workflow_report.json" in result["output_files"]
    assert "reports/demo_workflow_report.md" in result["output_files"]

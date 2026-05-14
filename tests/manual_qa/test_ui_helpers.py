from __future__ import annotations

import importlib
import sys
from pathlib import Path

from orchestrator.manual_qa.demo_service import run_demo_workflow
from orchestrator.manual_qa.models import ManualTestCase
from orchestrator.manual_qa.script_readiness_service import ScriptReadinessService
from orchestrator.manual_qa.ui_helpers import (
    format_artifact_count_summary,
    get_artifact_preview,
    get_next_recommended_actions,
    get_workspace_health,
    get_workspace_summary,
    list_api_draft_files,
    list_report_files,
    load_api_script_drafts,
    load_project,
    load_requirements,
    load_script_readiness_items,
    load_testcases,
    resolve_workspace,
    safe_load_json_artifact,
    summarize_bugs_for_ui,
    summarize_candidates_for_ui,
    summarize_run_for_ui,
    validate_workspace_for_ui,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


def test_resolve_workspace_returns_path(tmp_path):
    workspace = resolve_workspace(tmp_path / "manual_qa_demo")

    assert isinstance(workspace, Path)
    assert workspace.name == "manual_qa_demo"


def test_validate_workspace_for_ui_handles_missing_workspace(tmp_path):
    validation = validate_workspace_for_ui(tmp_path / "missing_workspace")

    assert validation["is_valid"] is False
    assert "does not exist" in validation["message"].lower()


def test_get_workspace_health_on_missing_workspace(tmp_path):
    health = get_workspace_health(tmp_path / "missing_workspace")

    assert health["exists"] is False
    assert health["health_level"] == "missing"


def test_get_workspace_health_on_initialized_workspace(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    health = get_workspace_health(workspace)

    assert health["exists"] is True
    assert health["is_valid"] is True
    assert health["health_level"] == "healthy"


def test_get_next_recommended_actions_for_empty_workspace(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    actions = get_next_recommended_actions(workspace)

    assert any("project" in action.lower() for action in actions)
    assert any("requirements" in action.lower() for action in actions)


def test_get_next_recommended_actions_after_demo_workflow(tmp_path):
    workspace = tmp_path / "manual_qa_demo"
    run_demo_workflow(workspace)

    actions = get_next_recommended_actions(workspace)

    assert any("review bug drafts" in action.lower() or "automation" in action.lower() for action in actions)


def test_get_workspace_summary_handles_empty_workspace(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    summary = get_workspace_summary(workspace)

    assert summary["exists"] is True
    assert summary["artifact_counts"]["requirements"] == 0
    assert summary["project"] == {}
    assert summary["validation"]["is_valid"] is True


def test_get_workspace_summary_handles_demo_workspace_artifacts(tmp_path):
    workspace = tmp_path / "manual_qa_demo"
    run_demo_workflow(workspace)

    summary = get_workspace_summary(workspace)

    assert summary["project"]["project_id"] == "manual-qa-demo"
    assert summary["artifact_counts"]["requirements"] == 1
    assert summary["artifact_counts"]["checklists"] == 2
    assert summary["artifact_counts"]["testcases"] == 2
    assert summary["artifact_counts"]["suites"] == 2
    assert summary["artifact_counts"]["runs"] == 4
    assert summary["artifact_counts"]["evidence"] == 2
    assert summary["artifact_counts"]["bugs"] == 2
    assert summary["artifact_counts"]["automation_candidates"] == 2
    assert summary["artifact_counts"]["reports"] == 2


def test_load_project_returns_empty_dict_when_project_missing(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    assert load_project(workspace) == {}


def test_load_requirements_returns_empty_list_when_missing(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    assert load_requirements(workspace) == []


def test_load_testcases_returns_empty_list_when_missing(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    assert load_testcases(workspace) == []


def test_safe_load_json_artifact_handles_missing_file(tmp_path):
    payload = safe_load_json_artifact(tmp_path / "missing.json")

    assert payload == {}


def test_get_artifact_preview_handles_missing_file(tmp_path):
    preview = get_artifact_preview(tmp_path / "missing.md")

    assert "not found" in preview.lower()


def test_list_report_files_returns_reports(tmp_path):
    workspace = tmp_path / "manual_qa_demo"
    run_demo_workflow(workspace)

    report_files = list_report_files(workspace)

    assert "reports/demo_workflow_report.json" in report_files
    assert "reports/demo_workflow_report.md" in report_files


def test_load_script_readiness_items_returns_report_items(tmp_path):
    workspace = tmp_path / "manual_qa_demo"
    run_demo_workflow(workspace)
    readiness_items = ScriptReadinessService().analyze_script_readiness_batch(
        [
            ManualTestCase(
                test_case_id="TC-500",
                requirement_ids=["REQ-500"],
                module="Order API",
                title="Create order endpoint",
                steps=["Send POST request to /api/orders."],
                expected_result="Status code is 201.",
            )
        ]
    )
    ManualQAWorkspaceService().write_json(
        workspace / "reports" / "script_readiness.json",
        [item.to_dict() for item in readiness_items],
    )

    loaded = load_script_readiness_items(workspace)

    assert loaded[0]["readiness_id"] == "READ-001"


def test_load_api_script_drafts_and_list_files_returns_artifacts(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    draft_dir = workspace / "script_drafts" / "api"
    draft_dir.mkdir(parents=True, exist_ok=True)
    (draft_dir / "api_script_drafts.json").write_text(
        '[{"draft_id":"API-DRAFT-001","test_case_id":"TC-900","requirement_ids":["REQ-900"],'
        '"module":"Order API","title":"Create order endpoint","readiness_id":"READ-900",'
        '"target_type":"api","framework":"pytest-requests","language":"python","file_name":"test_tc_900.py",'
        '"script_content":"import requests","status":"Draft","warnings":[],"assumptions":[],"metadata":{},'
        '"created_at":"2024-01-08T00:00:00Z"}]',
        encoding="utf-8",
    )
    (draft_dir / "api_script_drafts.md").write_text("# API Script Drafts", encoding="utf-8")
    (draft_dir / "test_tc_900.py").write_text("import requests", encoding="utf-8")

    loaded = load_api_script_drafts(workspace)
    files = list_api_draft_files(workspace)

    assert loaded[0]["draft_id"] == "API-DRAFT-001"
    assert "script_drafts/api/api_script_drafts.json" in files
    assert "script_drafts/api/test_tc_900.py" in files


def test_summarize_run_for_ui_handles_empty_missing_data():
    summary = summarize_run_for_ui({})

    assert summary["run_id"] == ""
    assert summary["total"] == 0
    assert summary["pass_rate"] == 0.0


def test_summarize_candidates_for_ui_handles_candidate_list():
    summary = summarize_candidates_for_ui(
        [
            {
                "candidate_id": "AUTO-001",
                "score": 80,
                "recommendation": "Should Automate",
            },
            {
                "candidate_id": "AUTO-002",
                "score": 50,
                "recommendation": "Consider Later",
            },
        ]
    )

    assert summary["count"] == 2
    assert summary["average_score"] == 65.0
    assert summary["recommendations"]["Should Automate"] == 1


def test_summarize_bugs_for_ui_handles_bug_list():
    summary = summarize_bugs_for_ui(
        [
            {
                "bug_id": "BUG-001",
                "severity": "Major",
                "status": "Draft",
            },
            {
                "bug_id": "BUG-002",
                "severity": "Minor",
                "status": "Draft",
            },
        ]
    )

    assert summary["count"] == 2
    assert summary["statuses"]["Draft"] == 2
    assert summary["severities"]["Major"] == 1


def test_format_artifact_count_summary_returns_readable_string():
    summary = format_artifact_count_summary({"requirements": 1, "checklists": 2})

    assert "requirements: 1" in summary
    assert "checklists: 2" in summary


def test_importing_ui_modules_does_not_import_mobile_dependencies():
    helpers_module = importlib.import_module("orchestrator.manual_qa.ui_helpers")
    streamlit_module = importlib.import_module("orchestrator.manual_qa.ui_streamlit")

    assert helpers_module is not None
    assert streamlit_module is not None
    assert hasattr(streamlit_module, "main")
    assert "mobile_appium" not in sys.modules
    assert "appium" not in sys.modules


def test_importing_ui_streamlit_does_not_execute_ui_flow_automatically():
    module = importlib.import_module("orchestrator.manual_qa.ui_streamlit")

    assert hasattr(module, "ManualQAStreamlitUI")
    assert hasattr(module, "main")

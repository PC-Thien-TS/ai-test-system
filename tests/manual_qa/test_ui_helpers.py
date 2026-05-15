from __future__ import annotations

import importlib
import sys
from pathlib import Path

from orchestrator.manual_qa.demo_service import run_demo_workflow
from orchestrator.manual_qa.models import ManualTestCase
from orchestrator.manual_qa.script_readiness_service import ScriptReadinessService
from orchestrator.manual_qa.ui_helpers import (
    get_api_execution_evidence_preview,
    get_api_execution_history_preview,
    get_api_execution_results_preview,
    format_artifact_count_summary,
    get_artifact_preview,
    get_draft_package_summary_preview,
    get_execution_preflight_preview,
    get_next_recommended_actions,
    get_workspace_health,
    get_workspace_summary,
    list_api_draft_files,
    list_api_validation_files,
    list_web_playwright_draft_files,
    list_web_playwright_validation_files,
    load_api_execution_evidence,
    load_api_execution_history,
    load_api_execution_results,
    load_api_execution_summary,
    load_api_execution_trend_summary,
    load_draft_package_summary,
    load_execution_preflight_plan,
    list_report_files,
    load_api_script_drafts,
    load_api_script_package_manifest,
    load_api_script_validation_results,
    load_web_playwright_script_drafts,
    load_web_playwright_validation_results,
    load_web_playwright_package_manifest,
    load_project,
    load_requirements,
    load_script_readiness_items,
    load_web_playwright_readiness_items,
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


def test_load_api_validation_and_package_manifest_artifacts(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    draft_dir = workspace / "script_drafts" / "api"
    draft_dir.mkdir(parents=True, exist_ok=True)
    (draft_dir / "api_script_validation.json").write_text(
        '[{"validation_id":"APIVAL-001","draft_id":"API-DRAFT-001","test_case_id":"TC-900","file_name":"test_tc_900.py",'
        '"is_valid":true,"syntax_valid":true,"has_draft_warning":true,"has_no_execution_marker":true,'
        '"has_status_assertion":true,"has_todo_endpoint":false,"has_todo_payload":false,"issues":[],'
        '"metadata":{},"created_at":"2024-01-09T00:00:00Z"}]',
        encoding="utf-8",
    )
    (draft_dir / "api_script_package_manifest.json").write_text(
        '{"package_id":"APIPKG-001","package_name":"api-script-drafts","draft_count":1,"valid_count":1,'
        '"invalid_count":0,"warning_count":0,"draft_files":["test_tc_900.py"],'
        '"validation_report_files":["script_drafts/api/api_script_validation.json"],'
        '"generated_at":"2024-01-10T00:00:00Z","status":"Ready for Review","metadata":{}}',
        encoding="utf-8",
    )
    (draft_dir / "api_script_validation.md").write_text("# API Script Validation Report", encoding="utf-8")
    (draft_dir / "api_script_package_manifest.md").write_text("# API Script Package Manifest", encoding="utf-8")

    validation_results = load_api_script_validation_results(workspace)
    manifest = load_api_script_package_manifest(workspace)
    files = list_api_validation_files(workspace)

    assert validation_results[0]["validation_id"] == "APIVAL-001"
    assert manifest["package_id"] == "APIPKG-001"
    assert "script_drafts/api/api_script_validation.json" in files
    assert "script_drafts/api/api_script_package_manifest.md" in files


def test_load_web_playwright_readiness_items_returns_report_items(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    (workspace / "reports" / "web_playwright_readiness.json").write_text(
        '[{"readiness_id":"WPREAD-001","test_case_id":"TC-901","requirement_ids":["REQ-901"],'
        '"module":"Portal UI","title":"Login page submit flow","readiness_status":"Ready",'
        '"readiness_score":80,"page_url":"/login","selector_hints":["data-testid=login-email"],'
        '"action_hints":["click"],"assertion_hints":["url contains"],"gaps":[],"strengths":["Selectors present"],'
        '"suggested_next_step":"Proceed to Playwright script draft generation","automation_candidate_id":"AUTO-001",'
        '"created_at":"2024-01-11T00:00:00Z","metadata":{}}]',
        encoding="utf-8",
    )

    loaded = load_web_playwright_readiness_items(workspace)

    assert loaded[0]["readiness_id"] == "WPREAD-001"


def test_load_web_playwright_script_drafts_and_list_files_returns_artifacts(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    draft_dir = workspace / "script_drafts" / "web_playwright"
    draft_dir.mkdir(parents=True, exist_ok=True)
    (draft_dir / "web_playwright_script_drafts.json").write_text(
        '[{"draft_id":"WEB-DRAFT-001","test_case_id":"TC-901","requirement_ids":["REQ-901"],'
        '"module":"Portal UI","title":"Login page submit flow","readiness_id":"WPREAD-001",'
        '"framework":"playwright-python","language":"python","file_name":"test_tc_901.py",'
        '"script_content":"from playwright.sync_api import Page, expect","status":"Draft",'
        '"warnings":[],"assumptions":[],"metadata":{},"created_at":"2024-01-12T00:00:00Z"}]',
        encoding="utf-8",
    )
    (draft_dir / "web_playwright_script_drafts.md").write_text("# Web Playwright Script Drafts", encoding="utf-8")
    (draft_dir / "test_tc_901.py").write_text("from playwright.sync_api import Page, expect", encoding="utf-8")

    loaded = load_web_playwright_script_drafts(workspace)
    files = list_web_playwright_draft_files(workspace)

    assert loaded[0]["draft_id"] == "WEB-DRAFT-001"
    assert "script_drafts/web_playwright/web_playwright_script_drafts.json" in files
    assert "script_drafts/web_playwright/test_tc_901.py" in files


def test_load_web_playwright_validation_and_package_manifest_artifacts(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    draft_dir = workspace / "script_drafts" / "web_playwright"
    draft_dir.mkdir(parents=True, exist_ok=True)
    (draft_dir / "web_playwright_validation.json").write_text(
        '[{"validation_id":"WPVAL-001","draft_id":"WEB-DRAFT-001","test_case_id":"TC-901","file_name":"test_tc_901.py",'
        '"is_valid":true,"syntax_valid":true,"has_draft_warning":true,"has_no_execution_marker":true,'
        '"has_playwright_import":true,"has_test_function":true,"has_page_goto":true,"has_locator_or_todo":true,'
        '"has_action_or_todo":true,"has_assertion_or_todo":true,"has_todo_page_url":false,"has_todo_selector":false,'
        '"has_todo_assertion":false,"issues":[],"metadata":{},"created_at":"2024-01-13T00:00:00Z"}]',
        encoding="utf-8",
    )
    (draft_dir / "web_playwright_package_manifest.json").write_text(
        '{"package_id":"WPPKG-001","package_name":"web-playwright-script-drafts","draft_count":1,"valid_count":1,'
        '"invalid_count":0,"warning_count":0,"draft_files":["test_tc_901.py"],'
        '"validation_report_files":["script_drafts/web_playwright/web_playwright_validation.json"],'
        '"generated_at":"2024-01-14T00:00:00Z","status":"Ready for Review","metadata":{}}',
        encoding="utf-8",
    )
    (draft_dir / "web_playwright_validation.md").write_text("# Web Playwright Validation Report", encoding="utf-8")
    (draft_dir / "web_playwright_package_manifest.md").write_text("# Web Playwright Package Manifest", encoding="utf-8")

    validation_results = load_web_playwright_validation_results(workspace)
    manifest = load_web_playwright_package_manifest(workspace)
    files = list_web_playwright_validation_files(workspace)

    assert validation_results[0]["validation_id"] == "WPVAL-001"
    assert manifest["package_id"] == "WPPKG-001"
    assert "script_drafts/web_playwright/web_playwright_validation.json" in files
    assert "script_drafts/web_playwright/web_playwright_package_manifest.md" in files


def test_load_draft_package_summary_handles_missing_summary(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    assert load_draft_package_summary(workspace) == {}


def test_load_draft_package_summary_loads_existing_summary(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    summary_path = workspace / "reports" / "draft_package_summary.json"
    summary_path.write_text(
        '{"summary_id":"DRAFT-SUM-001","workspace_path":"demo","total_groups":2,"total_drafts":1,'
        '"total_valid":1,"total_invalid":0,"total_warnings":0,"ready_groups":1,'
        '"needs_attention_groups":1,"invalid_groups":0,"missing_groups":1,"groups":[],'
        '"overall_status":"Needs Attention","recommended_next_step":"Resolve warnings and TODOs before execution planning",'
        '"created_at":"2024-01-15T00:00:00Z","metadata":{}}',
        encoding="utf-8",
    )

    loaded = load_draft_package_summary(workspace)

    assert loaded["summary_id"] == "DRAFT-SUM-001"
    assert loaded["overall_status"] == "Needs Attention"


def test_get_draft_package_summary_preview_returns_friendly_empty_state(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    preview = get_draft_package_summary_preview(workspace)

    assert "no draft package summary generated yet" in preview.lower()


def test_load_execution_preflight_plan_handles_missing_file(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    assert load_execution_preflight_plan(workspace) == {}


def test_get_execution_preflight_preview_returns_friendly_state(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    preview = get_execution_preflight_preview(workspace)

    assert "no execution preflight plan generated yet" in preview.lower()


def test_load_api_execution_results_handles_missing_file(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    assert load_api_execution_results(workspace) == []


def test_get_api_execution_results_preview_returns_friendly_state(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    preview = get_api_execution_results_preview(workspace)

    assert "no api sandbox execution results generated yet" in preview.lower()


def test_load_api_execution_evidence_handles_missing_file(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    assert load_api_execution_evidence(workspace) == []


def test_load_api_execution_summary_handles_missing_file(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    assert load_api_execution_summary(workspace) == {}


def test_get_api_execution_evidence_preview_returns_friendly_state(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    preview = get_api_execution_evidence_preview(workspace)

    assert "no api execution evidence report generated yet" in preview.lower()


def test_load_api_execution_history_handles_missing_file(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    assert load_api_execution_history(workspace) == []


def test_load_api_execution_trend_summary_handles_missing_file(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    assert load_api_execution_trend_summary(workspace) == {}


def test_get_api_execution_history_preview_returns_friendly_state(tmp_path):
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    preview = get_api_execution_history_preview(workspace)

    assert "no api execution history report generated yet" in preview.lower()


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

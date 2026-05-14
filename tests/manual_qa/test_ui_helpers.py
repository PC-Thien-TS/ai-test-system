from __future__ import annotations

import importlib
import sys
from pathlib import Path

from orchestrator.manual_qa.demo_service import run_demo_workflow
from orchestrator.manual_qa.ui_helpers import (
    format_artifact_count_summary,
    get_workspace_summary,
    load_project,
    load_requirements,
    load_testcases,
    resolve_workspace,
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

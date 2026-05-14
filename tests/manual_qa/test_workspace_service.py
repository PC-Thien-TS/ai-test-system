from __future__ import annotations

from orchestrator.manual_qa.models import ProjectProfile
from orchestrator.manual_qa.workspace_service import (
    WORKSPACE_MANIFEST_FILENAME,
    WORKSPACE_SUBFOLDERS,
    ManualQAWorkspaceService,
)


def test_creates_workspace_folders_under_tmp_path(tmp_path):
    service = ManualQAWorkspaceService()

    workspace = service.create_workspace(tmp_path / "manual_qa_demo")

    assert workspace.exists()
    assert (workspace / WORKSPACE_MANIFEST_FILENAME).exists()
    for folder in WORKSPACE_SUBFOLDERS:
        assert (workspace / folder).exists()


def test_writes_and_reads_json(tmp_path):
    service = ManualQAWorkspaceService()
    path = tmp_path / "sample.json"
    payload = {"name": "demo", "count": 1}

    service.write_json(path, payload)

    assert service.read_json(path) == payload


def test_writes_and_reads_markdown_and_text(tmp_path):
    service = ManualQAWorkspaceService()
    path = tmp_path / "sample.md"
    text = "# Demo\n\ncontent"

    service.write_markdown(path, text)

    assert service.read_text(path) == text


def test_creates_reads_and_updates_workspace_manifest(tmp_path):
    service = ManualQAWorkspaceService()
    workspace = service.create_workspace(tmp_path / "manual_qa_demo")
    project = ProjectProfile(
        project_id="demo-web",
        name="Demo Web",
        product_type="web",
    )

    created = service.create_workspace_manifest(workspace, project=project, metadata={"phase": "5b"})
    read_back = service.read_workspace_manifest(workspace)
    updated = service.update_workspace_manifest(workspace, metadata={"owner": "qa"})

    assert created["project_id"] == "demo-web"
    assert read_back["project_name"] == "Demo Web"
    assert updated["metadata"]["phase"] == "5b"
    assert updated["metadata"]["owner"] == "qa"
    assert updated["workspace_version"]


def test_validates_complete_workspace(tmp_path):
    service = ManualQAWorkspaceService()
    workspace = service.create_workspace(tmp_path / "manual_qa_demo")
    service.write_json(workspace / "project.json", {"project_id": "demo-web", "name": "Demo Web"})
    service.write_json(
        workspace / "requirements" / "normalized_requirements.json",
        [{"requirement_id": "REQ-001", "title": "Login success", "description": "Login success"}],
    )
    service.write_json(workspace / "checklists" / "checklist.json", [{"checklist_id": "CHK-001"}])
    service.update_workspace_manifest(
        workspace,
        metadata={"project_expected": True},
    )

    validation = service.validate_workspace(workspace)

    assert validation.is_valid is True
    assert validation.missing_folders == []
    assert validation.missing_files == []


def test_detects_missing_required_folder(tmp_path):
    service = ManualQAWorkspaceService()
    workspace = service.create_workspace(tmp_path / "manual_qa_demo")
    (workspace / "reports").rmdir()

    validation = service.validate_workspace(workspace)

    assert validation.is_valid is False
    assert "reports" in validation.missing_folders


def test_lists_workspace_artifact_counts(tmp_path):
    service = ManualQAWorkspaceService()
    workspace = service.create_workspace(tmp_path / "manual_qa_demo")
    service.write_json(workspace / "project.json", {"project_id": "demo-web"})
    service.write_json(workspace / "requirements" / "normalized_requirements.json", [{"id": "REQ-001"}])
    service.write_markdown(workspace / "reports" / "workspace_summary.md", "# Summary")

    listing = service.list_workspace_artifacts(workspace)

    assert listing["artifact_counts"]["requirements"] == 1
    assert listing["artifact_counts"]["reports"] == 1
    assert "project.json" in listing["root_files"]

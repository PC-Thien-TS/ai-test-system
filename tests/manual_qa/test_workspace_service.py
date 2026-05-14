from __future__ import annotations

from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService, WORKSPACE_SUBFOLDERS


def test_creates_workspace_folders_under_tmp_path(tmp_path):
    service = ManualQAWorkspaceService()

    workspace = service.create_workspace(tmp_path / "manual_qa_demo")

    assert workspace.exists()
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

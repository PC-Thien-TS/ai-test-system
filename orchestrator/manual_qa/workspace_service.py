"""Local workspace helpers for the Manual QA CLI adapter."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from orchestrator.manual_qa.models import ProjectProfile, WorkspaceValidationResult


WORKSPACE_SUBFOLDERS = (
    "requirements",
    "checklists",
    "testcases",
    "suites",
    "runs",
    "evidence",
    "bugs",
    "failure_memory",
    "automation_candidates",
    "reports",
)

WORKSPACE_MANIFEST_FILENAME = "workspace_manifest.json"
WORKSPACE_VERSION = "manual_qa_workspace_v1"


class ManualQAWorkspaceService:
    """Thin local file helpers for Manual QA CLI workflows."""

    _BASE_TIME = datetime(2024, 1, 6, 0, 0, 0)

    def __init__(self) -> None:
        self._next_timestamp_offset = 0

    def create_workspace(self, path: str | Path) -> Path:
        workspace_path = Path(path)
        workspace_path.mkdir(parents=True, exist_ok=True)
        for folder in WORKSPACE_SUBFOLDERS:
            (workspace_path / folder).mkdir(parents=True, exist_ok=True)
        manifest_path = workspace_path / WORKSPACE_MANIFEST_FILENAME
        if not manifest_path.exists():
            self.create_workspace_manifest(workspace_path)
        return workspace_path

    def create_workspace_manifest(
        self,
        workspace_path: str | Path,
        project: ProjectProfile | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace = self._ensure_workspace(workspace_path)
        manifest_path = workspace / WORKSPACE_MANIFEST_FILENAME
        existing = self.read_json(manifest_path) if manifest_path.exists() else {}
        timestamp = self._next_timestamp()
        listing = self.list_workspace_artifacts(workspace)
        project_data = self._project_data(project)

        manifest = {
            "workspace_version": WORKSPACE_VERSION,
            "created_by": "manual_qa_cli",
            "project_id": project_data.get("project_id", existing.get("project_id", "")),
            "project_name": project_data.get("name", existing.get("project_name", "")),
            "product_type": project_data.get("product_type", existing.get("product_type", "")),
            "created_at": existing.get("created_at") or timestamp,
            "updated_at": timestamp,
            "folders": list(WORKSPACE_SUBFOLDERS),
            "artifact_counts": listing["artifact_counts"],
            "metadata": {
                **dict(existing.get("metadata") or {}),
                **dict(metadata or {}),
            },
        }
        self.write_json(manifest_path, manifest)
        return manifest

    def read_workspace_manifest(self, workspace_path: str | Path) -> dict[str, Any]:
        manifest_path = Path(workspace_path) / WORKSPACE_MANIFEST_FILENAME
        return self.read_json(manifest_path)

    def update_workspace_manifest(
        self,
        workspace_path: str | Path,
        project: ProjectProfile | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.create_workspace_manifest(workspace_path, project=project, metadata=metadata)

    def validate_workspace(self, workspace_path: str | Path) -> WorkspaceValidationResult:
        workspace = Path(workspace_path)
        if not workspace.exists():
            return WorkspaceValidationResult(
                is_valid=False,
                missing_folders=list(WORKSPACE_SUBFOLDERS),
                missing_files=[],
                warnings=["Workspace path does not exist."],
                artifact_counts={folder: 0 for folder in WORKSPACE_SUBFOLDERS},
                metadata={
                    "workspace_path": str(workspace),
                    "manifest_exists": False,
                },
            )

        missing_folders = [
            folder for folder in WORKSPACE_SUBFOLDERS if not (workspace / folder).exists()
        ]
        listing = self.list_workspace_artifacts(workspace)
        manifest_path = workspace / WORKSPACE_MANIFEST_FILENAME
        manifest = self.read_json(manifest_path) if manifest_path.exists() else {}
        missing_files: list[str] = []
        warnings: list[str] = []

        if not manifest_path.exists():
            warnings.append("Workspace manifest is missing.")

        project_expected = self._project_is_expected(listing, manifest)
        project_path = workspace / "project.json"
        if project_expected and not project_path.exists():
            missing_files.append("project.json")

        requirements_expected = self._requirements_are_expected(listing)
        requirements_path = workspace / "requirements" / "normalized_requirements.json"
        if requirements_expected and not requirements_path.exists():
            missing_files.append("requirements/normalized_requirements.json")

        return WorkspaceValidationResult(
            is_valid=not missing_folders and not missing_files,
            missing_folders=missing_folders,
            missing_files=missing_files,
            warnings=warnings,
            artifact_counts=listing["artifact_counts"],
            metadata={
                "workspace_path": str(workspace),
                "manifest_exists": manifest_path.exists(),
                "root_files": listing["root_files"],
            },
        )

    def list_workspace_artifacts(self, workspace_path: str | Path) -> dict[str, Any]:
        workspace = Path(workspace_path)
        artifact_counts = {folder: 0 for folder in WORKSPACE_SUBFOLDERS}
        artifacts = {folder: [] for folder in WORKSPACE_SUBFOLDERS}

        if workspace.exists():
            for folder in WORKSPACE_SUBFOLDERS:
                folder_path = workspace / folder
                if not folder_path.exists():
                    continue
                files = sorted(
                    str(path.relative_to(workspace)).replace("\\", "/")
                    for path in folder_path.rglob("*")
                    if path.is_file()
                )
                artifacts[folder] = files
                artifact_counts[folder] = len(files)

            root_files = sorted(
                path.name
                for path in workspace.iterdir()
                if path.is_file()
            )
        else:
            root_files = []

        return {
            "workspace_path": str(workspace),
            "folders": list(WORKSPACE_SUBFOLDERS),
            "artifact_counts": artifact_counts,
            "artifacts": artifacts,
            "root_files": root_files,
        }

    def write_json(self, path: str | Path, data: Any) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        return output_path

    def read_json(self, path: str | Path) -> Any:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def write_markdown(self, path: str | Path, text: str) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(str(text), encoding="utf-8")
        return output_path

    def read_text(self, path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")

    def _ensure_workspace(self, workspace_path: str | Path) -> Path:
        workspace = Path(workspace_path)
        workspace.mkdir(parents=True, exist_ok=True)
        for folder in WORKSPACE_SUBFOLDERS:
            (workspace / folder).mkdir(parents=True, exist_ok=True)
        return workspace

    def _project_data(self, project: ProjectProfile | dict[str, Any] | None) -> dict[str, Any]:
        if project is None:
            return {}
        if isinstance(project, ProjectProfile):
            return project.to_dict()
        return dict(project)

    def _project_is_expected(self, listing: dict[str, Any], manifest: dict[str, Any]) -> bool:
        if manifest.get("project_id") or manifest.get("project_name"):
            return True
        relevant_folders = (
            "requirements",
            "checklists",
            "testcases",
            "suites",
            "runs",
            "evidence",
            "bugs",
            "failure_memory",
            "automation_candidates",
        )
        return any(listing["artifact_counts"].get(folder, 0) > 0 for folder in relevant_folders)

    def _requirements_are_expected(self, listing: dict[str, Any]) -> bool:
        relevant_folders = (
            "checklists",
            "testcases",
            "suites",
            "runs",
            "evidence",
            "bugs",
            "automation_candidates",
        )
        return any(listing["artifact_counts"].get(folder, 0) > 0 for folder in relevant_folders)

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_WORKSPACE_SERVICE = ManualQAWorkspaceService()


def create_workspace(path: str | Path) -> Path:
    return _DEFAULT_WORKSPACE_SERVICE.create_workspace(path)


def create_workspace_manifest(
    workspace_path: str | Path,
    project: ProjectProfile | dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _DEFAULT_WORKSPACE_SERVICE.create_workspace_manifest(
        workspace_path,
        project=project,
        metadata=metadata,
    )


def read_workspace_manifest(workspace_path: str | Path) -> dict[str, Any]:
    return _DEFAULT_WORKSPACE_SERVICE.read_workspace_manifest(workspace_path)


def update_workspace_manifest(
    workspace_path: str | Path,
    project: ProjectProfile | dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _DEFAULT_WORKSPACE_SERVICE.update_workspace_manifest(
        workspace_path,
        project=project,
        metadata=metadata,
    )


def validate_workspace(workspace_path: str | Path) -> WorkspaceValidationResult:
    return _DEFAULT_WORKSPACE_SERVICE.validate_workspace(workspace_path)


def list_workspace_artifacts(workspace_path: str | Path) -> dict[str, Any]:
    return _DEFAULT_WORKSPACE_SERVICE.list_workspace_artifacts(workspace_path)


def write_json(path: str | Path, data: Any) -> Path:
    return _DEFAULT_WORKSPACE_SERVICE.write_json(path, data)


def read_json(path: str | Path) -> Any:
    return _DEFAULT_WORKSPACE_SERVICE.read_json(path)


def write_markdown(path: str | Path, text: str) -> Path:
    return _DEFAULT_WORKSPACE_SERVICE.write_markdown(path, text)


def read_text(path: str | Path) -> str:
    return _DEFAULT_WORKSPACE_SERVICE.read_text(path)

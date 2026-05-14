"""Local workspace helpers for the Manual QA CLI adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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


class ManualQAWorkspaceService:
    """Thin local file helpers for Manual QA CLI workflows."""

    def create_workspace(self, path: str | Path) -> Path:
        workspace_path = Path(path)
        workspace_path.mkdir(parents=True, exist_ok=True)
        for folder in WORKSPACE_SUBFOLDERS:
            (workspace_path / folder).mkdir(parents=True, exist_ok=True)
        return workspace_path

    def write_json(self, path: str | Path, data: Any) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
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


_DEFAULT_WORKSPACE_SERVICE = ManualQAWorkspaceService()


def create_workspace(path: str | Path) -> Path:
    return _DEFAULT_WORKSPACE_SERVICE.create_workspace(path)


def write_json(path: str | Path, data: Any) -> Path:
    return _DEFAULT_WORKSPACE_SERVICE.write_json(path, data)


def read_json(path: str | Path) -> Any:
    return _DEFAULT_WORKSPACE_SERVICE.read_json(path)


def write_markdown(path: str | Path, text: str) -> Path:
    return _DEFAULT_WORKSPACE_SERVICE.write_markdown(path, text)


def read_text(path: str | Path) -> str:
    return _DEFAULT_WORKSPACE_SERVICE.read_text(path)

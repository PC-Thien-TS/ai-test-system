"""Helper utilities for the local Manual QA Streamlit prototype."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.manual_qa.workspace_service import (
    WORKSPACE_SUBFOLDERS,
    ManualQAWorkspaceService,
)


DEFAULT_UI_WORKSPACE = Path("artifacts/manual_qa_demo")


def resolve_workspace(path: str | Path | None) -> Path:
    raw_path = Path(path) if path else DEFAULT_UI_WORKSPACE
    return raw_path.expanduser().resolve(strict=False)


def get_workspace_summary(workspace_path: str | Path | None) -> dict[str, Any]:
    workspace = resolve_workspace(workspace_path)
    service = ManualQAWorkspaceService()
    exists = workspace.exists()
    validation = validate_workspace_for_ui(workspace)
    listing = service.list_workspace_artifacts(workspace) if exists else {
        "artifact_counts": {folder: 0 for folder in WORKSPACE_SUBFOLDERS},
        "artifacts": {folder: [] for folder in WORKSPACE_SUBFOLDERS},
        "root_files": [],
    }
    manifest = _safe_read_json(workspace / "workspace_manifest.json")
    project = load_project(workspace)

    return {
        "workspace_path": str(workspace),
        "exists": exists,
        "project": project,
        "manifest": manifest,
        "artifact_counts": listing["artifact_counts"],
        "artifact_count_summary": format_artifact_count_summary(listing["artifact_counts"]),
        "validation": validation,
        "reports": listing["artifacts"].get("reports", []),
        "root_files": listing.get("root_files", []),
    }


def load_project(workspace_path: str | Path | None) -> dict[str, Any]:
    return _safe_read_json(resolve_workspace(workspace_path) / "project.json")


def load_requirements(workspace_path: str | Path | None) -> list[dict[str, Any]]:
    return _safe_read_list(resolve_workspace(workspace_path) / "requirements" / "normalized_requirements.json")


def load_checklist(workspace_path: str | Path | None) -> list[dict[str, Any]]:
    return _safe_read_list(resolve_workspace(workspace_path) / "checklists" / "checklist.json")


def load_testcases(workspace_path: str | Path | None) -> list[dict[str, Any]]:
    return _safe_read_list(resolve_workspace(workspace_path) / "testcases" / "testcases.json")


def load_suites(workspace_path: str | Path | None) -> list[dict[str, Any]]:
    return _load_directory_json_objects(resolve_workspace(workspace_path) / "suites")


def load_runs(workspace_path: str | Path | None) -> list[dict[str, Any]]:
    directory = resolve_workspace(workspace_path) / "runs"
    items = []
    for item in _load_directory_json_objects(directory):
        run_id = str(item.get("run_id", ""))
        if run_id:
            items.append(item)
    return items


def load_bugs(workspace_path: str | Path | None) -> list[dict[str, Any]]:
    return _load_directory_json_objects(resolve_workspace(workspace_path) / "bugs")


def load_automation_candidates(workspace_path: str | Path | None) -> list[dict[str, Any]]:
    return _safe_read_list(resolve_workspace(workspace_path) / "automation_candidates" / "candidates.json")


def load_failure_memory_records(workspace_path: str | Path | None) -> list[dict[str, Any]]:
    directory = resolve_workspace(workspace_path) / "failure_memory"
    records: list[dict[str, Any]] = []
    if not directory.exists():
        return records

    for path in sorted(directory.glob("*.json")):
        payload = _safe_read_json(path)
        if isinstance(payload, list):
            records.extend(item for item in payload if isinstance(item, dict))
        elif isinstance(payload, dict):
            records.append(payload)
    return records


def format_artifact_count_summary(artifact_counts: dict[str, int] | None) -> str:
    counts = artifact_counts or {}
    if not counts:
        return "No artifacts found."
    return ", ".join(f"{name}: {counts.get(name, 0)}" for name in WORKSPACE_SUBFOLDERS)


def validate_workspace_for_ui(workspace_path: str | Path | None) -> dict[str, Any]:
    workspace = resolve_workspace(workspace_path)
    result = ManualQAWorkspaceService().validate_workspace(workspace).to_dict()
    if not workspace.exists():
        message = "Workspace does not exist yet."
    elif result["is_valid"]:
        message = "Workspace is valid."
    else:
        problems = []
        if result["missing_folders"]:
            problems.append(f"missing folders: {', '.join(result['missing_folders'])}")
        if result["missing_files"]:
            problems.append(f"missing files: {', '.join(result['missing_files'])}")
        message = "Workspace has issues: " + "; ".join(problems or ["unknown validation issue"])
    result["message"] = message
    return result


def _safe_read_json(path: Path) -> dict[str, Any]:
    try:
        payload = ManualQAWorkspaceService().read_json(path)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_read_list(path: Path) -> list[dict[str, Any]]:
    try:
        payload = ManualQAWorkspaceService().read_json(path)
    except FileNotFoundError:
        return []
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _load_directory_json_objects(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []

    items: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        if path.name.endswith("-summary.json"):
            continue
        payload = _safe_read_json(path)
        if payload:
            items.append(payload)
    return items

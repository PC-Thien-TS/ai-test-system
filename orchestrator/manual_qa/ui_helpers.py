"""Helper utilities for the local Manual QA Streamlit prototype."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestrator.manual_qa.workspace_service import (
    WORKSPACE_SUBFOLDERS,
    ManualQAWorkspaceService,
)


DEFAULT_UI_WORKSPACE = Path("artifacts/manual_qa_demo")
_WORKSPACE_SERVICE = ManualQAWorkspaceService()


def resolve_workspace(path: str | Path | None) -> Path:
    raw_path = Path(path) if path else DEFAULT_UI_WORKSPACE
    return raw_path.expanduser().resolve(strict=False)


def get_workspace_summary(workspace_path: str | Path | None) -> dict[str, Any]:
    workspace = resolve_workspace(workspace_path)
    exists = workspace.exists()
    listing = _WORKSPACE_SERVICE.list_workspace_artifacts(workspace) if exists else _empty_listing(workspace)
    validation = validate_workspace_for_ui(workspace)
    health = get_workspace_health(workspace)
    manifest = safe_load_json_artifact(workspace / "workspace_manifest.json")
    project = load_project(workspace)
    return {
        "workspace_path": str(workspace),
        "exists": exists,
        "project": project,
        "manifest": manifest,
        "artifact_counts": listing["artifact_counts"],
        "artifact_count_summary": format_artifact_count_summary(listing["artifact_counts"]),
        "validation": validation,
        "health": health,
        "reports": listing["artifacts"].get("reports", []),
        "root_files": listing.get("root_files", []),
    }


def get_workspace_health(workspace_path: str | Path | None) -> dict[str, Any]:
    workspace = resolve_workspace(workspace_path)
    summary = get_workspace_summary_core(workspace)
    validation = summary["validation"]
    counts = summary["artifact_counts"]
    health_level = "healthy" if validation["is_valid"] else "attention"
    if not summary["exists"]:
        health_level = "missing"
    return {
        "workspace_path": str(workspace),
        "exists": summary["exists"],
        "health_level": health_level,
        "is_valid": validation["is_valid"],
        "message": validation["message"],
        "artifact_counts": counts,
        "artifact_count_summary": format_artifact_count_summary(counts),
    }


def get_next_recommended_actions(workspace_path: str | Path | None) -> list[str]:
    workspace = resolve_workspace(workspace_path)
    if not workspace.exists():
        return [
            "Initialize the workspace.",
            "Create a project profile.",
            "Import requirements or run the demo workflow.",
        ]

    project = load_project(workspace)
    requirements = load_requirements(workspace)
    checklist = load_checklist(workspace)
    testcases = load_testcases(workspace)
    suites = load_suites(workspace)
    runs = load_runs(workspace)
    bugs = load_bugs(workspace)
    candidates = load_automation_candidates(workspace)
    readiness_items = load_script_readiness_items(workspace)
    web_playwright_readiness_items = load_web_playwright_readiness_items(workspace)

    actions: list[str] = []
    if not project:
        actions.append("Create a project profile.")
    if not requirements:
        actions.append("Import and normalize requirements.")
    if requirements and not checklist:
        actions.append("Generate a checklist from the normalized requirements.")
    if requirements and not testcases:
        actions.append("Generate manual test cases.")
    if testcases and not suites:
        actions.append("Create a suite from the available test cases.")
    if suites and not runs:
        actions.append("Create a run for one of the suites.")
    if runs:
        run_summary = summarize_run_for_ui(runs[0])
        if run_summary["not_run"] > 0:
            actions.append("Update run results to capture pass, fail, or blocked outcomes.")
        if run_summary["failed"] > 0 and not bugs:
            actions.append("Attach evidence metadata and generate a bug draft for failed results.")
    if testcases and not candidates:
        actions.append("Score automation candidates for the current test cases.")
    if testcases and not readiness_items:
        actions.append("Generate a script readiness report before attempting draft generation.")
    if readiness_items and not web_playwright_readiness_items:
        if any(item.get("target_type") in {"web_ui", "manual_only"} for item in readiness_items):
            actions.append("Generate a Web Playwright readiness report for web UI-like cases.")
    if load_api_script_drafts(workspace) and not load_api_script_validation_results(workspace):
        actions.append("Validate generated API draft artifacts and review the package manifest.")
    if bugs and candidates:
        actions.append("Review bug drafts and automation recommendations.")

    if not actions:
        actions.append("Workspace is in a good state. Review reports or run the demo workflow again.")
    return actions


def get_artifact_preview(path: str | Path, max_chars: int = 4000) -> str:
    artifact_path = Path(path)
    if not artifact_path.exists():
        return f"Artifact not found: {artifact_path}"

    try:
        text = artifact_path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"Unable to read artifact: {exc}"

    preview = text[:max_chars]
    if len(text) > max_chars:
        preview += "\n\n... preview truncated ..."
    return preview


def safe_load_json_artifact(path: str | Path) -> dict[str, Any]:
    artifact_path = Path(path)
    try:
        payload = _WORKSPACE_SERVICE.read_json(artifact_path)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def list_report_files(workspace_path: str | Path | None) -> list[str]:
    return _list_artifacts_by_folder(workspace_path, "reports")


def list_run_files(workspace_path: str | Path | None) -> list[str]:
    return [
        item for item in _list_artifacts_by_folder(workspace_path, "runs")
        if item.endswith(".json") and not item.endswith("-summary.json")
    ]


def list_suite_files(workspace_path: str | Path | None) -> list[str]:
    return [item for item in _list_artifacts_by_folder(workspace_path, "suites") if item.endswith(".json")]


def list_bug_files(workspace_path: str | Path | None) -> list[str]:
    return [item for item in _list_artifacts_by_folder(workspace_path, "bugs") if item.endswith(".json")]


def list_candidate_files(workspace_path: str | Path | None) -> list[str]:
    return [item for item in _list_artifacts_by_folder(workspace_path, "automation_candidates") if item.endswith(".json")]


def list_api_draft_files(workspace_path: str | Path | None) -> list[str]:
    workspace = resolve_workspace(workspace_path)
    draft_dir = workspace / "script_drafts" / "api"
    if not draft_dir.exists():
        return []
    return sorted(
        str(path.relative_to(workspace)).replace("\\", "/")
        for path in draft_dir.iterdir()
        if path.is_file()
    )


def list_api_validation_files(workspace_path: str | Path | None) -> list[str]:
    workspace = resolve_workspace(workspace_path)
    draft_dir = workspace / "script_drafts" / "api"
    if not draft_dir.exists():
        return []
    targets = {
        "api_script_validation.json",
        "api_script_validation.md",
        "api_script_package_manifest.json",
        "api_script_package_manifest.md",
    }
    return sorted(
        str(path.relative_to(workspace)).replace("\\", "/")
        for path in draft_dir.iterdir()
        if path.is_file() and path.name in targets
    )


def load_script_readiness_items(workspace_path: str | Path | None) -> list[dict[str, Any]]:
    return _safe_read_list(resolve_workspace(workspace_path) / "reports" / "script_readiness.json")


def load_web_playwright_readiness_items(workspace_path: str | Path | None) -> list[dict[str, Any]]:
    return _safe_read_list(resolve_workspace(workspace_path) / "reports" / "web_playwright_readiness.json")


def load_api_script_drafts(workspace_path: str | Path | None) -> list[dict[str, Any]]:
    return _safe_read_list(resolve_workspace(workspace_path) / "script_drafts" / "api" / "api_script_drafts.json")


def load_api_script_validation_results(workspace_path: str | Path | None) -> list[dict[str, Any]]:
    return _safe_read_list(resolve_workspace(workspace_path) / "script_drafts" / "api" / "api_script_validation.json")


def load_api_script_package_manifest(workspace_path: str | Path | None) -> dict[str, Any]:
    return safe_load_json_artifact(
        resolve_workspace(workspace_path) / "script_drafts" / "api" / "api_script_package_manifest.json"
    )


def load_project(workspace_path: str | Path | None) -> dict[str, Any]:
    return safe_load_json_artifact(resolve_workspace(workspace_path) / "project.json")


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
    items: list[dict[str, Any]] = []
    for item in _load_directory_json_objects(directory):
        if item.get("run_id"):
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
        try:
            payload = _WORKSPACE_SERVICE.read_json(path)
        except Exception:
            continue
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
    result = _WORKSPACE_SERVICE.validate_workspace(workspace).to_dict()
    if not workspace.exists():
        message = "Workspace does not exist yet."
    elif result["is_valid"]:
        message = "Workspace is valid."
    else:
        problems: list[str] = []
        if result["missing_folders"]:
            problems.append(f"missing folders: {', '.join(result['missing_folders'])}")
        if result["missing_files"]:
            problems.append(f"missing files: {', '.join(result['missing_files'])}")
        warnings = result.get("warnings") or []
        if warnings:
            problems.append(f"warnings: {', '.join(warnings)}")
        message = "Workspace has issues: " + "; ".join(problems or ["unknown validation issue"])
    result["message"] = message
    return result


def summarize_run_for_ui(run_dict: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(run_dict, dict):
        return {
            "run_id": "",
            "status": "Not Started",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "blocked": 0,
            "skipped": 0,
            "not_run": 0,
            "retest": 0,
            "pass_rate": 0.0,
            "tester": "",
            "environment": "",
            "build": "",
        }

    counts = {
        "Pass": 0,
        "Fail": 0,
        "Blocked": 0,
        "Skipped": 0,
        "Not Run": 0,
        "Retest": 0,
    }
    results = run_dict.get("results")
    if not isinstance(results, list):
        results = []
    for item in results:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "Not Run"))
        counts[status] = counts.get(status, 0) + 1

    total = len([item for item in results if isinstance(item, dict)])
    pass_rate = round((counts["Pass"] / total * 100.0), 2) if total else 0.0
    return {
        "run_id": str(run_dict.get("run_id", "")),
        "status": str(run_dict.get("status", "Not Started")),
        "total": total,
        "passed": counts.get("Pass", 0),
        "failed": counts.get("Fail", 0),
        "blocked": counts.get("Blocked", 0),
        "skipped": counts.get("Skipped", 0),
        "not_run": counts.get("Not Run", 0),
        "retest": counts.get("Retest", 0),
        "pass_rate": pass_rate,
        "tester": str(run_dict.get("tester", "")),
        "environment": str(run_dict.get("environment", "")),
        "build": str(run_dict.get("build", "")),
    }


def summarize_candidates_for_ui(candidate_items: list[dict[str, Any]] | None) -> dict[str, Any]:
    items = [item for item in (candidate_items or []) if isinstance(item, dict)]
    recommendations: dict[str, int] = {}
    for item in items:
        recommendation = str(item.get("recommendation", "Unknown"))
        recommendations[recommendation] = recommendations.get(recommendation, 0) + 1

    avg_score = round(
        sum(int(item.get("score", 0)) for item in items) / len(items),
        2,
    ) if items else 0.0
    return {
        "count": len(items),
        "average_score": avg_score,
        "recommendations": recommendations,
        "top_candidate_id": str(items[0].get("candidate_id", "")) if items else "",
    }


def summarize_bugs_for_ui(bug_items: list[dict[str, Any]] | None) -> dict[str, Any]:
    items = [item for item in (bug_items or []) if isinstance(item, dict)]
    statuses: dict[str, int] = {}
    severities: dict[str, int] = {}
    for item in items:
        status = str(item.get("status", "Unknown"))
        severity = str(item.get("severity", "Unknown"))
        statuses[status] = statuses.get(status, 0) + 1
        severities[severity] = severities.get(severity, 0) + 1

    return {
        "count": len(items),
        "statuses": statuses,
        "severities": severities,
        "top_bug_id": str(items[0].get("bug_id", "")) if items else "",
    }


def get_workspace_summary_core(workspace_path: str | Path | None) -> dict[str, Any]:
    workspace = resolve_workspace(workspace_path)
    exists = workspace.exists()
    listing = _WORKSPACE_SERVICE.list_workspace_artifacts(workspace) if exists else _empty_listing(workspace)
    validation = validate_workspace_for_ui(workspace)
    return {
        "workspace": workspace,
        "exists": exists,
        "artifact_counts": listing["artifact_counts"],
        "listing": listing,
        "validation": validation,
    }


def _list_artifacts_by_folder(workspace_path: str | Path | None, folder: str) -> list[str]:
    workspace = resolve_workspace(workspace_path)
    if not workspace.exists():
        return []
    listing = _WORKSPACE_SERVICE.list_workspace_artifacts(workspace)
    return list(listing["artifacts"].get(folder, []))


def _safe_read_list(path: Path) -> list[dict[str, Any]]:
    try:
        payload = _WORKSPACE_SERVICE.read_json(path)
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
        payload = safe_load_json_artifact(path)
        if payload:
            items.append(payload)
    return items


def _empty_listing(workspace: Path) -> dict[str, Any]:
    return {
        "workspace_path": str(workspace),
        "folders": list(WORKSPACE_SUBFOLDERS),
        "artifact_counts": {folder: 0 for folder in WORKSPACE_SUBFOLDERS},
        "artifacts": {folder: [] for folder in WORKSPACE_SUBFOLDERS},
        "root_files": [],
    }

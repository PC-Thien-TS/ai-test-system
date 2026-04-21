from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_json_files_in_dir(path: Path) -> List[Dict[str, Any]]:
    if not path.exists() or not path.is_dir():
        return []
    output: List[Dict[str, Any]] = []
    for file_path in sorted(path.glob("*.json")):
        data = _read_json(file_path)
        if isinstance(data, dict):
            output.append(data)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    output.append(item)
    return output


class LocalDashboardArtifactReader:
    def __init__(self, artifact_root: Path) -> None:
        self.artifact_root = artifact_root
        self.candidate_root = self.artifact_root / "candidate_artifacts"

    def _shared_artifact(self, filename: str) -> Any:
        return _read_json(self.artifact_root / filename)

    def read_failure_memory_records(self) -> List[Dict[str, Any]]:
        return _read_json_files_in_dir(self.artifact_root / "failure_memory")

    def read_decision_records(self) -> List[Dict[str, Any]]:
        records = _read_json_files_in_dir(self.artifact_root / "decision_results")
        # Also support an optional repo-root release decision artifact format when copied into artifacts.
        extra = _read_json(self.artifact_root / "release_decision.json")
        if isinstance(extra, dict):
            records.append(extra)
        return records

    def read_self_healing_records(self) -> List[Dict[str, Any]]:
        return _read_json_files_in_dir(self.artifact_root / "self_healing_actions")

    def read_bug_candidates(self) -> List[Dict[str, Any]]:
        return _read_json_files_in_dir(self.candidate_root / "bugs")

    def read_incident_candidates(self) -> List[Dict[str, Any]]:
        return _read_json_files_in_dir(self.candidate_root / "incidents")

    def read_candidate_suppressions(self) -> List[Dict[str, Any]]:
        return _read_json_files_in_dir(self.candidate_root / "suppressions")

    def read_release_records(self) -> List[Dict[str, Any]]:
        records = _read_json_files_in_dir(self.artifact_root / "release")
        shared = self._shared_artifact("release_decision.json")
        if isinstance(shared, dict):
            records.append(shared)
        return records

    def read_ci_gate_records(self) -> List[Dict[str, Any]]:
        records = _read_json_files_in_dir(self.artifact_root / "ci_gate")
        shared = self._shared_artifact("ci_regression_gate_result.json")
        if isinstance(shared, dict):
            records.append(shared)
        return records

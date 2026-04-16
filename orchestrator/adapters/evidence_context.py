from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from orchestrator.adapters.loader import get_active_adapter_id


REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "adapter_evidence"


@dataclass(frozen=True)
class AdapterEvidenceContext:
    adapter_id: str
    repo_root: Path
    artifact_dir: Path
    report_dir: Path

    def ensure_dirs(self) -> None:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def get_release_decision_path(self) -> Path:
        return self.artifact_dir / "release_decision.json"

    def get_dashboard_snapshot_path(self) -> Path:
        return self.artifact_dir / "dashboard_snapshot.json"

    def get_defect_cluster_report_path(self) -> Path:
        return self.artifact_dir / "defect_cluster_report.json"

    def get_rerun_plan_path(self) -> Path:
        return self.artifact_dir / "autonomous_rerun_plan.json"

    def get_trend_history_path(self) -> Path:
        return self.artifact_dir / "qa_snapshot_history.json"

    def get_regression_plan_path(self) -> Path:
        return self.artifact_dir / "regression_execution_plan.json"

    def get_change_aware_plan_path(self) -> Path:
        return self.artifact_dir / "change_aware_regression_plan.json"

    def get_ci_gate_result_path(self) -> Path:
        return self.artifact_dir / "ci_regression_gate_result.json"

    def get_validation_report_path(self) -> Path:
        return self.artifact_dir / "adapter_validation_report.json"

    def get_report_path(self, report_name: str) -> Path:
        return self.report_dir / report_name

    def get_local_artifact_path(self, artifact_name: str) -> Path:
        mapping = {
            "release_decision": self.get_release_decision_path(),
            "dashboard_snapshot": self.get_dashboard_snapshot_path(),
            "defect_cluster_report": self.get_defect_cluster_report_path(),
            "autonomous_rerun_plan": self.get_rerun_plan_path(),
            "qa_snapshot_history": self.get_trend_history_path(),
            "regression_execution_plan": self.get_regression_plan_path(),
            "change_aware_regression_plan": self.get_change_aware_plan_path(),
            "ci_regression_gate_result": self.get_ci_gate_result_path(),
            "adapter_validation_report": self.get_validation_report_path(),
        }
        if artifact_name not in mapping:
            raise KeyError(f"Unknown artifact name: {artifact_name}")
        return mapping[artifact_name]

    def get_legacy_artifact_path(self, artifact_name: str) -> Path:
        mapping = {
            "release_decision": self.repo_root / "release_decision.json",
            "dashboard_snapshot": self.repo_root / "dashboard_snapshot.json",
            "defect_cluster_report": self.repo_root / "defect_cluster_report.json",
            "autonomous_rerun_plan": self.repo_root / "autonomous_rerun_plan.json",
            "qa_snapshot_history": self.repo_root / "qa_snapshot_history.json",
            "regression_execution_plan": self.repo_root / "regression_execution_plan.json",
            "change_aware_regression_plan": self.repo_root / "change_aware_regression_plan.json",
            "ci_regression_gate_result": self.repo_root / "ci_regression_gate_result.json",
            "adapter_validation_report": self.repo_root / "adapter_validation_report.json",
        }
        if artifact_name not in mapping:
            raise KeyError(f"Unknown artifact name: {artifact_name}")
        return mapping[artifact_name]

    def get_legacy_report_path(self, report_name: str) -> Path:
        return self.repo_root / "docs" / "wave1_runtime" / report_name

    def artifact_exists(self, artifact_name: str) -> bool:
        local_path = self.get_local_artifact_path(artifact_name)
        if local_path.exists():
            return True
        if self.adapter_id == "rankmate":
            return self.get_legacy_artifact_path(artifact_name).exists()
        return False

    def load_json(self, artifact_name: str) -> dict[str, Any]:
        local_path = self.get_local_artifact_path(artifact_name)
        for path in (local_path,):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(raw, dict):
                return raw

        if self.adapter_id == "rankmate":
            legacy_path = self.get_legacy_artifact_path(artifact_name)
            try:
                raw = json.loads(legacy_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return {}
            return raw if isinstance(raw, dict) else {}

        return {}

    def write_json(self, artifact_name: str, payload: dict[str, Any]) -> Path:
        self.ensure_dirs()
        local_path = self.get_local_artifact_path(artifact_name)
        local_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        if self.adapter_id == "rankmate":
            legacy_path = self.get_legacy_artifact_path(artifact_name)
            legacy_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return local_path

    def write_report(self, report_name: str, content: str) -> Path:
        self.ensure_dirs()
        local_path = self.get_report_path(report_name)
        local_path.write_text(content, encoding="utf-8")
        if self.adapter_id == "rankmate":
            legacy_path = self.get_legacy_report_path(report_name)
            legacy_path.parent.mkdir(parents=True, exist_ok=True)
            legacy_path.write_text(content, encoding="utf-8")
        return local_path

    def read_report_text(self, report_name: str) -> str:
        local_path = self.get_report_path(report_name)
        try:
            return local_path.read_text(encoding="utf-8")
        except OSError:
            pass
        if self.adapter_id == "rankmate":
            legacy_path = self.get_legacy_report_path(report_name)
            try:
                return legacy_path.read_text(encoding="utf-8")
            except OSError:
                return ""
        return ""

    def is_bootstrap_state(self) -> bool:
        required = (
            "release_decision",
            "dashboard_snapshot",
            "autonomous_rerun_plan",
            "defect_cluster_report",
        )
        return not all(self.artifact_exists(name) for name in required)


def get_adapter_evidence_context(adapter_name: str | None = None) -> AdapterEvidenceContext:
    adapter_id = (adapter_name or get_active_adapter_id()).strip().lower()
    if not adapter_id:
        adapter_id = "rankmate"
    artifact_dir = ADAPTER_ARTIFACT_ROOT / adapter_id
    report_dir = artifact_dir / "reports"
    return AdapterEvidenceContext(
        adapter_id=adapter_id,
        repo_root=REPO_ROOT,
        artifact_dir=artifact_dir,
        report_dir=report_dir,
    )


def get_adapter_artifact_dir(adapter_name: str | None = None) -> Path:
    return get_adapter_evidence_context(adapter_name).artifact_dir


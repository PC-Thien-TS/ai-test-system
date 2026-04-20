from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..domain.models import DashboardQueryFilter
from ..domain.trend_utils import filter_by_date_range
from .local_readers import LocalDashboardArtifactReader


def _matches_field(record: Dict[str, object], field_name: str, expected: str | None) -> bool:
    if not expected:
        return True
    expected_lower = expected.lower()
    direct = str(record.get(field_name, "")).lower()
    metadata = record.get("metadata", {}) or {}
    meta = str(metadata.get(field_name, "")).lower() if isinstance(metadata, dict) else ""
    return expected_lower in {direct, meta}


def _apply_filter(records: List[Dict[str, object]], q: DashboardQueryFilter) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for rec in records:
        if not _matches_field(rec, "adapter_id", q.adapter_id):
            continue
        if not _matches_field(rec, "project_id", q.project_id):
            continue
        if q.severity and str(rec.get("severity", "")).lower() != q.severity.lower():
            continue
        if q.owner and str(rec.get("recommended_owner", "")).lower() != q.owner.lower():
            continue
        if q.candidate_type and str(rec.get("artifact_type", "")).lower() != q.candidate_type.lower():
            continue
        if q.decision_type and str(rec.get("primary_decision", "")).upper() != q.decision_type.upper():
            continue
        out.append(rec)
    return filter_by_date_range(out, start_date=q.start_date, end_date=q.end_date)


@dataclass
class DashboardQueryRepository:
    reader: LocalDashboardArtifactReader

    def memory_records(self, q: DashboardQueryFilter) -> List[Dict[str, object]]:
        return _apply_filter(self.reader.read_failure_memory_records(), q)

    def decision_records(self, q: DashboardQueryFilter) -> List[Dict[str, object]]:
        return _apply_filter(self.reader.read_decision_records(), q)

    def self_healing_records(self, q: DashboardQueryFilter) -> List[Dict[str, object]]:
        return _apply_filter(self.reader.read_self_healing_records(), q)

    def bug_candidate_records(self, q: DashboardQueryFilter) -> List[Dict[str, object]]:
        return _apply_filter(self.reader.read_bug_candidates(), q)

    def incident_candidate_records(self, q: DashboardQueryFilter) -> List[Dict[str, object]]:
        return _apply_filter(self.reader.read_incident_candidates(), q)

    def candidate_suppression_records(self, q: DashboardQueryFilter) -> List[Dict[str, object]]:
        return _apply_filter(self.reader.read_candidate_suppressions(), q)

    def release_records(self, q: DashboardQueryFilter) -> List[Dict[str, object]]:
        return _apply_filter(self.reader.read_release_records(), q)

    def ci_gate_records(self, q: DashboardQueryFilter) -> List[Dict[str, object]]:
        return _apply_filter(self.reader.read_ci_gate_records(), q)


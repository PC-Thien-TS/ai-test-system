"""Metadata-only API execution history and trend reporting for Manual QA."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from orchestrator.manual_qa.exporters import ManualQAExporter
from orchestrator.manual_qa.models import (
    APIExecutionEvidence,
    APIExecutionHistoryEntry,
    APIExecutionSummary,
    APIExecutionTrendSummary,
    FailureSignature,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


class APIExecutionHistoryService:
    """Build historical API execution trend reports from saved local artifacts."""

    _BASE_TIME = datetime(2024, 1, 21, 0, 0, 0)

    def __init__(self) -> None:
        self._workspace_service = ManualQAWorkspaceService()
        self._exporter = ManualQAExporter()
        self._next_history_number = 1
        self._next_trend_number = 1
        self._next_timestamp_offset = 0

    def create_api_execution_history_entry(
        self,
        summary: APIExecutionSummary,
        *,
        source_file: str = "",
        run_label: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> APIExecutionHistoryEntry:
        label = str(run_label or "").strip() or Path(source_file).stem or summary.summary_id
        entry = APIExecutionHistoryEntry(
            history_id=f"API-HIST-{self._next_history_number:03d}",
            source_file=str(source_file or ""),
            run_label=label,
            summary_id=summary.summary_id,
            total=summary.total,
            passed=summary.passed,
            failed=summary.failed,
            blocked=summary.blocked,
            dry_run=summary.dry_run,
            error=summary.error,
            not_run=summary.not_run,
            pass_rate=summary.pass_rate,
            failure_rate=summary.failure_rate,
            status=summary.status,
            evidence_ids=list(summary.evidence_ids),
            bug_suggestion_ids=list(summary.bug_suggestion_ids),
            failure_signature_ids=list(summary.failure_signature_ids),
            created_at=summary.created_at or self._next_timestamp(),
            metadata={
                "source": "APIExecutionSummary",
                **dict(summary.metadata),
                **dict(metadata or {}),
            },
        )
        self._next_history_number += 1
        return entry

    def build_api_execution_history(
        self,
        *,
        current_summary: APIExecutionSummary | dict[str, Any] | None = None,
        historical_summaries: list[APIExecutionSummary | dict[str, Any]] | None = None,
        current_source_file: str = "reports/api_execution_summary.json",
        metadata: dict[str, Any] | None = None,
    ) -> list[APIExecutionHistoryEntry]:
        entries: list[APIExecutionHistoryEntry] = []
        if current_summary:
            summary = self._coerce_summary(current_summary)
            if summary is not None:
                entries.append(
                    self.create_api_execution_history_entry(
                        summary,
                        source_file=current_source_file,
                        run_label="current",
                        metadata=metadata,
                    )
                )
        for index, item in enumerate(historical_summaries or [], start=1):
            summary = self._coerce_summary(item)
            if summary is None:
                continue
            source_file = ""
            if isinstance(item, dict):
                source_file = str(item.get("_source_file", ""))
            entries.append(
                self.create_api_execution_history_entry(
                    summary,
                    source_file=source_file,
                    run_label=str(item.get("_run_label", "")) if isinstance(item, dict) else f"history-{index}",
                    metadata=metadata,
                )
            )
        return self._sort_entries(entries)

    def summarize_api_execution_trends(
        self,
        entries: list[APIExecutionHistoryEntry],
        *,
        repeated_failure_keys: list[str] | None = None,
        flaky_candidate_keys: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> APIExecutionTrendSummary:
        ordered_entries = self._sort_entries(entries)
        total_runs = len(ordered_entries)
        if total_runs == 0:
            trend = APIExecutionTrendSummary(
                trend_id=f"API-TREND-{self._next_trend_number:03d}",
                trend_status="No History",
                recommended_next_step="Build API execution evidence before trend review",
                metadata=dict(metadata or {}),
                created_at=self._next_timestamp(),
            )
            self._next_trend_number += 1
            return trend

        latest = ordered_entries[-1]
        total_executions = sum(item.total for item in ordered_entries)
        average_pass_rate = round(sum(item.pass_rate for item in ordered_entries) / total_runs, 2)
        average_failure_rate = round(sum(item.failure_rate for item in ordered_entries) / total_runs, 2)
        repeated_keys = sorted(set(repeated_failure_keys or []))
        flaky_keys = sorted(set(flaky_candidate_keys or []))

        trend = APIExecutionTrendSummary(
            trend_id=f"API-TREND-{self._next_trend_number:03d}",
            total_runs=total_runs,
            total_executions=total_executions,
            total_passed=sum(item.passed for item in ordered_entries),
            total_failed=sum(item.failed for item in ordered_entries),
            total_blocked=sum(item.blocked for item in ordered_entries),
            total_dry_run=sum(item.dry_run for item in ordered_entries),
            total_error=sum(item.error for item in ordered_entries),
            total_not_run=sum(item.not_run for item in ordered_entries),
            average_pass_rate=average_pass_rate,
            average_failure_rate=average_failure_rate,
            latest_status=latest.status,
            trend_status=self._trend_status(ordered_entries),
            repeated_failure_count=len(repeated_keys),
            flaky_candidate_count=len(flaky_keys),
            repeated_failure_keys=repeated_keys,
            flaky_candidate_keys=flaky_keys,
            entries=ordered_entries,
            recommended_next_step=self._trend_next_step(self._trend_status(ordered_entries)),
            metadata=dict(metadata or {}),
            created_at=self._next_timestamp(),
        )
        self._next_trend_number += 1
        return trend

    def detect_repeated_failures(
        self,
        evidence_items: list[APIExecutionEvidence | dict[str, Any]] | None = None,
        failure_signatures: list[FailureSignature | dict[str, Any]] | None = None,
    ) -> list[str]:
        counts: dict[str, int] = {}
        for item in evidence_items or []:
            evidence = self._coerce_evidence(item)
            if evidence is None or evidence.status not in {"Failed", "Error"}:
                continue
            keys = [
                self._normalize_failure_key("endpoint", f"{evidence.method} {evidence.endpoint}"),
                self._normalize_failure_key("test_case", evidence.test_case_id),
            ]
            if evidence.error_type:
                keys.append(self._normalize_failure_key("error_type", evidence.error_type))
            if evidence.http_status_code is not None and evidence.assertion_passed is False:
                keys.append(self._normalize_failure_key("status_mismatch", str(evidence.http_status_code)))
            for key in keys:
                counts[key] = counts.get(key, 0) + 1

        for item in failure_signatures or []:
            payload = item.to_dict() if hasattr(item, "to_dict") else item
            if not isinstance(payload, dict):
                continue
            method = str(payload.get("metadata", {}).get("method", "")).strip() if isinstance(payload.get("metadata"), dict) else ""
            endpoint = str(payload.get("metadata", {}).get("endpoint", "")).strip() if isinstance(payload.get("metadata"), dict) else ""
            test_case_id = str(payload.get("test_case_id", "")).strip()
            error_type = str(payload.get("metadata", {}).get("error_type", "")).strip() if isinstance(payload.get("metadata"), dict) else ""
            for raw_key in [f"{method} {endpoint}".strip(), test_case_id, error_type]:
                if raw_key:
                    key = self._normalize_failure_key("signature", raw_key)
                    counts[key] = counts.get(key, 0) + 1

        return sorted(key for key, count in counts.items() if count > 1)

    def detect_flaky_candidates(
        self,
        evidence_items: list[APIExecutionEvidence | dict[str, Any]] | None = None,
    ) -> list[str]:
        outcomes: dict[str, set[str]] = {}
        for item in evidence_items or []:
            evidence = self._coerce_evidence(item)
            if evidence is None:
                continue
            outcome = self._normalize_outcome(evidence.status)
            for raw_key in [evidence.test_case_id, f"{evidence.method} {evidence.endpoint}".strip()]:
                key = raw_key.strip()
                if not key:
                    continue
                outcomes.setdefault(key, set()).add(outcome)
        return sorted(key for key, values in outcomes.items() if "passed" in values and "failed" in values)

    def build_api_execution_history_report(
        self,
        *,
        history_entries: list[APIExecutionHistoryEntry],
        evidence_items: list[APIExecutionEvidence | dict[str, Any]] | None = None,
        failure_signatures: list[FailureSignature | dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        repeated_failures = self.detect_repeated_failures(evidence_items, failure_signatures=failure_signatures)
        flaky_candidates = self.detect_flaky_candidates(evidence_items)
        trend_summary = self.summarize_api_execution_trends(
            history_entries,
            repeated_failure_keys=repeated_failures,
            flaky_candidate_keys=flaky_candidates,
            metadata=metadata,
        )
        return {
            "history_entries": self._sort_entries(history_entries),
            "trend_summary": trend_summary,
            "repeated_failures": repeated_failures,
            "flaky_candidates": flaky_candidates,
            "metadata": {"sandbox_only": True, **dict(metadata or {})},
        }

    def build_api_execution_history_report_from_workspace(
        self,
        workspace_path: str | Path,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace = Path(workspace_path)
        current_summary_path = workspace / "reports" / "api_execution_summary.json"
        evidence_path = workspace / "evidence" / "api_execution_evidence.json"
        failure_signature_path = workspace / "failure_memory" / "api_execution_failure_signatures.json"
        history_dir = workspace / "history" / "api_execution"

        current_summary = self._load_json_object(current_summary_path)
        historical_summaries = self._load_historical_summaries(history_dir, exclude_name="api_execution_history.json")
        entries = self.build_api_execution_history(
            current_summary=current_summary,
            historical_summaries=historical_summaries,
            current_source_file=str(current_summary_path.relative_to(workspace)).replace("\\", "/") if current_summary_path.exists() else "reports/api_execution_summary.json",
            metadata=metadata,
        )
        evidence_items = self._load_evidence_items(evidence_path)
        failure_signatures = self._load_failure_signatures(failure_signature_path)
        report = self.build_api_execution_history_report(
            history_entries=entries,
            evidence_items=evidence_items,
            failure_signatures=failure_signatures,
            metadata=metadata,
        )

        history_json_path = history_dir / "api_execution_history.json"
        history_md_path = history_dir / "api_execution_history.md"
        trend_json_path = workspace / "reports" / "api_execution_trend_summary.json"
        trend_md_path = workspace / "reports" / "api_execution_trend_summary.md"

        self._exporter.export_json_file(report["history_entries"], history_json_path)
        self._workspace_service.write_markdown(
            history_md_path,
            self._exporter.export_markdown_string(report, title="API Execution History Report"),
        )
        self._exporter.export_json_file(report["trend_summary"], trend_json_path)
        self._exporter.export_markdown_file(report["trend_summary"], trend_md_path)
        self._workspace_service.update_workspace_manifest(workspace)
        return report

    def _trend_status(self, entries: list[APIExecutionHistoryEntry]) -> str:
        if not entries:
            return "No History"
        if all(item.status == "All Dry Run" for item in entries):
            return "All Dry Run"
        if len(entries) == 1:
            if entries[0].status == "Failed":
                return "Needs Review"
            return "Stable"

        latest = entries[-1]
        earlier = entries[:-1]
        earlier_average_pass = sum(item.pass_rate for item in earlier) / len(earlier)
        earlier_average_failure = sum(item.failure_rate for item in earlier) / len(earlier)
        earlier_failed_or_error = sum(item.failed + item.error for item in earlier) / len(earlier)
        latest_failed_or_error = latest.failed + latest.error

        if latest.status == "Failed" and any(item.status in {"Passed", "Needs Review"} for item in earlier):
            return "Regressing"
        if latest.failure_rate > earlier_average_failure + 5:
            return "Regressing"
        if latest.pass_rate > earlier_average_pass + 5 and latest_failed_or_error < earlier_failed_or_error:
            return "Improving"
        if abs(latest.pass_rate - earlier_average_pass) <= 5 and abs(latest.failure_rate - earlier_average_failure) <= 5:
            return "Stable"
        return "Needs Review"

    def _trend_next_step(self, trend_status: str) -> str:
        steps = {
            "No History": "Build API execution evidence before trend review",
            "All Dry Run": "Approve safe execution before relying on trend data",
            "Improving": "Continue monitoring improving sandbox outcomes before promotion",
            "Stable": "Monitor history and review repeated failure hotspots",
            "Regressing": "Investigate regressions before promoting scripts",
            "Needs Review": "Review mixed history and failure patterns",
        }
        return steps.get(trend_status, "Review mixed history and failure patterns")

    def _load_historical_summaries(self, history_dir: Path, *, exclude_name: str) -> list[dict[str, Any]]:
        if not history_dir.exists():
            return []
        items: list[dict[str, Any]] = []
        for path in sorted(history_dir.glob("api_execution_summary_*.json")):
            payload = self._load_json_object(path)
            if payload:
                payload["_source_file"] = str(path).replace("\\", "/")
                payload["_run_label"] = path.stem
                items.append(payload)
        if not items:
            for path in sorted(history_dir.glob("*.json")):
                if path.name == exclude_name or path.name.endswith("_evidence.json"):
                    continue
                payload = self._load_json_object(path)
                if payload and "summary_id" in payload:
                    payload["_source_file"] = str(path).replace("\\", "/")
                    payload["_run_label"] = path.stem
                    items.append(payload)
        return items

    def _load_json_object(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}

    def _load_evidence_items(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []

    def _load_failure_signatures(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []

    def _coerce_summary(self, item: APIExecutionSummary | dict[str, Any] | None) -> APIExecutionSummary | None:
        if item is None:
            return None
        if isinstance(item, APIExecutionSummary):
            return item
        if not isinstance(item, dict):
            return None
        return APIExecutionSummary(
            summary_id=str(item.get("summary_id", "")),
            total=int(item.get("total", 0) or 0),
            passed=int(item.get("passed", 0) or 0),
            failed=int(item.get("failed", 0) or 0),
            blocked=int(item.get("blocked", 0) or 0),
            dry_run=int(item.get("dry_run", 0) or 0),
            error=int(item.get("error", 0) or 0),
            not_run=int(item.get("not_run", 0) or 0),
            pass_rate=float(item.get("pass_rate", 0.0) or 0.0),
            failure_rate=float(item.get("failure_rate", 0.0) or 0.0),
            evidence_ids=list(item.get("evidence_ids", [])) if isinstance(item.get("evidence_ids"), list) else [],
            bug_suggestion_ids=list(item.get("bug_suggestion_ids", [])) if isinstance(item.get("bug_suggestion_ids"), list) else [],
            failure_signature_ids=list(item.get("failure_signature_ids", [])) if isinstance(item.get("failure_signature_ids"), list) else [],
            status=str(item.get("status", "No Results")),
            recommended_next_step=str(item.get("recommended_next_step", "")),
            metadata=dict(item.get("metadata", {})) if isinstance(item.get("metadata"), dict) else {},
            created_at=item.get("created_at"),
        )

    def _coerce_evidence(self, item: APIExecutionEvidence | dict[str, Any]) -> APIExecutionEvidence | None:
        if isinstance(item, APIExecutionEvidence):
            return item
        if not isinstance(item, dict):
            return None
        return APIExecutionEvidence(
            evidence_id=str(item.get("evidence_id", "")),
            execution_id=str(item.get("execution_id", "")),
            draft_id=str(item.get("draft_id", "")),
            test_case_id=str(item.get("test_case_id", "")),
            evidence_type=str(item.get("evidence_type", "api_execution_result")),
            title=str(item.get("title", "")),
            summary=str(item.get("summary", "")),
            status=str(item.get("status", "")),
            method=str(item.get("method", "")),
            base_url=str(item.get("base_url", "")),
            endpoint=str(item.get("endpoint", "")),
            http_status_code=item.get("http_status_code"),
            assertion_passed=item.get("assertion_passed"),
            response_excerpt=str(item.get("response_excerpt", "")),
            error_type=str(item.get("error_type", "")),
            error_message=str(item.get("error_message", "")),
            log_refs=list(item.get("log_refs", [])) if isinstance(item.get("log_refs"), list) else [],
            metadata=dict(item.get("metadata", {})) if isinstance(item.get("metadata"), dict) else {},
            created_at=item.get("created_at"),
        )

    def _sort_entries(self, entries: list[APIExecutionHistoryEntry]) -> list[APIExecutionHistoryEntry]:
        return sorted(entries, key=lambda item: ((item.created_at or ""), item.history_id))

    def _normalize_failure_key(self, prefix: str, raw_value: str) -> str:
        return f"{prefix}:{str(raw_value or '').strip()}"

    def _normalize_outcome(self, status: str) -> str:
        if status == "Passed":
            return "passed"
        if status in {"Failed", "Error"}:
            return "failed"
        return "other"

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_API_EXECUTION_HISTORY_SERVICE = APIExecutionHistoryService()


def create_api_execution_history_entry(
    summary: APIExecutionSummary,
    *,
    source_file: str = "",
    run_label: str = "",
    metadata: dict[str, Any] | None = None,
) -> APIExecutionHistoryEntry:
    return _DEFAULT_API_EXECUTION_HISTORY_SERVICE.create_api_execution_history_entry(
        summary,
        source_file=source_file,
        run_label=run_label,
        metadata=metadata,
    )


def build_api_execution_history(
    *,
    current_summary: APIExecutionSummary | dict[str, Any] | None = None,
    historical_summaries: list[APIExecutionSummary | dict[str, Any]] | None = None,
    current_source_file: str = "reports/api_execution_summary.json",
    metadata: dict[str, Any] | None = None,
) -> list[APIExecutionHistoryEntry]:
    return _DEFAULT_API_EXECUTION_HISTORY_SERVICE.build_api_execution_history(
        current_summary=current_summary,
        historical_summaries=historical_summaries,
        current_source_file=current_source_file,
        metadata=metadata,
    )


def summarize_api_execution_trends(
    entries: list[APIExecutionHistoryEntry],
    *,
    repeated_failure_keys: list[str] | None = None,
    flaky_candidate_keys: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> APIExecutionTrendSummary:
    return _DEFAULT_API_EXECUTION_HISTORY_SERVICE.summarize_api_execution_trends(
        entries,
        repeated_failure_keys=repeated_failure_keys,
        flaky_candidate_keys=flaky_candidate_keys,
        metadata=metadata,
    )


def detect_repeated_failures(
    evidence_items: list[APIExecutionEvidence | dict[str, Any]] | None = None,
    failure_signatures: list[FailureSignature | dict[str, Any]] | None = None,
) -> list[str]:
    return _DEFAULT_API_EXECUTION_HISTORY_SERVICE.detect_repeated_failures(
        evidence_items,
        failure_signatures=failure_signatures,
    )


def detect_flaky_candidates(
    evidence_items: list[APIExecutionEvidence | dict[str, Any]] | None = None,
) -> list[str]:
    return _DEFAULT_API_EXECUTION_HISTORY_SERVICE.detect_flaky_candidates(evidence_items)


def build_api_execution_history_report(
    *,
    history_entries: list[APIExecutionHistoryEntry],
    evidence_items: list[APIExecutionEvidence | dict[str, Any]] | None = None,
    failure_signatures: list[FailureSignature | dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _DEFAULT_API_EXECUTION_HISTORY_SERVICE.build_api_execution_history_report(
        history_entries=history_entries,
        evidence_items=evidence_items,
        failure_signatures=failure_signatures,
        metadata=metadata,
    )


def build_api_execution_history_report_from_workspace(
    workspace_path: str | Path,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _DEFAULT_API_EXECUTION_HISTORY_SERVICE.build_api_execution_history_report_from_workspace(
        workspace_path,
        metadata=metadata,
    )

from __future__ import annotations

import json

from orchestrator.manual_qa.api_execution_history_service import APIExecutionHistoryService
from orchestrator.manual_qa.models import APIExecutionEvidence, APIExecutionSummary, TestResult
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


def _build_summary(
    *,
    summary_id: str = "API-EXEC-SUM-001",
    total: int = 2,
    passed: int = 1,
    failed: int = 1,
    blocked: int = 0,
    dry_run: int = 0,
    error: int = 0,
    not_run: int = 0,
    pass_rate: float = 50.0,
    failure_rate: float = 50.0,
    status: str = "Failed",
    created_at: str = "2024-01-20T00:00:00Z",
) -> APIExecutionSummary:
    return APIExecutionSummary(
        summary_id=summary_id,
        total=total,
        passed=passed,
        failed=failed,
        blocked=blocked,
        dry_run=dry_run,
        error=error,
        not_run=not_run,
        pass_rate=pass_rate,
        failure_rate=failure_rate,
        evidence_ids=["API-EVD-001"],
        bug_suggestion_ids=["BUG-APIEXEC-001"] if failed or error else [],
        failure_signature_ids=["FSIG-001"] if failed or error else [],
        status=status,
        recommended_next_step="Review mixed execution outcomes",
        metadata={"sandbox_only": True},
        created_at=created_at,
    )


def _build_evidence(
    *,
    status: str = "Failed",
    test_case_id: str = "TC-900",
    method: str = "GET",
    endpoint: str = "/api/orders",
    error_type: str = "",
    http_status_code: int | None = 500,
) -> APIExecutionEvidence:
    return APIExecutionEvidence(
        evidence_id=f"API-EVD-{test_case_id}",
        execution_id=f"API-EXEC-{test_case_id}-{status}",
        draft_id="API-DRAFT-001",
        test_case_id=test_case_id,
        evidence_type="api_execution_result",
        title=f"{test_case_id} evidence",
        summary="Sandbox summary",
        status=status,
        method=method,
        base_url="http://localhost:8000",
        endpoint=endpoint,
        http_status_code=http_status_code,
        assertion_passed=status == "Passed",
        response_excerpt="ok" if status == "Passed" else "error",
        error_type=error_type,
        error_message=error_type.lower() if error_type else "",
        log_refs=["LOG-001"],
        metadata={"sandbox_only": True},
        created_at="2024-01-20T00:10:00Z",
    )


def test_create_history_entry_from_summary():
    service = APIExecutionHistoryService()

    entry = service.create_api_execution_history_entry(
        _build_summary(),
        source_file="reports/api_execution_summary.json",
        run_label="current",
    )

    assert entry.summary_id == "API-EXEC-SUM-001"
    assert entry.source_file == "reports/api_execution_summary.json"
    assert entry.run_label == "current"


def test_empty_workspace_has_no_history_and_no_history_trend(tmp_path):
    service = APIExecutionHistoryService()
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")

    report = service.build_api_execution_history_report_from_workspace(workspace)

    assert report["history_entries"] == []
    assert report["trend_summary"].trend_status == "No History"


def test_build_history_from_current_summary():
    service = APIExecutionHistoryService()

    entries = service.build_api_execution_history(current_summary=_build_summary(status="Passed", failed=0, pass_rate=100.0, failure_rate=0.0))

    assert len(entries) == 1
    assert entries[0].status == "Passed"


def test_build_history_from_historical_summary_files(tmp_path):
    service = APIExecutionHistoryService()
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    history_dir = workspace / "history" / "api_execution"
    history_dir.mkdir(parents=True, exist_ok=True)
    (workspace / "reports" / "api_execution_summary.json").write_text(
        json.dumps(_build_summary(summary_id="API-EXEC-SUM-002").to_dict(), indent=2),
        encoding="utf-8",
    )
    (history_dir / "api_execution_summary_20240120.json").write_text(
        json.dumps(_build_summary(summary_id="API-EXEC-SUM-001", created_at="2024-01-19T00:00:00Z").to_dict(), indent=2),
        encoding="utf-8",
    )

    report = service.build_api_execution_history_report_from_workspace(workspace)

    assert len(report["history_entries"]) == 2


def test_trend_all_dry_run_is_all_dry_run():
    service = APIExecutionHistoryService()
    entries = [
        service.create_api_execution_history_entry(_build_summary(status="All Dry Run", total=1, dry_run=1, passed=0, failed=0, pass_rate=0.0, failure_rate=0.0)),
        service.create_api_execution_history_entry(_build_summary(summary_id="API-EXEC-SUM-002", status="All Dry Run", total=1, dry_run=1, passed=0, failed=0, pass_rate=0.0, failure_rate=0.0, created_at="2024-01-21T00:00:00Z")),
    ]

    summary = service.summarize_api_execution_trends(entries)

    assert summary.trend_status == "All Dry Run"


def test_trend_improving():
    service = APIExecutionHistoryService()
    entries = [
        service.create_api_execution_history_entry(_build_summary(summary_id="API-EXEC-SUM-001", passed=0, failed=2, total=2, pass_rate=0.0, failure_rate=100.0, status="Failed", created_at="2024-01-19T00:00:00Z")),
        service.create_api_execution_history_entry(_build_summary(summary_id="API-EXEC-SUM-002", passed=2, failed=0, total=2, pass_rate=100.0, failure_rate=0.0, status="Passed", created_at="2024-01-20T00:00:00Z")),
    ]

    summary = service.summarize_api_execution_trends(entries)

    assert summary.trend_status == "Improving"


def test_trend_regressing():
    service = APIExecutionHistoryService()
    entries = [
        service.create_api_execution_history_entry(_build_summary(summary_id="API-EXEC-SUM-001", passed=2, failed=0, total=2, pass_rate=100.0, failure_rate=0.0, status="Passed", created_at="2024-01-19T00:00:00Z")),
        service.create_api_execution_history_entry(_build_summary(summary_id="API-EXEC-SUM-002", passed=0, failed=2, total=2, pass_rate=0.0, failure_rate=100.0, status="Failed", created_at="2024-01-20T00:00:00Z")),
    ]

    summary = service.summarize_api_execution_trends(entries)

    assert summary.trend_status == "Regressing"


def test_trend_stable():
    service = APIExecutionHistoryService()
    entries = [
        service.create_api_execution_history_entry(_build_summary(summary_id="API-EXEC-SUM-001", pass_rate=50.0, failure_rate=50.0, created_at="2024-01-19T00:00:00Z")),
        service.create_api_execution_history_entry(_build_summary(summary_id="API-EXEC-SUM-002", pass_rate=52.0, failure_rate=48.0, created_at="2024-01-20T00:00:00Z")),
    ]

    summary = service.summarize_api_execution_trends(entries)

    assert summary.trend_status == "Stable"


def test_detect_repeated_failures_by_endpoint_method_test_case_and_error():
    service = APIExecutionHistoryService()
    evidence_items = [
        _build_evidence(status="Failed", test_case_id="TC-900", method="GET", endpoint="/api/orders", error_type=""),
        _build_evidence(status="Error", test_case_id="TC-900", method="GET", endpoint="/api/orders", error_type="TimeoutError", http_status_code=None),
        _build_evidence(status="Failed", test_case_id="TC-901", method="POST", endpoint="/api/orders", error_type="TimeoutError"),
    ]

    repeated = service.detect_repeated_failures(evidence_items)

    assert "endpoint:GET /api/orders" in repeated
    assert "test_case:TC-900" in repeated
    assert "error_type:TimeoutError" in repeated


def test_detect_flaky_candidates_with_mixed_pass_fail_outcomes():
    service = APIExecutionHistoryService()
    evidence_items = [
        _build_evidence(status="Passed", test_case_id="TC-900", endpoint="/api/orders", http_status_code=200),
        _build_evidence(status="Failed", test_case_id="TC-900", endpoint="/api/orders", http_status_code=500),
    ]

    flaky = service.detect_flaky_candidates(evidence_items)

    assert "TC-900" in flaky
    assert "GET /api/orders" in flaky


def test_report_writes_expected_files(tmp_path):
    service = APIExecutionHistoryService()
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    (workspace / "reports" / "api_execution_summary.json").write_text(
        json.dumps(_build_summary().to_dict(), indent=2),
        encoding="utf-8",
    )
    (workspace / "evidence" / "api_execution_evidence.json").write_text(
        json.dumps([_build_evidence().to_dict(), _build_evidence(status="Passed", http_status_code=200).to_dict()], indent=2),
        encoding="utf-8",
    )
    (workspace / "failure_memory" / "api_execution_failure_signatures.json").write_text(
        json.dumps(
            [
                {
                    "signature_id": "FSIG-001",
                    "fingerprint": "FP-ABC",
                    "module": "Order API",
                    "test_case_id": "TC-900",
                    "title": "Failure",
                    "symptom": "GET /api/orders failed",
                    "expected_result": "",
                    "actual_result": "",
                    "environment": "",
                    "build": "",
                    "severity": "",
                    "priority": "",
                    "source_bug_id": "",
                    "tags": [],
                    "created_at": "2024-01-20T00:00:00Z",
                    "metadata": {"method": "GET", "endpoint": "/api/orders", "error_type": "TimeoutError"},
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    report = service.build_api_execution_history_report_from_workspace(workspace)

    assert report["trend_summary"].total_runs == 1
    assert (workspace / "history" / "api_execution" / "api_execution_history.json").exists()
    assert (workspace / "history" / "api_execution" / "api_execution_history.md").exists()
    assert (workspace / "reports" / "api_execution_trend_summary.json").exists()
    assert (workspace / "reports" / "api_execution_trend_summary.md").exists()


def test_manual_test_result_is_not_modified():
    service = APIExecutionHistoryService()
    manual_result = TestResult(
        result_id="RES-001",
        run_id="RUN-001",
        test_case_id="TC-900",
        status="Not Run",
        actual_result="",
        notes="",
        metadata={},
    )

    service.build_api_execution_history_report(history_entries=[])

    assert manual_result.status == "Not Run"
    assert manual_result.metadata == {}

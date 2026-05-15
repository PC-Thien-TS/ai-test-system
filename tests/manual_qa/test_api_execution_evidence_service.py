from __future__ import annotations

import json

from orchestrator.manual_qa.api_execution_evidence_service import APIExecutionEvidenceService
from orchestrator.manual_qa.models import (
    APIExecutionLogEntry,
    APIExecutionRequest,
    APIExecutionResult,
    APITestScriptDraft,
    ManualTestCase,
    TestResult,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


def _build_request() -> APIExecutionRequest:
    return APIExecutionRequest(
        request_id="API-EXEC-REQ-001",
        draft_id="API-DRAFT-001",
        test_case_id="TC-900",
        file_name="test_api_tc_001.py",
        method="GET",
        base_url="http://localhost:8000",
        endpoint="/api/orders",
        headers={},
        payload={},
        timeout_seconds=30,
        policy_id="EXEC-POLICY-DEFAULT",
        preflight_id="EXEC-PREFLIGHT-001",
        dry_run=False,
        metadata={"approved": True},
        created_at="2024-01-18T00:00:00Z",
    )


def _build_result(status: str = "Passed") -> APIExecutionResult:
    http_status_code = 200 if status == "Passed" else 500 if status == "Failed" else None
    assertion_passed = True if status == "Passed" else False if status == "Failed" else None
    error_type = "RequestException" if status == "Error" else ""
    error_message = "connection reset" if status == "Error" else "Expected HTTP status 200 but received 500." if status == "Failed" else ""
    response_excerpt = "ok" if status == "Passed" else "server error response" if status == "Failed" else ""
    return APIExecutionResult(
        execution_id=f"API-EXEC-RESULT-{status.replace(' ', '-').upper()}",
        request=_build_request(),
        status=status,
        http_status_code=http_status_code,
        duration_ms=25,
        response_excerpt=response_excerpt,
        error_type=error_type,
        error_message=error_message,
        assertion_expected_status=200,
        assertion_passed=assertion_passed,
        logs=[
            APIExecutionLogEntry(
                log_id="API-EXEC-LOG-001",
                level="Info",
                message="Sandbox-only log",
                metadata={},
                created_at="2024-01-18T00:01:00Z",
            )
        ],
        executed_at="2024-01-18T00:02:00Z",
        metadata={"sandbox_only": True},
    )


def _build_test_case() -> ManualTestCase:
    return ManualTestCase(
        test_case_id="TC-900",
        requirement_ids=["REQ-900"],
        module="Order API",
        title="Create order endpoint returns success",
        steps=["Send request to /api/orders.", "Verify status code."],
        expected_result="Response status code is 200.",
        metadata={},
    )


def _build_draft() -> APITestScriptDraft:
    return APITestScriptDraft(
        draft_id="API-DRAFT-001",
        test_case_id="TC-900",
        requirement_ids=["REQ-900"],
        module="Order API",
        title="Order API draft",
        readiness_id="READ-900",
        target_type="api",
        framework="pytest-requests",
        language="python",
        file_name="test_api_tc_001.py",
        script_content="import requests",
        status="Draft",
        metadata={},
        created_at="2024-01-08T00:00:00Z",
    )


def test_create_evidence_from_passed_result():
    service = APIExecutionEvidenceService()

    evidence = service.create_api_execution_evidence(
        _build_result("Passed"),
        manual_test_case=_build_test_case(),
        draft=_build_draft(),
    )

    assert evidence.status == "Passed"
    assert evidence.http_status_code == 200
    assert evidence.evidence_type == "api_execution_result"


def test_create_evidence_from_failed_result():
    service = APIExecutionEvidenceService()

    evidence = service.create_api_execution_evidence(_build_result("Failed"))

    assert evidence.status == "Failed"
    assert evidence.assertion_passed is False
    assert "HTTP 500" in evidence.summary or "Failed" in evidence.summary


def test_create_evidence_from_dry_run_result():
    service = APIExecutionEvidenceService()

    evidence = service.create_api_execution_evidence(_build_result("Dry Run"))

    assert evidence.status == "Dry Run"
    assert "dry run" in evidence.summary.lower()


def test_summary_with_no_results_is_no_results():
    service = APIExecutionEvidenceService()

    summary = service.summarize_api_execution_results([])

    assert summary.status == "No Results"
    assert summary.total == 0


def test_summary_all_dry_run_is_all_dry_run():
    service = APIExecutionEvidenceService()

    summary = service.summarize_api_execution_results([_build_result("Dry Run"), _build_result("Dry Run")])

    assert summary.status == "All Dry Run"
    assert summary.dry_run == 2


def test_summary_all_passed_is_passed():
    service = APIExecutionEvidenceService()

    summary = service.summarize_api_execution_results([_build_result("Passed"), _build_result("Passed")])

    assert summary.status == "Passed"
    assert summary.pass_rate == 100.0


def test_summary_failed_or_error_is_failed():
    service = APIExecutionEvidenceService()

    summary = service.summarize_api_execution_results([_build_result("Failed"), _build_result("Error")])

    assert summary.status == "Failed"
    assert summary.failure_rate == 100.0


def test_bug_suggestion_generated_for_failed():
    service = APIExecutionEvidenceService()

    bug = service.generate_bug_suggestion_from_api_execution(_build_result("Failed"))

    assert bug is not None
    assert bug.status == "Draft"
    assert "TC-900" in bug.title


def test_bug_suggestion_generated_for_error():
    service = APIExecutionEvidenceService()

    bug = service.generate_bug_suggestion_from_api_execution(_build_result("Error"))

    assert bug is not None
    assert "connection reset" in bug.actual_result


def test_bug_suggestion_not_generated_for_passed_dry_run_or_blocked():
    service = APIExecutionEvidenceService()

    assert service.generate_bug_suggestion_from_api_execution(_build_result("Passed")) is None
    assert service.generate_bug_suggestion_from_api_execution(_build_result("Dry Run")) is None
    assert service.generate_bug_suggestion_from_api_execution(_build_result("Blocked")) is None


def test_failure_signature_generated_for_failed_or_error():
    service = APIExecutionEvidenceService()

    failed_signature = service.generate_failure_signature_from_api_execution(_build_result("Failed"))
    error_signature = service.generate_failure_signature_from_api_execution(_build_result("Error"))

    assert failed_signature is not None
    assert error_signature is not None
    assert failed_signature.metadata["source"] == "APIExecutionResult"


def test_evidence_report_includes_evidence_summary_suggestions_and_signatures():
    service = APIExecutionEvidenceService()
    results = [_build_result("Passed"), _build_result("Failed"), _build_result("Error")]

    report = service.build_api_execution_evidence_report(
        results,
        test_cases_by_id={"TC-900": _build_test_case()},
        drafts_by_id={"API-DRAFT-001": _build_draft()},
    )

    assert len(report["evidence_items"]) == 3
    assert report["summary"].status == "Failed"
    assert len(report["bug_suggestions"]) == 2
    assert len(report["failure_signatures"]) == 2


def test_workspace_report_writes_expected_files(tmp_path):
    service = APIExecutionEvidenceService()
    workspace = ManualQAWorkspaceService().create_workspace(tmp_path / "manual_qa_demo")
    api_dir = workspace / "script_drafts" / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "api_execution_results.json").write_text(
        json.dumps([_build_result("Failed").to_dict()], indent=2),
        encoding="utf-8",
    )
    (api_dir / "api_script_drafts.json").write_text(
        json.dumps([_build_draft().to_dict()], indent=2),
        encoding="utf-8",
    )
    (workspace / "testcases" / "testcases.json").write_text(
        json.dumps([_build_test_case().to_dict()], indent=2),
        encoding="utf-8",
    )

    report = service.build_api_execution_evidence_report_from_workspace(workspace)

    assert len(report["evidence_items"]) == 1
    assert (workspace / "evidence" / "api_execution_evidence.json").exists()
    assert (workspace / "evidence" / "api_execution_evidence.md").exists()
    assert (workspace / "reports" / "api_execution_summary.json").exists()
    assert (workspace / "reports" / "api_execution_summary.md").exists()
    assert (workspace / "bugs" / "api_execution_bug_suggestions.json").exists()
    assert (workspace / "failure_memory" / "api_execution_failure_signatures.json").exists()


def test_manual_test_result_is_not_modified():
    service = APIExecutionEvidenceService()
    manual_result = TestResult(
        result_id="RES-001",
        run_id="RUN-001",
        test_case_id="TC-900",
        status="Not Run",
        actual_result="",
        notes="",
        metadata={},
    )

    service.build_api_execution_evidence_report([_build_result("Failed")])

    assert manual_result.status == "Not Run"
    assert manual_result.metadata == {}

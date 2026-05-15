"""Metadata-only API execution evidence integration for Manual QA."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from orchestrator.manual_qa.exporters import ManualQAExporter
from orchestrator.manual_qa.failure_memory_service import FailureMemoryService
from orchestrator.manual_qa.models import (
    APIExecutionEvidence,
    APIExecutionLogEntry,
    APIExecutionRequest,
    APIExecutionResult,
    APIExecutionSummary,
    APITestScriptDraft,
    BugDraft,
    FailureSignature,
    ManualTestCase,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


class APIExecutionEvidenceService:
    """Convert API sandbox execution results into evidence-oriented artifacts."""

    _BASE_TIME = datetime(2024, 1, 20, 0, 0, 0)

    def __init__(self) -> None:
        self._workspace_service = ManualQAWorkspaceService()
        self._exporter = ManualQAExporter()
        self._failure_memory_service = FailureMemoryService()
        self._next_evidence_number = 1
        self._next_summary_number = 1
        self._next_bug_number = 1
        self._next_timestamp_offset = 0

    def create_api_execution_evidence(
        self,
        execution_result: APIExecutionResult,
        *,
        manual_test_case: ManualTestCase | None = None,
        draft: APITestScriptDraft | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> APIExecutionEvidence:
        request = execution_result.request
        title = self._build_evidence_title(execution_result, manual_test_case=manual_test_case, draft=draft)
        summary = self._build_evidence_summary(execution_result)
        evidence = APIExecutionEvidence(
            evidence_id=f"API-EVD-{self._next_evidence_number:03d}",
            execution_id=execution_result.execution_id,
            draft_id=request.draft_id,
            test_case_id=request.test_case_id,
            evidence_type="api_execution_result",
            title=title,
            summary=summary,
            status=execution_result.status,
            method=request.method,
            base_url=request.base_url,
            endpoint=request.endpoint,
            http_status_code=execution_result.http_status_code,
            assertion_passed=execution_result.assertion_passed,
            response_excerpt=execution_result.response_excerpt,
            error_type=execution_result.error_type,
            error_message=execution_result.error_message,
            log_refs=[item.log_id for item in execution_result.logs],
            metadata={
                "source": "APIExecutionResult",
                "sandbox_only": True,
                "file_name": request.file_name,
                "manual_test_case_title": manual_test_case.title if manual_test_case is not None else "",
                "draft_title": draft.title if draft is not None else "",
                **dict(metadata or {}),
            },
            created_at=self._next_timestamp(),
        )
        self._next_evidence_number += 1
        return evidence

    def create_api_execution_evidence_batch(
        self,
        execution_results: list[APIExecutionResult],
        *,
        test_cases_by_id: dict[str, ManualTestCase] | None = None,
        drafts_by_id: dict[str, APITestScriptDraft] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[APIExecutionEvidence]:
        evidence_items: list[APIExecutionEvidence] = []
        for result in execution_results:
            evidence_items.append(
                self.create_api_execution_evidence(
                    result,
                    manual_test_case=(test_cases_by_id or {}).get(result.request.test_case_id),
                    draft=(drafts_by_id or {}).get(result.request.draft_id),
                    metadata=metadata,
                )
            )
        return evidence_items

    def summarize_api_execution_results(
        self,
        execution_results: list[APIExecutionResult],
        *,
        evidence_ids: list[str] | None = None,
        bug_suggestion_ids: list[str] | None = None,
        failure_signature_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> APIExecutionSummary:
        total = len(execution_results)
        counts = {
            "Passed": 0,
            "Failed": 0,
            "Blocked": 0,
            "Dry Run": 0,
            "Error": 0,
            "Not Run": 0,
        }
        for result in execution_results:
            counts[result.status] = counts.get(result.status, 0) + 1

        pass_rate = round((counts["Passed"] / total) * 100, 2) if total else 0.0
        failure_rate = round(((counts["Failed"] + counts["Error"]) / total) * 100, 2) if total else 0.0
        status = self._summary_status(execution_results, counts=counts)
        summary = APIExecutionSummary(
            summary_id=f"API-EXEC-SUM-{self._next_summary_number:03d}",
            total=total,
            passed=counts["Passed"],
            failed=counts["Failed"],
            blocked=counts["Blocked"],
            dry_run=counts["Dry Run"],
            error=counts["Error"],
            not_run=counts["Not Run"],
            pass_rate=pass_rate,
            failure_rate=failure_rate,
            evidence_ids=list(evidence_ids or []),
            bug_suggestion_ids=list(bug_suggestion_ids or []),
            failure_signature_ids=list(failure_signature_ids or []),
            status=status,
            recommended_next_step=self._recommended_next_step(status),
            metadata=dict(metadata or {}),
            created_at=self._next_timestamp(),
        )
        self._next_summary_number += 1
        return summary

    def generate_bug_suggestion_from_api_execution(
        self,
        execution_result: APIExecutionResult,
        *,
        evidence: APIExecutionEvidence | None = None,
        manual_test_case: ManualTestCase | None = None,
        draft: APITestScriptDraft | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BugDraft | None:
        if execution_result.status not in {"Failed", "Error"}:
            return None

        request = execution_result.request
        expected_result = self._expected_result(execution_result, manual_test_case=manual_test_case)
        actual_result = self._actual_result(execution_result)
        bug = BugDraft(
            bug_id=f"BUG-APIEXEC-{self._next_bug_number:03d}",
            run_id="API-SANDBOX",
            test_case_id=request.test_case_id,
            title=f"{request.test_case_id} {request.method} {request.endpoint} sandbox bug suggestion",
            severity="Major",
            priority="High",
            environment=request.base_url,
            build="api-execution-sandbox",
            steps_to_reproduce=list(manual_test_case.steps) if manual_test_case is not None else [
                f"Execute sandbox request {request.method} {request.endpoint}.",
                "Review API sandbox execution evidence.",
            ],
            expected_result=expected_result,
            actual_result=actual_result,
            evidence_ids=[evidence.evidence_id] if evidence is not None else [],
            status="Draft",
            created_at=self._next_timestamp(),
            metadata={
                "source": "APIExecutionResult",
                "sandbox_only": True,
                "execution_id": execution_result.execution_id,
                "draft_id": request.draft_id,
                "method": request.method,
                "endpoint": request.endpoint,
                "http_status_code": execution_result.http_status_code,
                "error_type": execution_result.error_type,
                "draft_title": draft.title if draft is not None else "",
                **dict(metadata or {}),
            },
        )
        self._next_bug_number += 1
        return bug

    def generate_failure_signature_from_api_execution(
        self,
        execution_result: APIExecutionResult,
        *,
        bug_suggestion: BugDraft | None = None,
        manual_test_case: ManualTestCase | None = None,
        draft: APITestScriptDraft | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FailureSignature | None:
        if execution_result.status not in {"Failed", "Error"}:
            return None

        request = execution_result.request
        title = (
            bug_suggestion.title
            if bug_suggestion is not None
            else f"{request.test_case_id} {request.method} {request.endpoint} sandbox failure"
        )
        actual_result = self._actual_result(execution_result)
        symptom = f"{request.method} {request.endpoint} -> {execution_result.status}"
        return self._failure_memory_service.create_failure_signature(
            module=(draft.module if draft is not None else manual_test_case.module if manual_test_case is not None else ""),
            test_case_id=request.test_case_id,
            title=title,
            symptom=f"{symptom}; {actual_result}".strip("; "),
            expected_result=self._expected_result(execution_result, manual_test_case=manual_test_case),
            actual_result=actual_result,
            environment=request.base_url,
            build="api-execution-sandbox",
            severity=bug_suggestion.severity if bug_suggestion is not None else "Major",
            priority=bug_suggestion.priority if bug_suggestion is not None else "High",
            source_bug_id=bug_suggestion.bug_id if bug_suggestion is not None else "",
            tags=["api-execution", "sandbox", execution_result.status.lower().replace(" ", "-")],
            metadata={
                "source": "APIExecutionResult",
                "sandbox_only": True,
                "execution_id": execution_result.execution_id,
                "draft_id": request.draft_id,
                "method": request.method,
                "endpoint": request.endpoint,
                "http_status_code": execution_result.http_status_code,
                "error_type": execution_result.error_type,
                **dict(metadata or {}),
            },
        )

    def build_api_execution_evidence_report(
        self,
        execution_results: list[APIExecutionResult],
        *,
        test_cases_by_id: dict[str, ManualTestCase] | None = None,
        drafts_by_id: dict[str, APITestScriptDraft] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        evidence_items = self.create_api_execution_evidence_batch(
            execution_results,
            test_cases_by_id=test_cases_by_id,
            drafts_by_id=drafts_by_id,
            metadata=metadata,
        )

        bug_suggestions: list[BugDraft] = []
        failure_signatures: list[FailureSignature] = []
        evidence_by_execution_id = {item.execution_id: item for item in evidence_items}

        for result in execution_results:
            manual_test_case = (test_cases_by_id or {}).get(result.request.test_case_id)
            draft = (drafts_by_id or {}).get(result.request.draft_id)
            bug = self.generate_bug_suggestion_from_api_execution(
                result,
                evidence=evidence_by_execution_id.get(result.execution_id),
                manual_test_case=manual_test_case,
                draft=draft,
                metadata=metadata,
            )
            if bug is None:
                continue
            bug_suggestions.append(bug)
            failure_signature = self.generate_failure_signature_from_api_execution(
                result,
                bug_suggestion=bug,
                manual_test_case=manual_test_case,
                draft=draft,
                metadata=metadata,
            )
            if failure_signature is not None:
                failure_signatures.append(failure_signature)

        summary = self.summarize_api_execution_results(
            execution_results,
            evidence_ids=[item.evidence_id for item in evidence_items],
            bug_suggestion_ids=[item.bug_id for item in bug_suggestions],
            failure_signature_ids=[item.signature_id for item in failure_signatures],
            metadata=metadata,
        )
        return {
            "evidence_items": evidence_items,
            "summary": summary,
            "bug_suggestions": bug_suggestions,
            "failure_signatures": failure_signatures,
            "metadata": {"sandbox_only": True, **dict(metadata or {})},
        }

    def build_api_execution_evidence_report_from_workspace(
        self,
        workspace_path: str | Path,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace = Path(workspace_path)
        execution_results = self._load_execution_results(
            workspace / "script_drafts" / "api" / "api_execution_results.json"
        )
        test_cases_by_id = self._load_test_cases_by_id(workspace / "testcases" / "testcases.json")
        drafts_by_id = self._load_api_drafts_by_id(workspace / "script_drafts" / "api" / "api_script_drafts.json")
        report = self.build_api_execution_evidence_report(
            execution_results,
            test_cases_by_id=test_cases_by_id,
            drafts_by_id=drafts_by_id,
            metadata=metadata,
        )

        evidence_json_path = workspace / "evidence" / "api_execution_evidence.json"
        evidence_md_path = workspace / "evidence" / "api_execution_evidence.md"
        summary_json_path = workspace / "reports" / "api_execution_summary.json"
        summary_md_path = workspace / "reports" / "api_execution_summary.md"
        self._exporter.export_json_file(report["evidence_items"], evidence_json_path)
        self._workspace_service.write_markdown(
            evidence_md_path,
            self._exporter.export_markdown_string(report, title="API Execution Evidence Report"),
        )
        self._exporter.export_json_file(report["summary"], summary_json_path)
        self._exporter.export_markdown_file(report["summary"], summary_md_path)

        if report["bug_suggestions"]:
            self._exporter.export_json_file(report["bug_suggestions"], workspace / "bugs" / "api_execution_bug_suggestions.json")
            self._exporter.export_markdown_file(
                report["bug_suggestions"],
                workspace / "bugs" / "api_execution_bug_suggestions.md",
            )
        if report["failure_signatures"]:
            self._exporter.export_json_file(
                report["failure_signatures"],
                workspace / "failure_memory" / "api_execution_failure_signatures.json",
            )
            self._exporter.export_markdown_file(
                report["failure_signatures"],
                workspace / "failure_memory" / "api_execution_failure_signatures.md",
            )

        self._workspace_service.update_workspace_manifest(workspace)
        return report

    def _summary_status(
        self,
        execution_results: list[APIExecutionResult],
        *,
        counts: dict[str, int],
    ) -> str:
        total = len(execution_results)
        if total == 0:
            return "No Results"
        if counts["Dry Run"] == total:
            return "All Dry Run"
        if counts["Failed"] > 0 or counts["Error"] > 0:
            return "Failed"
        if counts["Blocked"] > 0:
            return "Blocked"
        if counts["Passed"] == total:
            return "Passed"
        return "Needs Review"

    def _recommended_next_step(self, status: str) -> str:
        steps = {
            "Passed": "Review sandbox evidence before promoting scripts",
            "Failed": "Review failed API execution evidence and create bug/failure records if confirmed",
            "Blocked": "Resolve safety or preflight blockers before execution",
            "All Dry Run": "Approve safe localhost/staging execution only after review",
            "No Results": "Run API sandbox dry-run or execution first",
            "Needs Review": "Review mixed execution outcomes",
        }
        return steps.get(status, "Review mixed execution outcomes")

    def _expected_result(
        self,
        execution_result: APIExecutionResult,
        *,
        manual_test_case: ManualTestCase | None = None,
    ) -> str:
        if execution_result.assertion_expected_status is not None:
            return f"HTTP status {execution_result.assertion_expected_status} should be returned."
        if manual_test_case is not None and manual_test_case.expected_result:
            return manual_test_case.expected_result
        return "Sandbox API request should complete successfully."

    def _actual_result(self, execution_result: APIExecutionResult) -> str:
        if execution_result.status == "Error" and execution_result.error_message:
            return f"Sandbox execution error: {execution_result.error_message}"
        if execution_result.http_status_code is not None and execution_result.assertion_expected_status is not None:
            return (
                f"Expected HTTP status {execution_result.assertion_expected_status} "
                f"but received {execution_result.http_status_code}."
            )
        if execution_result.http_status_code is not None:
            return f"Sandbox request returned HTTP status {execution_result.http_status_code}."
        if execution_result.error_message:
            return execution_result.error_message
        return f"Sandbox execution finished with status {execution_result.status}."

    def _build_evidence_title(
        self,
        execution_result: APIExecutionResult,
        *,
        manual_test_case: ManualTestCase | None,
        draft: APITestScriptDraft | None,
    ) -> str:
        request = execution_result.request
        if manual_test_case is not None and manual_test_case.title:
            return f"{manual_test_case.title} - API sandbox {execution_result.status}"
        if draft is not None and draft.title:
            return f"{draft.title} - API sandbox {execution_result.status}"
        return f"{request.test_case_id} {request.method} {request.endpoint} - API sandbox {execution_result.status}"

    def _build_evidence_summary(self, execution_result: APIExecutionResult) -> str:
        request = execution_result.request
        if execution_result.status == "Passed":
            return (
                f"Sandbox request {request.method} {request.endpoint} passed"
                f" with HTTP {execution_result.http_status_code}."
            )
        if execution_result.status == "Dry Run":
            return f"Sandbox request {request.method} {request.endpoint} was not executed because it remained a dry run."
        if execution_result.status == "Blocked":
            return (
                f"Sandbox request {request.method} {request.endpoint} was blocked"
                f" before execution. {execution_result.error_message}".strip()
            )
        if execution_result.status == "Error":
            return (
                f"Sandbox request {request.method} {request.endpoint} errored during execution."
                f" {execution_result.error_message}".strip()
            )
        return (
            f"Sandbox request {request.method} {request.endpoint} completed"
            f" with status {execution_result.status} and HTTP {execution_result.http_status_code}."
        )

    def _load_execution_results(self, path: Path) -> list[APIExecutionResult]:
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return []
        return [self._execution_result_from_dict(item) for item in payload if isinstance(item, dict)]

    def _execution_result_from_dict(self, payload: dict[str, Any]) -> APIExecutionResult:
        request_payload = payload.get("request", {}) if isinstance(payload.get("request"), dict) else {}
        request = APIExecutionRequest(
            request_id=str(request_payload.get("request_id", "")),
            draft_id=str(request_payload.get("draft_id", "")),
            test_case_id=str(request_payload.get("test_case_id", "")),
            file_name=str(request_payload.get("file_name", "")),
            method=str(request_payload.get("method", "GET")),
            base_url=str(request_payload.get("base_url", "")),
            endpoint=str(request_payload.get("endpoint", "")),
            headers=dict(request_payload.get("headers", {})) if isinstance(request_payload.get("headers"), dict) else {},
            payload=dict(request_payload.get("payload", {})) if isinstance(request_payload.get("payload"), dict) else {},
            timeout_seconds=int(request_payload.get("timeout_seconds", 30) or 30),
            policy_id=str(request_payload.get("policy_id", "")),
            preflight_id=str(request_payload.get("preflight_id", "")),
            dry_run=bool(request_payload.get("dry_run", True)),
            metadata=dict(request_payload.get("metadata", {})) if isinstance(request_payload.get("metadata"), dict) else {},
            created_at=request_payload.get("created_at"),
        )
        logs = [
            APIExecutionLogEntry(
                log_id=str(item.get("log_id", "")),
                level=str(item.get("level", "")),
                message=str(item.get("message", "")),
                metadata=dict(item.get("metadata", {})) if isinstance(item.get("metadata"), dict) else {},
                created_at=item.get("created_at"),
            )
            for item in payload.get("logs", [])
            if isinstance(item, dict)
        ]
        return APIExecutionResult(
            execution_id=str(payload.get("execution_id", "")),
            request=request,
            status=str(payload.get("status", "Not Run")),
            http_status_code=payload.get("http_status_code"),
            duration_ms=int(payload.get("duration_ms", 0) or 0),
            response_excerpt=str(payload.get("response_excerpt", "")),
            error_type=str(payload.get("error_type", "")),
            error_message=str(payload.get("error_message", "")),
            assertion_expected_status=payload.get("assertion_expected_status"),
            assertion_passed=payload.get("assertion_passed"),
            logs=logs,
            executed_at=payload.get("executed_at"),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata"), dict) else {},
        )

    def _load_test_cases_by_id(self, path: Path) -> dict[str, ManualTestCase]:
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return {}
        items: dict[str, ManualTestCase] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            test_case = ManualTestCase(
                test_case_id=str(item.get("test_case_id", "")),
                requirement_ids=list(item.get("requirement_ids", [])) if isinstance(item.get("requirement_ids"), list) else [],
                module=str(item.get("module", "")),
                title=str(item.get("title", "")),
                preconditions=list(item.get("preconditions", [])) if isinstance(item.get("preconditions"), list) else [],
                steps=list(item.get("steps", [])) if isinstance(item.get("steps"), list) else [],
                expected_result=str(item.get("expected_result", "")),
                priority=str(item.get("priority", "Medium")),
                test_type=str(item.get("test_type", "Positive")),
                status=str(item.get("status", "Not Run")),
                metadata=dict(item.get("metadata", {})) if isinstance(item.get("metadata"), dict) else {},
            )
            items[test_case.test_case_id] = test_case
        return items

    def _load_api_drafts_by_id(self, path: Path) -> dict[str, APITestScriptDraft]:
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return {}
        items: dict[str, APITestScriptDraft] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            draft = APITestScriptDraft(
                draft_id=str(item.get("draft_id", "")),
                test_case_id=str(item.get("test_case_id", "")),
                requirement_ids=list(item.get("requirement_ids", [])) if isinstance(item.get("requirement_ids"), list) else [],
                module=str(item.get("module", "")),
                title=str(item.get("title", "")),
                readiness_id=str(item.get("readiness_id", "")),
                target_type=str(item.get("target_type", "api")),
                framework=str(item.get("framework", "pytest-requests")),
                language=str(item.get("language", "python")),
                file_name=str(item.get("file_name", "")),
                script_content=str(item.get("script_content", "")),
                status=str(item.get("status", "Draft")),
                warnings=list(item.get("warnings", [])) if isinstance(item.get("warnings"), list) else [],
                assumptions=list(item.get("assumptions", [])) if isinstance(item.get("assumptions"), list) else [],
                metadata=dict(item.get("metadata", {})) if isinstance(item.get("metadata"), dict) else {},
                created_at=item.get("created_at"),
            )
            items[draft.draft_id] = draft
        return items

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_API_EXECUTION_EVIDENCE_SERVICE = APIExecutionEvidenceService()


def create_api_execution_evidence(
    execution_result: APIExecutionResult,
    *,
    manual_test_case: ManualTestCase | None = None,
    draft: APITestScriptDraft | None = None,
    metadata: dict[str, Any] | None = None,
) -> APIExecutionEvidence:
    return _DEFAULT_API_EXECUTION_EVIDENCE_SERVICE.create_api_execution_evidence(
        execution_result,
        manual_test_case=manual_test_case,
        draft=draft,
        metadata=metadata,
    )


def create_api_execution_evidence_batch(
    execution_results: list[APIExecutionResult],
    *,
    test_cases_by_id: dict[str, ManualTestCase] | None = None,
    drafts_by_id: dict[str, APITestScriptDraft] | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[APIExecutionEvidence]:
    return _DEFAULT_API_EXECUTION_EVIDENCE_SERVICE.create_api_execution_evidence_batch(
        execution_results,
        test_cases_by_id=test_cases_by_id,
        drafts_by_id=drafts_by_id,
        metadata=metadata,
    )


def summarize_api_execution_results(
    execution_results: list[APIExecutionResult],
    *,
    evidence_ids: list[str] | None = None,
    bug_suggestion_ids: list[str] | None = None,
    failure_signature_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> APIExecutionSummary:
    return _DEFAULT_API_EXECUTION_EVIDENCE_SERVICE.summarize_api_execution_results(
        execution_results,
        evidence_ids=evidence_ids,
        bug_suggestion_ids=bug_suggestion_ids,
        failure_signature_ids=failure_signature_ids,
        metadata=metadata,
    )


def generate_bug_suggestion_from_api_execution(
    execution_result: APIExecutionResult,
    *,
    evidence: APIExecutionEvidence | None = None,
    manual_test_case: ManualTestCase | None = None,
    draft: APITestScriptDraft | None = None,
    metadata: dict[str, Any] | None = None,
) -> BugDraft | None:
    return _DEFAULT_API_EXECUTION_EVIDENCE_SERVICE.generate_bug_suggestion_from_api_execution(
        execution_result,
        evidence=evidence,
        manual_test_case=manual_test_case,
        draft=draft,
        metadata=metadata,
    )


def generate_failure_signature_from_api_execution(
    execution_result: APIExecutionResult,
    *,
    bug_suggestion: BugDraft | None = None,
    manual_test_case: ManualTestCase | None = None,
    draft: APITestScriptDraft | None = None,
    metadata: dict[str, Any] | None = None,
) -> FailureSignature | None:
    return _DEFAULT_API_EXECUTION_EVIDENCE_SERVICE.generate_failure_signature_from_api_execution(
        execution_result,
        bug_suggestion=bug_suggestion,
        manual_test_case=manual_test_case,
        draft=draft,
        metadata=metadata,
    )


def build_api_execution_evidence_report(
    execution_results: list[APIExecutionResult],
    *,
    test_cases_by_id: dict[str, ManualTestCase] | None = None,
    drafts_by_id: dict[str, APITestScriptDraft] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _DEFAULT_API_EXECUTION_EVIDENCE_SERVICE.build_api_execution_evidence_report(
        execution_results,
        test_cases_by_id=test_cases_by_id,
        drafts_by_id=drafts_by_id,
        metadata=metadata,
    )


def build_api_execution_evidence_report_from_workspace(
    workspace_path: str | Path,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _DEFAULT_API_EXECUTION_EVIDENCE_SERVICE.build_api_execution_evidence_report_from_workspace(
        workspace_path,
        metadata=metadata,
    )

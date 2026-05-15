"""JSON and Markdown exporters for Manual QA models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from orchestrator.manual_qa.models import (
    APIExecutionEvidence,
    APIExecutionLogEntry,
    APIExecutionRequest,
    APIExecutionResult,
    APIExecutionSummary,
    APIScriptPackageManifest,
    APIScriptValidationIssue,
    APIScriptValidationResult,
    APITestScriptDraft,
    AutomationCandidate,
    BugDraft,
    DraftPackageGroupSummary,
    Evidence,
    ExecutionPlan,
    ExecutionPreflightIssue,
    ExecutionPreflightResult,
    ExecutionSafetyPolicy,
    ExecutionTarget,
    ExportBundle,
    FailureRecord,
    FailureSignature,
    RunSummary,
    ScriptGenerationGap,
    ScriptGenerationReadiness,
    TestRun,
    TestSuite,
    UnifiedDraftPackageSummary,
    WebPlaywrightGap,
    WebPlaywrightPackageManifest,
    WebPlaywrightReadiness,
    WebPlaywrightScriptDraft,
    WebPlaywrightValidationIssue,
    WebPlaywrightValidationResult,
)


class ManualQAExporter:
    """Export Manual QA content as JSON or Markdown."""

    def export_json_string(
        self,
        payload: object,
    ) -> str:
        return json.dumps(self._json_ready(payload), indent=2, ensure_ascii=False, sort_keys=True)

    def export_json_file(
        self,
        payload: object,
        path: Path | str,
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.export_json_string(payload), encoding="utf-8")
        return output_path

    def export_markdown_string(
        self,
        payload: object,
        *,
        title: Optional[str] = None,
    ) -> str:
        if isinstance(payload, dict) and self._is_api_execution_evidence_report(payload):
            return self._export_api_execution_evidence_report_markdown(payload, title=title)
        if isinstance(payload, list):
            if not payload:
                return f"# {title or 'Export'}\n"
            first_item = payload[0]
            if isinstance(first_item, APIExecutionEvidence):
                return self._export_api_execution_evidence_list_markdown(payload, title=title)
            if isinstance(first_item, BugDraft):
                return self._export_bug_draft_list_markdown(payload, title=title)
            if isinstance(first_item, FailureSignature):
                return self._export_failure_signature_list_markdown(payload, title=title)
            if isinstance(first_item, FailureRecord):
                return self._export_failure_record_list_markdown(payload, title=title)
            if isinstance(first_item, ScriptGenerationReadiness):
                return self._export_script_readiness_list_markdown(payload, title=title)
            if isinstance(first_item, APIExecutionResult):
                return self._export_api_execution_result_list_markdown(payload, title=title)
            if isinstance(first_item, APITestScriptDraft):
                return self._export_api_script_draft_list_markdown(payload, title=title)
            if isinstance(first_item, APIScriptValidationResult):
                return self._export_api_script_validation_result_list_markdown(payload, title=title)
            if isinstance(first_item, DraftPackageGroupSummary):
                return self._export_draft_package_group_summary_list_markdown(payload, title=title)
            if isinstance(first_item, ExecutionTarget):
                return self._export_execution_target_list_markdown(payload, title=title)
            if isinstance(first_item, ExecutionPreflightResult):
                return self._export_execution_preflight_result_list_markdown(payload, title=title)
            if isinstance(first_item, WebPlaywrightReadiness):
                return self._export_web_playwright_readiness_list_markdown(payload, title=title)
            if isinstance(first_item, WebPlaywrightScriptDraft):
                return self._export_web_playwright_script_draft_list_markdown(payload, title=title)
            if isinstance(first_item, WebPlaywrightValidationResult):
                return self._export_web_playwright_validation_result_list_markdown(payload, title=title)
            return self._export_automation_candidate_list_markdown(payload, title=title)
        if isinstance(payload, ExportBundle):
            return self._export_bundle_markdown(payload, title=title)
        if isinstance(payload, TestSuite):
            return self._export_suite_markdown(payload, title=title)
        if isinstance(payload, TestRun):
            return self._export_run_markdown(payload, title=title)
        if isinstance(payload, Evidence):
            return self._export_evidence_markdown(payload, title=title)
        if isinstance(payload, BugDraft):
            return self._export_bug_draft_markdown(payload, title=title)
        if isinstance(payload, FailureSignature):
            return self._export_failure_signature_markdown(payload, title=title)
        if isinstance(payload, FailureRecord):
            return self._export_failure_record_markdown(payload, title=title)
        if isinstance(payload, ScriptGenerationGap):
            return self._export_script_gap_markdown(payload, title=title)
        if isinstance(payload, ScriptGenerationReadiness):
            return self._export_script_readiness_markdown(payload, title=title)
        if isinstance(payload, APIExecutionEvidence):
            return self._export_api_execution_evidence_markdown(payload, title=title)
        if isinstance(payload, APIExecutionRequest):
            return self._export_api_execution_request_markdown(payload, title=title)
        if isinstance(payload, APIExecutionLogEntry):
            return self._export_api_execution_log_entry_markdown(payload, title=title)
        if isinstance(payload, APIExecutionResult):
            return self._export_api_execution_result_markdown(payload, title=title)
        if isinstance(payload, APIExecutionSummary):
            return self._export_api_execution_summary_markdown(payload, title=title)
        if isinstance(payload, APITestScriptDraft):
            return self._export_api_script_draft_markdown(payload, title=title)
        if isinstance(payload, APIScriptValidationIssue):
            return self._export_api_script_validation_issue_markdown(payload, title=title)
        if isinstance(payload, APIScriptValidationResult):
            return self._export_api_script_validation_result_markdown(payload, title=title)
        if isinstance(payload, APIScriptPackageManifest):
            return self._export_api_script_package_manifest_markdown(payload, title=title)
        if isinstance(payload, DraftPackageGroupSummary):
            return self._export_draft_package_group_summary_markdown(payload, title=title)
        if isinstance(payload, UnifiedDraftPackageSummary):
            return self._export_unified_draft_package_summary_markdown(payload, title=title)
        if isinstance(payload, ExecutionSafetyPolicy):
            return self._export_execution_safety_policy_markdown(payload, title=title)
        if isinstance(payload, ExecutionTarget):
            return self._export_execution_target_markdown(payload, title=title)
        if isinstance(payload, ExecutionPreflightIssue):
            return self._export_execution_preflight_issue_markdown(payload, title=title)
        if isinstance(payload, ExecutionPreflightResult):
            return self._export_execution_preflight_result_markdown(payload, title=title)
        if isinstance(payload, ExecutionPlan):
            return self._export_execution_plan_markdown(payload, title=title)
        if isinstance(payload, WebPlaywrightGap):
            return self._export_web_playwright_gap_markdown(payload, title=title)
        if isinstance(payload, WebPlaywrightReadiness):
            return self._export_web_playwright_readiness_markdown(payload, title=title)
        if isinstance(payload, WebPlaywrightScriptDraft):
            return self._export_web_playwright_script_draft_markdown(payload, title=title)
        if isinstance(payload, WebPlaywrightValidationIssue):
            return self._export_web_playwright_validation_issue_markdown(payload, title=title)
        if isinstance(payload, WebPlaywrightValidationResult):
            return self._export_web_playwright_validation_result_markdown(payload, title=title)
        if isinstance(payload, WebPlaywrightPackageManifest):
            return self._export_web_playwright_package_manifest_markdown(payload, title=title)
        if isinstance(payload, AutomationCandidate):
            return self._export_automation_candidate_markdown(payload, title=title)
        return self._export_summary_markdown(payload, title=title)

    def _json_ready(self, payload: object) -> object:
        if isinstance(payload, list):
            return [self._json_ready(item) for item in payload]
        if isinstance(payload, dict):
            return {str(key): self._json_ready(value) for key, value in payload.items()}
        if hasattr(payload, "to_dict"):
            return payload.to_dict()  # type: ignore[no-any-return]
        return payload

    def _is_api_execution_evidence_report(self, payload: dict[object, object]) -> bool:
        keys = {str(key) for key in payload.keys()}
        return {"evidence_items", "summary", "bug_suggestions", "failure_signatures"}.issubset(keys)

    def _export_bundle_markdown(
        self,
        bundle: ExportBundle,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Manual QA Export - {bundle.project.name}"
        lines = [
            f"# {heading}",
            "",
            "## Project",
            f"- Project ID: {bundle.project.project_id}",
            f"- Name: {bundle.project.name}",
            f"- Product Type: {bundle.project.product_type}",
            "",
            "## Requirements",
        ]

        for requirement in bundle.requirements:
            lines.extend(
                [
                    f"- {requirement.requirement_id}: {requirement.title}",
                    f"  Module: {requirement.module}",
                    f"  Priority: {requirement.priority}",
                ]
            )

        lines.extend(["", "## Checklist"])
        for item in bundle.checklist_items:
            lines.extend(
                [
                    f"- {item.checklist_id} [{item.requirement_id}] {item.title}",
                    f"  Priority: {item.priority}",
                    f"  Description: {item.description}",
                ]
            )

        lines.extend(["", "## Manual Test Cases"])
        for case in bundle.test_cases:
            lines.extend(
                [
                    f"- {case.test_case_id} [{', '.join(case.requirement_ids)}] {case.title}",
                    f"  Type: {case.test_type}",
                    f"  Status: {case.status}",
                    f"  Expected: {case.expected_result}",
                ]
            )

        lines.append("")
        return "\n".join(lines)

    def _export_suite_markdown(
        self,
        suite: TestSuite,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Manual Test Suite - {suite.name}"
        lines = [
            f"# {heading}",
            "",
            "## Suite",
            f"- Suite ID: {suite.suite_id}",
            f"- Project ID: {suite.project_id}",
            f"- Name: {suite.name}",
            f"- Scope: {suite.scope or 'N/A'}",
            f"- Owner: {suite.owner or 'N/A'}",
            "",
            "## Test Cases",
        ]
        for test_case_id in suite.test_case_ids:
            lines.append(f"- {test_case_id}")
        lines.append("")
        return "\n".join(lines)

    def _export_run_markdown(
        self,
        test_run: TestRun,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Manual Test Run - {test_run.run_id}"
        lines = [
            f"# {heading}",
            "",
            "## Run",
            f"- Run ID: {test_run.run_id}",
            f"- Project ID: {test_run.project_id}",
            f"- Suite ID: {test_run.suite_id}",
            f"- Environment: {test_run.environment or 'N/A'}",
            f"- Build: {test_run.build or 'N/A'}",
            f"- Tester: {test_run.tester or 'N/A'}",
            f"- Status: {test_run.status}",
            "",
            "## Results",
        ]
        for result in test_run.results:
            lines.extend(
                [
                    f"- {result.result_id} [{result.test_case_id}] {result.status}",
                    f"  Actual: {result.actual_result or 'N/A'}",
                    f"  Notes: {result.notes or 'N/A'}",
                ]
            )
        lines.append("")
        return "\n".join(lines)

    def _export_summary_markdown(
        self,
        summary: RunSummary,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Manual Test Run Summary - {summary.run_id}"
        lines = [
            f"# {heading}",
            "",
            "## Summary",
            f"- Run ID: {summary.run_id}",
            f"- Status: {summary.status}",
            f"- Total: {summary.total}",
            f"- Passed: {summary.passed}",
            f"- Failed: {summary.failed}",
            f"- Blocked: {summary.blocked}",
            f"- Skipped: {summary.skipped}",
            f"- Not Run: {summary.not_run}",
            f"- Retest: {summary.retest}",
            f"- Pass Rate: {summary.pass_rate}%",
            "",
        ]
        return "\n".join(lines)

    def _export_evidence_markdown(
        self,
        evidence: Evidence,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Evidence - {evidence.evidence_id}"
        lines = [
            f"# {heading}",
            "",
            "## Evidence",
            f"- Evidence ID: {evidence.evidence_id}",
            f"- Run ID: {evidence.run_id}",
            f"- Test Case ID: {evidence.test_case_id}",
            f"- Type: {evidence.evidence_type or 'N/A'}",
            f"- Reference: {evidence.path_or_url or 'N/A'}",
            f"- Description: {evidence.description or 'N/A'}",
            f"- Content Type: {evidence.content_type or 'N/A'}",
            f"- Created At: {evidence.created_at or 'N/A'}",
            "",
        ]
        return "\n".join(lines)

    def _export_bug_draft_markdown(
        self,
        bug_draft: BugDraft,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Bug Draft - {bug_draft.bug_id}"
        steps = bug_draft.steps_to_reproduce or ["No explicit steps provided."]
        evidence_ids = bug_draft.evidence_ids or ["None"]
        lines = [
            f"# {heading}",
            "",
            "## Title",
            bug_draft.title,
            "",
            "## Test Case ID",
            bug_draft.test_case_id,
            "",
            "## Severity",
            bug_draft.severity,
            "",
            "## Priority",
            bug_draft.priority,
            "",
            "## Environment",
            bug_draft.environment or "N/A",
            "",
            "## Build",
            bug_draft.build or "N/A",
            "",
            "## Steps to Reproduce",
        ]
        for step in steps:
            lines.append(f"- {step}")
        lines.extend(
            [
                "",
                "## Expected Result",
                bug_draft.expected_result or "N/A",
                "",
                "## Actual Result",
                bug_draft.actual_result or "N/A",
                "",
                "## Evidence IDs",
            ]
        )
        for evidence_id in evidence_ids:
            lines.append(f"- {evidence_id}")
        lines.extend(
            [
                "",
                "## Status",
                bug_draft.status,
                "",
            ]
        )
        return "\n".join(lines)

    def _export_failure_signature_markdown(
        self,
        signature: FailureSignature,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Failure Signature - {signature.signature_id}"
        lines = [
            f"# {heading}",
            "",
            "## Signature",
            f"- Signature ID: {signature.signature_id}",
            f"- Fingerprint: {signature.fingerprint}",
            f"- Module: {signature.module or 'N/A'}",
            f"- Test Case ID: {signature.test_case_id or 'N/A'}",
            f"- Title: {signature.title or 'N/A'}",
            f"- Symptom: {signature.symptom or 'N/A'}",
            f"- Expected Result: {signature.expected_result or 'N/A'}",
            f"- Actual Result: {signature.actual_result or 'N/A'}",
            f"- Environment: {signature.environment or 'N/A'}",
            f"- Build: {signature.build or 'N/A'}",
            f"- Severity: {signature.severity or 'N/A'}",
            f"- Priority: {signature.priority or 'N/A'}",
            f"- Source Bug ID: {signature.source_bug_id or 'N/A'}",
            "",
        ]
        return "\n".join(lines)

    def _export_failure_record_markdown(
        self,
        record: FailureRecord,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Failure Record - {record.record_id}"
        signature = record.signature
        lines = [
            f"# {heading}",
            "",
            "## Failure Record",
            f"- Record ID: {record.record_id}",
            f"- Signature ID: {signature.signature_id}",
            f"- Fingerprint: {signature.fingerprint}",
            f"- Module: {signature.module or 'N/A'}",
            f"- Test Case ID: {signature.test_case_id or 'N/A'}",
            f"- Title: {signature.title or 'N/A'}",
            f"- Symptom: {signature.symptom or 'N/A'}",
            f"- Expected Result: {signature.expected_result or 'N/A'}",
            f"- Actual Result: {signature.actual_result or 'N/A'}",
            f"- Severity: {signature.severity or 'N/A'}",
            f"- Priority: {signature.priority or 'N/A'}",
            f"- Occurrence Count: {record.occurrence_count}",
            f"- Related Bug IDs: {', '.join(record.related_bug_ids) if record.related_bug_ids else 'None'}",
            f"- Related Run IDs: {', '.join(record.related_run_ids) if record.related_run_ids else 'None'}",
            f"- Related Test Case IDs: {', '.join(record.related_test_case_ids) if record.related_test_case_ids else 'None'}",
            "",
        ]
        return "\n".join(lines)

    def _export_failure_record_list_markdown(
        self,
        records: list[FailureRecord],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Failure Records"
        lines = [f"# {heading}", ""]
        for record in records:
            lines.extend(
                [
                    f"## {record.record_id}",
                    f"- Signature ID: {record.signature.signature_id}",
                    f"- Fingerprint: {record.signature.fingerprint}",
                    f"- Occurrence Count: {record.occurrence_count}",
                    f"- Actual Result: {record.signature.actual_result or 'N/A'}",
                    f"- Related Bug IDs: {', '.join(record.related_bug_ids) if record.related_bug_ids else 'None'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_automation_candidate_markdown(
        self,
        candidate: AutomationCandidate,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Automation Candidate - {candidate.candidate_id}"
        reasons = candidate.reasons or ["None"]
        blockers = candidate.blockers or ["None"]
        related_records = candidate.related_failure_record_ids or ["None"]
        lines = [
            f"# {heading}",
            "",
            "## Candidate",
            f"- Candidate ID: {candidate.candidate_id}",
            f"- Test Case ID: {candidate.test_case_id}",
            f"- Module: {candidate.module or 'N/A'}",
            f"- Title: {candidate.title or 'N/A'}",
            f"- Score: {candidate.score}",
            f"- Recommendation: {candidate.recommendation}",
            f"- Suggested Automation Type: {candidate.suggested_automation_type}",
            "",
            "## Reasons",
        ]
        for reason in reasons:
            lines.append(f"- {reason}")
        lines.extend(["", "## Blockers"])
        for blocker in blockers:
            lines.append(f"- {blocker}")
        lines.extend(["", "## Related Failure Record IDs"])
        for record_id in related_records:
            lines.append(f"- {record_id}")
        lines.append("")
        return "\n".join(lines)

    def _export_automation_candidate_list_markdown(
        self,
        candidates: list[AutomationCandidate],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Automation Candidates"
        lines = [f"# {heading}", ""]
        for candidate in candidates:
            lines.extend(
                [
                    f"## {candidate.candidate_id}",
                    f"- Test Case ID: {candidate.test_case_id}",
                    f"- Score: {candidate.score}",
                    f"- Recommendation: {candidate.recommendation}",
                    f"- Suggested Automation Type: {candidate.suggested_automation_type}",
                    f"- Reasons: {', '.join(candidate.reasons) if candidate.reasons else 'None'}",
                    f"- Blockers: {', '.join(candidate.blockers) if candidate.blockers else 'None'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_script_gap_markdown(
        self,
        gap: ScriptGenerationGap,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Script Readiness Gap - {gap.gap_id}"
        lines = [
            f"# {heading}",
            "",
            "## Gap",
            f"- Gap ID: {gap.gap_id}",
            f"- Test Case ID: {gap.test_case_id}",
            f"- Gap Type: {gap.gap_type}",
            f"- Severity: {gap.severity}",
            f"- Message: {gap.message}",
            f"- Recommendation: {gap.recommendation}",
            "",
        ]
        return "\n".join(lines)

    def _export_script_readiness_markdown(
        self,
        readiness: ScriptGenerationReadiness,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Script Readiness - {readiness.readiness_id}"
        strengths = readiness.strengths or ["None"]
        gaps = readiness.gaps or []
        lines = [
            f"# {heading}",
            "",
            "## Readiness",
            f"- Readiness ID: {readiness.readiness_id}",
            f"- Test Case ID: {readiness.test_case_id}",
            f"- Module: {readiness.module or 'N/A'}",
            f"- Title: {readiness.title or 'N/A'}",
            f"- Target Type: {readiness.target_type}",
            f"- Readiness Status: {readiness.readiness_status}",
            f"- Readiness Score: {readiness.readiness_score}",
            f"- Automation Candidate ID: {readiness.automation_candidate_id or 'N/A'}",
            "",
            "## Strengths",
        ]
        for strength in strengths:
            lines.append(f"- {strength}")
        lines.extend(["", "## Gaps"])
        if not gaps:
            lines.append("- None")
        for gap in gaps:
            lines.append(
                f"- {gap.gap_id} [{gap.severity}] {gap.gap_type}: {gap.message} | Recommendation: {gap.recommendation}"
            )
        lines.extend(
            [
                "",
                "## Suggested Next Step",
                readiness.suggested_next_step or "N/A",
                "",
            ]
        )
        return "\n".join(lines)

    def _export_script_readiness_list_markdown(
        self,
        items: list[ScriptGenerationReadiness],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Script Readiness Report"
        lines = [f"# {heading}", ""]
        for item in items:
            lines.extend(
                [
                    f"## {item.readiness_id}",
                    f"- Test Case ID: {item.test_case_id}",
                    f"- Target Type: {item.target_type}",
                    f"- Readiness Status: {item.readiness_status}",
                    f"- Readiness Score: {item.readiness_score}",
                    f"- Strengths: {', '.join(item.strengths) if item.strengths else 'None'}",
                    f"- Gaps: {', '.join(gap.gap_type for gap in item.gaps) if item.gaps else 'None'}",
                    f"- Suggested Next Step: {item.suggested_next_step}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_api_execution_request_markdown(
        self,
        request: APIExecutionRequest,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"API Execution Request - {request.request_id}"
        lines = [
            f"# {heading}",
            "",
            "## Request",
            f"- Request ID: {request.request_id}",
            f"- Draft ID: {request.draft_id}",
            f"- Test Case ID: {request.test_case_id}",
            f"- File Name: {request.file_name}",
            f"- Method: {request.method}",
            f"- Base URL: {request.base_url or 'N/A'}",
            f"- Endpoint: {request.endpoint or 'N/A'}",
            f"- Timeout Seconds: {request.timeout_seconds}",
            f"- Policy ID: {request.policy_id or 'N/A'}",
            f"- Preflight ID: {request.preflight_id or 'N/A'}",
            f"- Dry Run: {request.dry_run}",
            "",
        ]
        return "\n".join(lines)

    def _export_api_execution_log_entry_markdown(
        self,
        entry: APIExecutionLogEntry,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"API Execution Log Entry - {entry.log_id}"
        lines = [
            f"# {heading}",
            "",
            "## Log",
            f"- Log ID: {entry.log_id}",
            f"- Level: {entry.level}",
            f"- Message: {entry.message}",
            "",
        ]
        return "\n".join(lines)

    def _export_api_execution_result_markdown(
        self,
        result: APIExecutionResult,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"API Execution Result - {result.execution_id}"
        lines = [
            f"# {heading}",
            "",
            "## Sandbox Warning",
            "This result is sandbox-only and does not update Manual QA run or result state.",
            "",
            "## Execution",
            f"- Execution ID: {result.execution_id}",
            f"- Status: {result.status}",
            f"- Draft ID: {result.request.draft_id}",
            f"- Test Case ID: {result.request.test_case_id}",
            f"- Method: {result.request.method}",
            f"- Base URL: {result.request.base_url or 'N/A'}",
            f"- Endpoint: {result.request.endpoint or 'N/A'}",
            f"- HTTP Status Code: {result.http_status_code if result.http_status_code is not None else 'N/A'}",
            f"- Assertion Expected Status: {result.assertion_expected_status if result.assertion_expected_status is not None else 'N/A'}",
            f"- Assertion Passed: {result.assertion_passed if result.assertion_passed is not None else 'N/A'}",
            f"- Duration Ms: {result.duration_ms}",
            f"- Dry Run Request: {result.request.dry_run}",
            f"- Error Type: {result.error_type or 'N/A'}",
            f"- Error Message: {result.error_message or 'N/A'}",
            "",
            "## Response Excerpt",
            result.response_excerpt or "N/A",
            "",
            "## Logs",
        ]
        for entry in result.logs or []:
            lines.append(f"- {entry.log_id} [{entry.level}] {entry.message}")
        if not result.logs:
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)

    def _export_api_execution_result_list_markdown(
        self,
        results: list[APIExecutionResult],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "API Sandbox Execution Results"
        lines = [f"# {heading}", "", "This report is sandbox-only and does not update Manual QA result state.", ""]
        for result in results:
            lines.extend(
                [
                    f"## {result.execution_id}",
                    f"- Status: {result.status}",
                    f"- Draft ID: {result.request.draft_id}",
                    f"- Test Case ID: {result.request.test_case_id}",
                    f"- Method: {result.request.method}",
                    f"- Base URL: {result.request.base_url or 'N/A'}",
                    f"- Endpoint: {result.request.endpoint or 'N/A'}",
                    f"- HTTP Status Code: {result.http_status_code if result.http_status_code is not None else 'N/A'}",
                    f"- Assertion Passed: {result.assertion_passed if result.assertion_passed is not None else 'N/A'}",
                    f"- Duration Ms: {result.duration_ms}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_api_execution_evidence_markdown(
        self,
        evidence: APIExecutionEvidence,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"API Execution Evidence - {evidence.evidence_id}"
        lines = [
            f"# {heading}",
            "",
            "## Warning",
            "This evidence is sandbox-only and does not overwrite Manual QA TestResult state.",
            "",
            "## Evidence",
            f"- Evidence ID: {evidence.evidence_id}",
            f"- Execution ID: {evidence.execution_id}",
            f"- Draft ID: {evidence.draft_id}",
            f"- Test Case ID: {evidence.test_case_id}",
            f"- Status: {evidence.status}",
            f"- Method: {evidence.method}",
            f"- Base URL: {evidence.base_url or 'N/A'}",
            f"- Endpoint: {evidence.endpoint or 'N/A'}",
            f"- HTTP Status Code: {evidence.http_status_code if evidence.http_status_code is not None else 'N/A'}",
            f"- Assertion Passed: {evidence.assertion_passed if evidence.assertion_passed is not None else 'N/A'}",
            f"- Error Type: {evidence.error_type or 'N/A'}",
            f"- Error Message: {evidence.error_message or 'N/A'}",
            "",
            "## Summary",
            evidence.summary or "N/A",
            "",
            "## Response Excerpt",
            evidence.response_excerpt or "N/A",
            "",
            "## Log Refs",
        ]
        for log_ref in evidence.log_refs:
            lines.append(f"- {log_ref}")
        if not evidence.log_refs:
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)

    def _export_api_execution_evidence_list_markdown(
        self,
        evidence_items: list[APIExecutionEvidence],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "API Execution Evidence"
        lines = [f"# {heading}", "", "This evidence is sandbox-only and does not overwrite Manual QA TestResult state.", ""]
        for evidence in evidence_items:
            lines.extend(
                [
                    f"## {evidence.evidence_id}",
                    f"- Execution ID: {evidence.execution_id}",
                    f"- Draft ID: {evidence.draft_id}",
                    f"- Test Case ID: {evidence.test_case_id}",
                    f"- Status: {evidence.status}",
                    f"- Method: {evidence.method}",
                    f"- Endpoint: {evidence.endpoint or 'N/A'}",
                    f"- HTTP Status Code: {evidence.http_status_code if evidence.http_status_code is not None else 'N/A'}",
                    f"- Assertion Passed: {evidence.assertion_passed if evidence.assertion_passed is not None else 'N/A'}",
                    f"- Summary: {evidence.summary or 'N/A'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_api_execution_summary_markdown(
        self,
        summary: APIExecutionSummary,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"API Execution Summary - {summary.summary_id}"
        lines = [
            f"# {heading}",
            "",
            "## Warning",
            "This summary is sandbox-only and does not overwrite Manual QA TestResult state.",
            "",
            "## Summary",
            f"- Summary ID: {summary.summary_id}",
            f"- Status: {summary.status}",
            f"- Total: {summary.total}",
            f"- Passed: {summary.passed}",
            f"- Failed: {summary.failed}",
            f"- Blocked: {summary.blocked}",
            f"- Dry Run: {summary.dry_run}",
            f"- Error: {summary.error}",
            f"- Not Run: {summary.not_run}",
            f"- Pass Rate: {summary.pass_rate}",
            f"- Failure Rate: {summary.failure_rate}",
            f"- Recommended Next Step: {summary.recommended_next_step or 'N/A'}",
            "",
            "## Related IDs",
            f"- Evidence IDs: {', '.join(summary.evidence_ids) if summary.evidence_ids else 'None'}",
            f"- Bug Suggestion IDs: {', '.join(summary.bug_suggestion_ids) if summary.bug_suggestion_ids else 'None'}",
            f"- Failure Signature IDs: {', '.join(summary.failure_signature_ids) if summary.failure_signature_ids else 'None'}",
            "",
        ]
        return "\n".join(lines)

    def _export_bug_draft_list_markdown(
        self,
        bugs: list[BugDraft],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Bug Draft Suggestions"
        lines = [f"# {heading}", ""]
        for bug in bugs:
            lines.extend(
                [
                    f"## {bug.bug_id}",
                    f"- Test Case ID: {bug.test_case_id}",
                    f"- Title: {bug.title}",
                    f"- Severity: {bug.severity}",
                    f"- Priority: {bug.priority}",
                    f"- Status: {bug.status}",
                    f"- Actual Result: {bug.actual_result or 'N/A'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_failure_signature_list_markdown(
        self,
        signatures: list[FailureSignature],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Failure Signatures"
        lines = [f"# {heading}", ""]
        for signature in signatures:
            lines.extend(
                [
                    f"## {signature.signature_id}",
                    f"- Fingerprint: {signature.fingerprint}",
                    f"- Test Case ID: {signature.test_case_id or 'N/A'}",
                    f"- Title: {signature.title or 'N/A'}",
                    f"- Symptom: {signature.symptom or 'N/A'}",
                    f"- Actual Result: {signature.actual_result or 'N/A'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_api_execution_evidence_report_markdown(
        self,
        report: dict[str, object],
        *,
        title: Optional[str] = None,
    ) -> str:
        summary = report.get("summary")
        evidence_items = report.get("evidence_items")
        bug_suggestions = report.get("bug_suggestions")
        failure_signatures = report.get("failure_signatures")

        if not isinstance(summary, APIExecutionSummary):
            return f"# {title or 'API Execution Evidence Report'}\n"

        lines = [
            f"# {title or 'API Execution Evidence Report'}",
            "",
            "This report is sandbox-only and does not overwrite Manual QA TestResult state.",
            "",
            "## Summary",
            f"- Summary Status: {summary.status}",
            f"- Total: {summary.total}",
            f"- Passed: {summary.passed}",
            f"- Failed: {summary.failed}",
            f"- Blocked: {summary.blocked}",
            f"- Dry Run: {summary.dry_run}",
            f"- Error: {summary.error}",
            f"- Pass Rate: {summary.pass_rate}",
            f"- Failure Rate: {summary.failure_rate}",
            f"- Recommended Next Step: {summary.recommended_next_step or 'N/A'}",
            "",
            "## Evidence",
        ]
        if isinstance(evidence_items, list) and evidence_items:
            for evidence in evidence_items:
                if not isinstance(evidence, APIExecutionEvidence):
                    continue
                lines.append(
                    f"- {evidence.evidence_id} [{evidence.status}] {evidence.test_case_id} "
                    f"{evidence.method} {evidence.endpoint}"
                )
        else:
            lines.append("- None")

        lines.extend(["", "## Failed Or Error Details"])
        if isinstance(evidence_items, list):
            failed_items = [
                item for item in evidence_items
                if isinstance(item, APIExecutionEvidence) and item.status in {"Failed", "Error"}
            ]
            if failed_items:
                for item in failed_items:
                    lines.append(
                        f"- {item.evidence_id}: HTTP {item.http_status_code if item.http_status_code is not None else 'N/A'} "
                        f"| Error: {item.error_message or item.error_type or 'N/A'}"
                    )
            else:
                lines.append("- None")
        else:
            lines.append("- None")

        lines.extend(["", "## Bug Suggestions"])
        if isinstance(bug_suggestions, list) and bug_suggestions:
            for bug in bug_suggestions:
                if isinstance(bug, BugDraft):
                    lines.append(f"- {bug.bug_id}: {bug.title}")
        else:
            lines.append("- None")

        lines.extend(["", "## Failure Signatures"])
        if isinstance(failure_signatures, list) and failure_signatures:
            for signature in failure_signatures:
                if isinstance(signature, FailureSignature):
                    lines.append(f"- {signature.signature_id}: {signature.fingerprint}")
        else:
            lines.append("- None")

        lines.append("")
        return "\n".join(lines)

    def _export_api_script_draft_markdown(
        self,
        draft: APITestScriptDraft,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"API Script Draft - {draft.draft_id}"
        warnings = draft.warnings or ["None"]
        assumptions = draft.assumptions or ["None"]
        lines = [
            f"# {heading}",
            "",
            "## Draft",
            f"- Draft ID: {draft.draft_id}",
            f"- Test Case ID: {draft.test_case_id}",
            f"- Requirement IDs: {', '.join(draft.requirement_ids) if draft.requirement_ids else 'None'}",
            f"- Title: {draft.title or 'N/A'}",
            f"- Readiness ID: {draft.readiness_id or 'N/A'}",
            f"- Framework: {draft.framework}",
            f"- Language: {draft.language}",
            f"- File Name: {draft.file_name}",
            f"- Status: {draft.status}",
            "",
            "## Warnings",
        ]
        for item in warnings:
            lines.append(f"- {item}")
        lines.extend(["", "## Assumptions"])
        for item in assumptions:
            lines.append(f"- {item}")
        lines.extend(["", "## Script Content", "```python", draft.script_content, "```", ""])
        return "\n".join(lines)

    def _export_api_script_draft_list_markdown(
        self,
        drafts: list[APITestScriptDraft],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "API Script Drafts"
        lines = [f"# {heading}", ""]
        for draft in drafts:
            lines.extend(
                [
                    f"## {draft.draft_id}",
                    f"- Test Case ID: {draft.test_case_id}",
                    f"- Readiness ID: {draft.readiness_id or 'N/A'}",
                    f"- File Name: {draft.file_name}",
                    f"- Status: {draft.status}",
                    f"- Warnings: {', '.join(draft.warnings) if draft.warnings else 'None'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_api_script_validation_issue_markdown(
        self,
        issue: APIScriptValidationIssue,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"API Script Validation Issue - {issue.issue_id}"
        lines = [
            f"# {heading}",
            "",
            "## Issue",
            f"- Issue ID: {issue.issue_id}",
            f"- Draft ID: {issue.draft_id}",
            f"- Severity: {issue.severity}",
            f"- Issue Type: {issue.issue_type}",
            f"- Message: {issue.message}",
            f"- Recommendation: {issue.recommendation}",
            "",
        ]
        return "\n".join(lines)

    def _export_api_script_validation_result_markdown(
        self,
        result: APIScriptValidationResult,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"API Script Validation - {result.validation_id}"
        issues = result.issues or []
        lines = [
            f"# {heading}",
            "",
            "## Validation",
            f"- Validation ID: {result.validation_id}",
            f"- Draft ID: {result.draft_id}",
            f"- Test Case ID: {result.test_case_id}",
            f"- File Name: {result.file_name}",
            f"- Is Valid: {result.is_valid}",
            f"- Syntax Valid: {result.syntax_valid}",
            f"- Has Draft Warning: {result.has_draft_warning}",
            f"- Has No Execution Marker: {result.has_no_execution_marker}",
            f"- Has Status Assertion: {result.has_status_assertion}",
            f"- Has TODO Endpoint: {result.has_todo_endpoint}",
            f"- Has TODO Payload: {result.has_todo_payload}",
            "",
            "## Issues",
        ]
        if not issues:
            lines.append("- None")
        for issue in issues:
            lines.append(
                f"- {issue.issue_id} [{issue.severity}] {issue.issue_type}: {issue.message} | Recommendation: {issue.recommendation}"
            )
        lines.append("")
        return "\n".join(lines)

    def _export_api_script_validation_result_list_markdown(
        self,
        results: list[APIScriptValidationResult],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "API Script Validation Report"
        lines = [f"# {heading}", ""]
        for result in results:
            issue_types = ", ".join(issue.issue_type for issue in result.issues) if result.issues else "None"
            lines.extend(
                [
                    f"## {result.validation_id}",
                    f"- Draft ID: {result.draft_id}",
                    f"- File Name: {result.file_name}",
                    f"- Is Valid: {result.is_valid}",
                    f"- Syntax Valid: {result.syntax_valid}",
                    f"- TODO Endpoint: {result.has_todo_endpoint}",
                    f"- TODO Payload: {result.has_todo_payload}",
                    f"- Issue List: {issue_types}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_api_script_package_manifest_markdown(
        self,
        manifest: APIScriptPackageManifest,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"API Script Package Manifest - {manifest.package_id}"
        lines = [
            f"# {heading}",
            "",
            "## Package",
            f"- Package ID: {manifest.package_id}",
            f"- Package Name: {manifest.package_name}",
            f"- Package Status: {manifest.status}",
            f"- Draft Count: {manifest.draft_count}",
            f"- Valid Count: {manifest.valid_count}",
            f"- Invalid Count: {manifest.invalid_count}",
            f"- Warning Count: {manifest.warning_count}",
            "",
            "## Draft Files",
        ]
        for draft_file in manifest.draft_files or ["None"]:
            lines.append(f"- {draft_file}")
        lines.extend(["", "## Validation Report Files"])
        for report_file in manifest.validation_report_files or ["None"]:
            lines.append(f"- {report_file}")
        lines.append("")
        return "\n".join(lines)

    def _export_web_playwright_gap_markdown(
        self,
        gap: WebPlaywrightGap,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Web Playwright Gap - {gap.gap_id}"
        lines = [
            f"# {heading}",
            "",
            "## Gap",
            f"- Gap ID: {gap.gap_id}",
            f"- Test Case ID: {gap.test_case_id}",
            f"- Gap Type: {gap.gap_type}",
            f"- Severity: {gap.severity}",
            f"- Message: {gap.message}",
            f"- Recommendation: {gap.recommendation}",
            "",
        ]
        return "\n".join(lines)

    def _export_web_playwright_readiness_markdown(
        self,
        readiness: WebPlaywrightReadiness,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Web Playwright Readiness - {readiness.readiness_id}"
        lines = [
            f"# {heading}",
            "",
            "## Readiness",
            f"- Readiness ID: {readiness.readiness_id}",
            f"- Test Case ID: {readiness.test_case_id}",
            f"- Module: {readiness.module or 'N/A'}",
            f"- Title: {readiness.title or 'N/A'}",
            f"- Readiness Status: {readiness.readiness_status}",
            f"- Readiness Score: {readiness.readiness_score}",
            f"- Page URL: {readiness.page_url or 'N/A'}",
            f"- Automation Candidate ID: {readiness.automation_candidate_id or 'N/A'}",
            "",
            "## Selector Hints",
        ]
        for item in readiness.selector_hints or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Action Hints"])
        for item in readiness.action_hints or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Assertion Hints"])
        for item in readiness.assertion_hints or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Strengths"])
        for item in readiness.strengths or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Gaps"])
        if not readiness.gaps:
            lines.append("- None")
        for gap in readiness.gaps:
            lines.append(
                f"- {gap.gap_id} [{gap.severity}] {gap.gap_type}: {gap.message} | Recommendation: {gap.recommendation}"
            )
        lines.extend(["", "## Suggested Next Step", readiness.suggested_next_step or "N/A", ""])
        return "\n".join(lines)

    def _export_web_playwright_readiness_list_markdown(
        self,
        items: list[WebPlaywrightReadiness],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Web Playwright Readiness Report"
        lines = [f"# {heading}", ""]
        for item in items:
            lines.extend(
                [
                    f"## {item.readiness_id}",
                    f"- Test Case ID: {item.test_case_id}",
                    f"- Module: {item.module or 'N/A'}",
                    f"- Title: {item.title or 'N/A'}",
                    f"- Readiness Status: {item.readiness_status}",
                    f"- Readiness Score: {item.readiness_score}",
                    f"- Page URL: {item.page_url or 'N/A'}",
                    f"- Selector Hints: {', '.join(item.selector_hints) if item.selector_hints else 'None'}",
                    f"- Action Hints: {', '.join(item.action_hints) if item.action_hints else 'None'}",
                    f"- Assertion Hints: {', '.join(item.assertion_hints) if item.assertion_hints else 'None'}",
                    f"- Strengths: {', '.join(item.strengths) if item.strengths else 'None'}",
                    f"- Gaps: {', '.join(gap.gap_type for gap in item.gaps) if item.gaps else 'None'}",
                    f"- Suggested Next Step: {item.suggested_next_step}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_web_playwright_script_draft_markdown(
        self,
        draft: WebPlaywrightScriptDraft,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Web Playwright Script Draft - {draft.draft_id}"
        warnings = draft.warnings or ["None"]
        assumptions = draft.assumptions or ["None"]
        lines = [
            f"# {heading}",
            "",
            "## Draft",
            f"- Draft ID: {draft.draft_id}",
            f"- Test Case ID: {draft.test_case_id}",
            f"- Requirement IDs: {', '.join(draft.requirement_ids) if draft.requirement_ids else 'None'}",
            f"- Title: {draft.title or 'N/A'}",
            f"- Readiness ID: {draft.readiness_id or 'N/A'}",
            f"- Framework: {draft.framework}",
            f"- Language: {draft.language}",
            f"- File Name: {draft.file_name}",
            f"- Status: {draft.status}",
            "",
            "## Warnings",
        ]
        for item in warnings:
            lines.append(f"- {item}")
        lines.extend(["", "## Assumptions"])
        for item in assumptions:
            lines.append(f"- {item}")
        lines.extend(["", "## Script Content", "```python", draft.script_content, "```", ""])
        return "\n".join(lines)

    def _export_web_playwright_script_draft_list_markdown(
        self,
        drafts: list[WebPlaywrightScriptDraft],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Web Playwright Script Drafts"
        lines = [f"# {heading}", ""]
        for draft in drafts:
            lines.extend(
                [
                    f"## {draft.draft_id}",
                    f"- Test Case ID: {draft.test_case_id}",
                    f"- Requirement IDs: {', '.join(draft.requirement_ids) if draft.requirement_ids else 'None'}",
                    f"- Readiness ID: {draft.readiness_id or 'N/A'}",
                    f"- File Name: {draft.file_name}",
                    f"- Status: {draft.status}",
                    f"- Warnings: {', '.join(draft.warnings) if draft.warnings else 'None'}",
                    f"- Assumptions: {', '.join(draft.assumptions) if draft.assumptions else 'None'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_web_playwright_validation_issue_markdown(
        self,
        issue: WebPlaywrightValidationIssue,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Web Playwright Validation Issue - {issue.issue_id}"
        lines = [
            f"# {heading}",
            "",
            "## Issue",
            f"- Issue ID: {issue.issue_id}",
            f"- Draft ID: {issue.draft_id}",
            f"- Severity: {issue.severity}",
            f"- Issue Type: {issue.issue_type}",
            f"- Message: {issue.message}",
            f"- Recommendation: {issue.recommendation}",
            "",
        ]
        return "\n".join(lines)

    def _export_web_playwright_validation_result_markdown(
        self,
        result: WebPlaywrightValidationResult,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Web Playwright Validation - {result.validation_id}"
        issues = result.issues or []
        lines = [
            f"# {heading}",
            "",
            "## Validation",
            f"- Validation ID: {result.validation_id}",
            f"- Draft ID: {result.draft_id}",
            f"- Test Case ID: {result.test_case_id}",
            f"- File Name: {result.file_name}",
            f"- Is Valid: {result.is_valid}",
            f"- Syntax Valid: {result.syntax_valid}",
            f"- Has Draft Warning: {result.has_draft_warning}",
            f"- Has No Execution Marker: {result.has_no_execution_marker}",
            f"- Has Playwright Import: {result.has_playwright_import}",
            f"- Has Test Function: {result.has_test_function}",
            f"- Has page.goto: {result.has_page_goto}",
            f"- Has Locator Or TODO: {result.has_locator_or_todo}",
            f"- Has Action Or TODO: {result.has_action_or_todo}",
            f"- Has Assertion Or TODO: {result.has_assertion_or_todo}",
            f"- Has TODO Page URL: {result.has_todo_page_url}",
            f"- Has TODO Selector: {result.has_todo_selector}",
            f"- Has TODO Assertion: {result.has_todo_assertion}",
            "",
            "## Issues",
        ]
        if not issues:
            lines.append("- None")
        for issue in issues:
            lines.append(
                f"- {issue.issue_id} [{issue.severity}] {issue.issue_type}: {issue.message} | Recommendation: {issue.recommendation}"
            )
        lines.append("")
        return "\n".join(lines)

    def _export_web_playwright_validation_result_list_markdown(
        self,
        results: list[WebPlaywrightValidationResult],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Web Playwright Validation Report"
        lines = [f"# {heading}", ""]
        for result in results:
            issue_types = ", ".join(issue.issue_type for issue in result.issues) if result.issues else "None"
            lines.extend(
                [
                    f"## {result.validation_id}",
                    f"- Draft ID: {result.draft_id}",
                    f"- File Name: {result.file_name}",
                    f"- Is Valid: {result.is_valid}",
                    f"- Syntax Valid: {result.syntax_valid}",
                    f"- TODO Page URL: {result.has_todo_page_url}",
                    f"- TODO Selector: {result.has_todo_selector}",
                    f"- TODO Assertion: {result.has_todo_assertion}",
                    f"- Issue List: {issue_types}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_web_playwright_package_manifest_markdown(
        self,
        manifest: WebPlaywrightPackageManifest,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Web Playwright Package Manifest - {manifest.package_id}"
        lines = [
            f"# {heading}",
            "",
            "## Package",
            f"- Package ID: {manifest.package_id}",
            f"- Package Name: {manifest.package_name}",
            f"- Package Status: {manifest.status}",
            f"- Draft Count: {manifest.draft_count}",
            f"- Valid Count: {manifest.valid_count}",
            f"- Invalid Count: {manifest.invalid_count}",
            f"- Warning Count: {manifest.warning_count}",
            "",
            "## Draft Files",
        ]
        for draft_file in manifest.draft_files or ["None"]:
            lines.append(f"- {draft_file}")
        lines.extend(["", "## Validation Report Files"])
        for report_file in manifest.validation_report_files or ["None"]:
            lines.append(f"- {report_file}")
        lines.append("")
        return "\n".join(lines)

    def _export_draft_package_group_summary_markdown(
        self,
        group: DraftPackageGroupSummary,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Draft Package Group Summary - {group.group_id}"
        lines = [
            f"# {heading}",
            "",
            "## Group",
            f"- Group ID: {group.group_id}",
            f"- Group Type: {group.group_type}",
            f"- Status: {group.status}",
            f"- Missing: {group.missing}",
            f"- Manifest Path: {group.manifest_path}",
            f"- Validation Path: {group.validation_path}",
            f"- Draft Count: {group.draft_count}",
            f"- Valid Count: {group.valid_count}",
            f"- Invalid Count: {group.invalid_count}",
            f"- Warning Count: {group.warning_count}",
            f"- Ready for Review Count: {group.ready_for_review_count}",
            f"- Needs Attention Count: {group.needs_attention_count}",
            f"- Invalid Item Count: {group.invalid_item_count}",
            "",
            "## Notes",
        ]
        for note in group.notes or ["None"]:
            lines.append(f"- {note}")
        lines.append("")
        return "\n".join(lines)

    def _export_draft_package_group_summary_list_markdown(
        self,
        groups: list[DraftPackageGroupSummary],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Draft Package Group Summaries"
        lines = [f"# {heading}", ""]
        for group in groups:
            lines.extend(
                [
                    f"## {group.group_type}",
                    f"- Status: {group.status}",
                    f"- Draft Count: {group.draft_count}",
                    f"- Valid Count: {group.valid_count}",
                    f"- Invalid Count: {group.invalid_count}",
                    f"- Warning Count: {group.warning_count}",
                    f"- Missing: {group.missing}",
                    f"- Notes: {', '.join(group.notes) if group.notes else 'None'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_unified_draft_package_summary_markdown(
        self,
        summary: UnifiedDraftPackageSummary,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Unified Draft Package Summary"
        lines = [
            f"# {heading}",
            "",
            "## Overview",
            f"- Summary ID: {summary.summary_id}",
            f"- Workspace Path: {summary.workspace_path}",
            f"- Overall Status: {summary.overall_status}",
            f"- Recommended Next Step: {summary.recommended_next_step}",
            f"- Total Drafts: {summary.total_drafts}",
            f"- Total Valid: {summary.total_valid}",
            f"- Total Invalid: {summary.total_invalid}",
            f"- Total Warnings: {summary.total_warnings}",
            f"- Ready Groups: {summary.ready_groups}",
            f"- Needs Attention Groups: {summary.needs_attention_groups}",
            f"- Invalid Groups: {summary.invalid_groups}",
            f"- Missing Groups: {summary.missing_groups}",
            "",
        ]

        group_by_type = {group.group_type: group for group in summary.groups}
        for section_title, group_key in (
            ("API Group Summary", "api"),
            ("Web Playwright Group Summary", "web_playwright"),
        ):
            group = group_by_type.get(group_key)
            lines.append(f"## {section_title}")
            if group is None:
                lines.extend(["- Status: Missing", "- Notes: Group was not summarized.", ""])
                continue
            lines.extend(
                [
                    f"- Status: {group.status}",
                    f"- Manifest Path: {group.manifest_path}",
                    f"- Validation Path: {group.validation_path}",
                    f"- Draft Count: {group.draft_count}",
                    f"- Valid Count: {group.valid_count}",
                    f"- Invalid Count: {group.invalid_count}",
                    f"- Warning Count: {group.warning_count}",
                    f"- Ready for Review Count: {group.ready_for_review_count}",
                    f"- Needs Attention Count: {group.needs_attention_count}",
                    f"- Invalid Item Count: {group.invalid_item_count}",
                    f"- Missing: {group.missing}",
                ]
            )
            lines.append("- Notes:")
            for note in group.notes or ["None"]:
                lines.append(f"  - {note}")
            lines.append("")

        missing_group_names = [group.group_type for group in summary.groups if group.missing]
        lines.append("## Missing Groups")
        for group_name in missing_group_names or ["None"]:
            lines.append(f"- {group_name}")
        lines.append("")

        all_notes = [
            f"{group.group_type}: {note}"
            for group in summary.groups
            for note in group.notes
        ]
        lines.append("## Notes")
        for note in all_notes or ["None"]:
            lines.append(f"- {note}")
        lines.append("")
        return "\n".join(lines)

    def _export_execution_safety_policy_markdown(
        self,
        policy: ExecutionSafetyPolicy,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Execution Safety Policy - {policy.name}"
        lines = [
            f"# {heading}",
            "",
            "## Policy Summary",
            f"- Policy ID: {policy.policy_id}",
            f"- Name: {policy.name}",
            f"- Allow Execution: {policy.allow_execution}",
            f"- Dry Run Only: {policy.dry_run_only}",
            f"- Require Human Approval: {policy.require_human_approval}",
            f"- Require Valid Package: {policy.require_valid_package}",
            f"- Require No Critical TODOs: {policy.require_no_critical_todos}",
            f"- Allow Write Methods: {policy.allow_write_methods}",
            f"- Allow Delete Methods: {policy.allow_delete_methods}",
            f"- Timeout Seconds: {policy.timeout_seconds}",
            f"- Max Scripts Per Run: {policy.max_scripts_per_run}",
            "",
            "## Allowed Base URLs",
        ]
        for item in policy.allowed_base_urls or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Blocked Base URLs"])
        for item in policy.blocked_base_urls or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Allowed Script Types"])
        for item in policy.allowed_script_types or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Blocked Script Types"])
        for item in policy.blocked_script_types or ["None"]:
            lines.append(f"- {item}")
        lines.append("")
        return "\n".join(lines)

    def _export_execution_target_markdown(
        self,
        target: ExecutionTarget,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Execution Target - {target.target_id}"
        lines = [
            f"# {heading}",
            "",
            "## Target",
            f"- Target ID: {target.target_id}",
            f"- Script Type: {target.script_type}",
            f"- Draft ID: {target.draft_id}",
            f"- File Name: {target.file_name}",
            f"- Package Status: {target.package_status}",
            f"- Validation Status: {target.validation_status}",
            f"- Base URL: {target.base_url or 'N/A'}",
            f"- Method: {target.method or 'N/A'}",
            f"- Endpoint Or Page: {target.endpoint_or_page or 'N/A'}",
            f"- Has TODOs: {target.has_todos}",
            f"- Has Critical TODOs: {target.has_critical_todos}",
            "",
        ]
        return "\n".join(lines)

    def _export_execution_target_list_markdown(
        self,
        targets: list[ExecutionTarget],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Execution Targets"
        lines = [f"# {heading}", ""]
        for target in targets:
            lines.extend(
                [
                    f"## {target.target_id}",
                    f"- Script Type: {target.script_type}",
                    f"- Package Status: {target.package_status}",
                    f"- Validation Status: {target.validation_status}",
                    f"- Base URL: {target.base_url or 'N/A'}",
                    f"- Method: {target.method or 'N/A'}",
                    f"- Endpoint Or Page: {target.endpoint_or_page or 'N/A'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_execution_preflight_issue_markdown(
        self,
        issue: ExecutionPreflightIssue,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Execution Preflight Issue - {issue.issue_id}"
        lines = [
            f"# {heading}",
            "",
            "## Issue",
            f"- Issue ID: {issue.issue_id}",
            f"- Target ID: {issue.target_id}",
            f"- Severity: {issue.severity}",
            f"- Issue Type: {issue.issue_type}",
            f"- Message: {issue.message}",
            f"- Recommendation: {issue.recommendation}",
            "",
        ]
        return "\n".join(lines)

    def _export_execution_preflight_result_markdown(
        self,
        result: ExecutionPreflightResult,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Execution Preflight Result - {result.preflight_id}"
        lines = [
            f"# {heading}",
            "",
            "## Result",
            f"- Preflight ID: {result.preflight_id}",
            f"- Target ID: {result.target_id}",
            f"- Script Type: {result.script_type}",
            f"- Decision: {result.decision}",
            f"- Is Allowed: {result.is_allowed}",
            f"- Risk Level: {result.risk_level}",
            f"- Recommended Action: {result.recommended_action}",
            "",
            "## Issues",
        ]
        for issue in result.issues or []:
            lines.append(
                f"- {issue.issue_id} [{issue.severity}] {issue.issue_type}: {issue.message} | Recommendation: {issue.recommendation}"
            )
        if not result.issues:
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)

    def _export_execution_preflight_result_list_markdown(
        self,
        results: list[ExecutionPreflightResult],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Execution Preflight Results"
        lines = [f"# {heading}", ""]
        for result in results:
            issue_types = ", ".join(issue.issue_type for issue in result.issues) if result.issues else "None"
            lines.extend(
                [
                    f"## {result.preflight_id}",
                    f"- Target ID: {result.target_id}",
                    f"- Script Type: {result.script_type}",
                    f"- Decision: {result.decision}",
                    f"- Risk Level: {result.risk_level}",
                    f"- Issue List: {issue_types}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_execution_plan_markdown(
        self,
        plan: ExecutionPlan,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Execution Preflight Plan"
        lines = [
            f"# {heading}",
            "",
            "## Policy Summary",
            f"- Policy Name: {plan.policy.name}",
            f"- Allow Execution: {plan.policy.allow_execution}",
            f"- Dry Run Only: {plan.policy.dry_run_only}",
            f"- Require Human Approval: {plan.policy.require_human_approval}",
            "",
            "## Overview",
            f"- Overall Decision: {plan.overall_decision}",
            f"- Recommended Next Step: {plan.recommended_next_step}",
            f"- Total Targets: {plan.total_targets}",
            f"- Allowed Count: {plan.allowed_count}",
            f"- Blocked Count: {plan.blocked_count}",
            f"- Needs Approval Count: {plan.needs_approval_count}",
            f"- Dry Run Only: {plan.dry_run_only}",
            "",
            "## Targets",
        ]
        for target in plan.targets or []:
            lines.append(
                f"- {target.target_id} [{target.script_type}] {target.file_name} | "
                f"package={target.package_status} validation={target.validation_status} "
                f"base_url={target.base_url or 'N/A'} method={target.method or 'N/A'}"
            )
        if not plan.targets:
            lines.append("- None")
        lines.extend(["", "## Preflight Results"])
        for result in plan.preflight_results or []:
            lines.append(
                f"- {result.target_id}: decision={result.decision} risk={result.risk_level} "
                f"issues={len(result.issues)}"
            )
        if not plan.preflight_results:
            lines.append("- None")
        lines.extend(["", "## Issues"])
        issue_lines = [
            f"- {result.target_id} [{issue.severity}] {issue.issue_type}: {issue.message}"
            for result in plan.preflight_results
            for issue in result.issues
        ]
        for item in issue_lines or ["- None"]:
            lines.append(item)
        lines.extend(["", "## Risk Levels"])
        risk_lines = [
            f"- {result.target_id}: {result.risk_level}"
            for result in plan.preflight_results
        ]
        for item in risk_lines or ["- None"]:
            lines.append(item)
        lines.append("")
        return "\n".join(lines)

    def export_markdown_file(
        self,
        payload: ExportBundle | TestSuite | TestRun | RunSummary | Evidence | BugDraft | FailureSignature | FailureRecord | AutomationCandidate | ScriptGenerationGap | ScriptGenerationReadiness | APITestScriptDraft | APIScriptValidationIssue | APIScriptValidationResult | APIScriptPackageManifest | WebPlaywrightGap | WebPlaywrightReadiness | WebPlaywrightScriptDraft | WebPlaywrightValidationIssue | WebPlaywrightValidationResult | WebPlaywrightPackageManifest | list[FailureRecord] | list[AutomationCandidate] | list[ScriptGenerationReadiness] | list[APITestScriptDraft] | list[APIScriptValidationResult] | list[WebPlaywrightReadiness] | list[WebPlaywrightScriptDraft] | list[WebPlaywrightValidationResult],
        path: Path | str,
        *,
        title: Optional[str] = None,
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.export_markdown_string(payload, title=title), encoding="utf-8")
        return output_path


def export_bundle_to_json_string(bundle: ExportBundle) -> str:
    return ManualQAExporter().export_json_string(bundle)


def export_bundle_to_json_file(bundle: ExportBundle, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(bundle, path)


def export_bundle_to_markdown_string(bundle: ExportBundle, *, title: Optional[str] = None) -> str:
    return ManualQAExporter().export_markdown_string(bundle, title=title)


def export_bundle_to_markdown_file(
    bundle: ExportBundle,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(bundle, path, title=title)


def export_suite_to_json_string(suite: TestSuite) -> str:
    return ManualQAExporter().export_json_string(suite)


def export_suite_to_json_file(suite: TestSuite, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(suite, path)


def export_suite_to_markdown_string(suite: TestSuite, *, title: Optional[str] = None) -> str:
    return ManualQAExporter().export_markdown_string(suite, title=title)


def export_suite_to_markdown_file(
    suite: TestSuite,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(suite, path, title=title)


def export_run_to_json_string(test_run: TestRun) -> str:
    return ManualQAExporter().export_json_string(test_run)


def export_run_to_json_file(test_run: TestRun, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(test_run, path)


def export_run_to_markdown_string(test_run: TestRun, *, title: Optional[str] = None) -> str:
    return ManualQAExporter().export_markdown_string(test_run, title=title)


def export_run_to_markdown_file(
    test_run: TestRun,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(test_run, path, title=title)


def export_summary_to_json_string(summary: RunSummary) -> str:
    return ManualQAExporter().export_json_string(summary)


def export_summary_to_json_file(summary: RunSummary, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(summary, path)


def export_summary_to_markdown_string(summary: RunSummary, *, title: Optional[str] = None) -> str:
    return ManualQAExporter().export_markdown_string(summary, title=title)


def export_summary_to_markdown_file(
    summary: RunSummary,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(summary, path, title=title)


def export_evidence_to_json_string(evidence: Evidence) -> str:
    return ManualQAExporter().export_json_string(evidence)


def export_evidence_to_json_file(evidence: Evidence, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(evidence, path)


def export_evidence_to_markdown_string(evidence: Evidence, *, title: Optional[str] = None) -> str:
    return ManualQAExporter().export_markdown_string(evidence, title=title)


def export_evidence_to_markdown_file(
    evidence: Evidence,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(evidence, path, title=title)


def export_bug_draft_to_json_string(bug_draft: BugDraft) -> str:
    return ManualQAExporter().export_json_string(bug_draft)


def export_bug_draft_to_json_file(bug_draft: BugDraft, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(bug_draft, path)


def export_bug_draft_to_markdown_string(
    bug_draft: BugDraft,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(bug_draft, title=title)


def export_bug_draft_to_markdown_file(
    bug_draft: BugDraft,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(bug_draft, path, title=title)


def export_failure_signature_to_json_string(signature: FailureSignature) -> str:
    return ManualQAExporter().export_json_string(signature)


def export_failure_signature_to_json_file(signature: FailureSignature, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(signature, path)


def export_failure_signature_to_markdown_string(
    signature: FailureSignature,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(signature, title=title)


def export_failure_signature_to_markdown_file(
    signature: FailureSignature,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(signature, path, title=title)


def export_failure_record_to_json_string(record: FailureRecord) -> str:
    return ManualQAExporter().export_json_string(record)


def export_failure_record_to_json_file(record: FailureRecord, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(record, path)


def export_failure_record_to_markdown_string(
    record: FailureRecord,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(record, title=title)


def export_failure_record_to_markdown_file(
    record: FailureRecord,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(record, path, title=title)


def export_failure_records_to_json_string(records: list[FailureRecord]) -> str:
    return ManualQAExporter().export_json_string(records)


def export_failure_records_to_json_file(records: list[FailureRecord], path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(records, path)


def export_failure_records_to_markdown_string(
    records: list[FailureRecord],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(records, title=title)


def export_failure_records_to_markdown_file(
    records: list[FailureRecord],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(records, path, title=title)


def export_automation_candidate_to_json_string(candidate: AutomationCandidate) -> str:
    return ManualQAExporter().export_json_string(candidate)


def export_automation_candidate_to_json_file(candidate: AutomationCandidate, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(candidate, path)


def export_automation_candidate_to_markdown_string(
    candidate: AutomationCandidate,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(candidate, title=title)


def export_automation_candidate_to_markdown_file(
    candidate: AutomationCandidate,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(candidate, path, title=title)


def export_automation_candidates_to_json_string(candidates: list[AutomationCandidate]) -> str:
    return ManualQAExporter().export_json_string(candidates)


def export_automation_candidates_to_json_file(candidates: list[AutomationCandidate], path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(candidates, path)


def export_automation_candidates_to_markdown_string(
    candidates: list[AutomationCandidate],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(candidates, title=title)


def export_automation_candidates_to_markdown_file(
    candidates: list[AutomationCandidate],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(candidates, path, title=title)


def export_script_gap_to_json_string(gap: ScriptGenerationGap) -> str:
    return ManualQAExporter().export_json_string(gap)


def export_script_gap_to_json_file(gap: ScriptGenerationGap, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(gap, path)


def export_script_gap_to_markdown_string(
    gap: ScriptGenerationGap,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(gap, title=title)


def export_script_gap_to_markdown_file(
    gap: ScriptGenerationGap,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(gap, path, title=title)


def export_script_readiness_to_json_string(readiness: ScriptGenerationReadiness) -> str:
    return ManualQAExporter().export_json_string(readiness)


def export_script_readiness_to_json_file(readiness: ScriptGenerationReadiness, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(readiness, path)


def export_script_readiness_to_markdown_string(
    readiness: ScriptGenerationReadiness,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(readiness, title=title)


def export_script_readiness_to_markdown_file(
    readiness: ScriptGenerationReadiness,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(readiness, path, title=title)


def export_script_readiness_list_to_json_string(items: list[ScriptGenerationReadiness]) -> str:
    return ManualQAExporter().export_json_string(items)


def export_script_readiness_list_to_json_file(items: list[ScriptGenerationReadiness], path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(items, path)


def export_script_readiness_list_to_markdown_string(
    items: list[ScriptGenerationReadiness],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(items, title=title)


def export_script_readiness_list_to_markdown_file(
    items: list[ScriptGenerationReadiness],
    path: Path | str,
    *,
    title: Optional[str] = None,
    ) -> Path:
        return ManualQAExporter().export_markdown_file(items, path, title=title)


def export_api_script_draft_to_json_string(draft: APITestScriptDraft) -> str:
    return ManualQAExporter().export_json_string(draft)


def export_api_script_draft_to_json_file(draft: APITestScriptDraft, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(draft, path)


def export_api_script_draft_to_markdown_string(
    draft: APITestScriptDraft,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(draft, title=title)


def export_api_script_draft_to_markdown_file(
    draft: APITestScriptDraft,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(draft, path, title=title)


def export_api_script_drafts_to_json_string(drafts: list[APITestScriptDraft]) -> str:
    return ManualQAExporter().export_json_string(drafts)


def export_api_script_drafts_to_json_file(drafts: list[APITestScriptDraft], path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(drafts, path)


def export_api_script_drafts_to_markdown_string(
    drafts: list[APITestScriptDraft],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(drafts, title=title)


def export_api_script_drafts_to_markdown_file(
    drafts: list[APITestScriptDraft],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(drafts, path, title=title)


def export_api_script_draft_to_python_file(draft: APITestScriptDraft, path: Path | str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(draft.script_content, encoding="utf-8")
    return output_path


def export_api_script_validation_issue_to_json_string(issue: APIScriptValidationIssue) -> str:
    return ManualQAExporter().export_json_string(issue)


def export_api_script_validation_issue_to_json_file(
    issue: APIScriptValidationIssue,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(issue, path)


def export_api_script_validation_issue_to_markdown_string(
    issue: APIScriptValidationIssue,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(issue, title=title)


def export_api_script_validation_issue_to_markdown_file(
    issue: APIScriptValidationIssue,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(issue, path, title=title)


def export_api_script_validation_result_to_json_string(result: APIScriptValidationResult) -> str:
    return ManualQAExporter().export_json_string(result)


def export_api_script_validation_result_to_json_file(
    result: APIScriptValidationResult,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(result, path)


def export_api_script_validation_result_to_markdown_string(
    result: APIScriptValidationResult,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(result, title=title)


def export_api_script_validation_result_to_markdown_file(
    result: APIScriptValidationResult,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(result, path, title=title)


def export_api_script_validation_results_to_json_string(
    results: list[APIScriptValidationResult],
) -> str:
    return ManualQAExporter().export_json_string(results)


def export_api_script_validation_results_to_json_file(
    results: list[APIScriptValidationResult],
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(results, path)


def export_api_script_validation_results_to_markdown_string(
    results: list[APIScriptValidationResult],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(results, title=title)


def export_api_script_validation_results_to_markdown_file(
    results: list[APIScriptValidationResult],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(results, path, title=title)


def export_api_script_package_manifest_to_json_string(manifest: APIScriptPackageManifest) -> str:
    return ManualQAExporter().export_json_string(manifest)


def export_api_script_package_manifest_to_json_file(
    manifest: APIScriptPackageManifest,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(manifest, path)


def export_api_script_package_manifest_to_markdown_string(
    manifest: APIScriptPackageManifest,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(manifest, title=title)


def export_api_script_package_manifest_to_markdown_file(
    manifest: APIScriptPackageManifest,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(manifest, path, title=title)


def export_web_playwright_gap_to_json_string(gap: WebPlaywrightGap) -> str:
    return ManualQAExporter().export_json_string(gap)


def export_web_playwright_gap_to_json_file(gap: WebPlaywrightGap, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(gap, path)


def export_web_playwright_gap_to_markdown_string(
    gap: WebPlaywrightGap,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(gap, title=title)


def export_web_playwright_gap_to_markdown_file(
    gap: WebPlaywrightGap,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(gap, path, title=title)


def export_web_playwright_readiness_to_json_string(readiness: WebPlaywrightReadiness) -> str:
    return ManualQAExporter().export_json_string(readiness)


def export_web_playwright_readiness_to_json_file(
    readiness: WebPlaywrightReadiness,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(readiness, path)


def export_web_playwright_readiness_to_markdown_string(
    readiness: WebPlaywrightReadiness,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(readiness, title=title)


def export_web_playwright_readiness_to_markdown_file(
    readiness: WebPlaywrightReadiness,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(readiness, path, title=title)


def export_web_playwright_readiness_list_to_json_string(items: list[WebPlaywrightReadiness]) -> str:
    return ManualQAExporter().export_json_string(items)


def export_web_playwright_readiness_list_to_json_file(
    items: list[WebPlaywrightReadiness],
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(items, path)


def export_web_playwright_readiness_list_to_markdown_string(
    items: list[WebPlaywrightReadiness],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(items, title=title)


def export_web_playwright_readiness_list_to_markdown_file(
    items: list[WebPlaywrightReadiness],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(items, path, title=title)


def export_web_playwright_script_draft_to_json_string(draft: WebPlaywrightScriptDraft) -> str:
    return ManualQAExporter().export_json_string(draft)


def export_web_playwright_script_draft_to_json_file(
    draft: WebPlaywrightScriptDraft,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(draft, path)


def export_web_playwright_script_draft_to_markdown_string(
    draft: WebPlaywrightScriptDraft,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(draft, title=title)


def export_web_playwright_script_draft_to_markdown_file(
    draft: WebPlaywrightScriptDraft,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(draft, path, title=title)


def export_web_playwright_script_drafts_to_json_string(
    drafts: list[WebPlaywrightScriptDraft],
) -> str:
    return ManualQAExporter().export_json_string(drafts)


def export_web_playwright_script_drafts_to_json_file(
    drafts: list[WebPlaywrightScriptDraft],
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(drafts, path)


def export_web_playwright_script_drafts_to_markdown_string(
    drafts: list[WebPlaywrightScriptDraft],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(drafts, title=title)


def export_web_playwright_script_drafts_to_markdown_file(
    drafts: list[WebPlaywrightScriptDraft],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(drafts, path, title=title)


def export_web_playwright_script_draft_to_python_file(
    draft: WebPlaywrightScriptDraft,
    path: Path | str,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(draft.script_content, encoding="utf-8")
    return output_path


def export_web_playwright_validation_issue_to_json_string(issue: WebPlaywrightValidationIssue) -> str:
    return ManualQAExporter().export_json_string(issue)


def export_web_playwright_validation_issue_to_json_file(
    issue: WebPlaywrightValidationIssue,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(issue, path)


def export_web_playwright_validation_issue_to_markdown_string(
    issue: WebPlaywrightValidationIssue,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(issue, title=title)


def export_web_playwright_validation_issue_to_markdown_file(
    issue: WebPlaywrightValidationIssue,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(issue, path, title=title)


def export_web_playwright_validation_result_to_json_string(result: WebPlaywrightValidationResult) -> str:
    return ManualQAExporter().export_json_string(result)


def export_web_playwright_validation_result_to_json_file(
    result: WebPlaywrightValidationResult,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(result, path)


def export_web_playwright_validation_result_to_markdown_string(
    result: WebPlaywrightValidationResult,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(result, title=title)


def export_web_playwright_validation_result_to_markdown_file(
    result: WebPlaywrightValidationResult,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(result, path, title=title)


def export_web_playwright_validation_results_to_json_string(
    results: list[WebPlaywrightValidationResult],
) -> str:
    return ManualQAExporter().export_json_string(results)


def export_web_playwright_validation_results_to_json_file(
    results: list[WebPlaywrightValidationResult],
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(results, path)


def export_web_playwright_validation_results_to_markdown_string(
    results: list[WebPlaywrightValidationResult],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(results, title=title)


def export_web_playwright_validation_results_to_markdown_file(
    results: list[WebPlaywrightValidationResult],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(results, path, title=title)


def export_web_playwright_package_manifest_to_json_string(
    manifest: WebPlaywrightPackageManifest,
) -> str:
    return ManualQAExporter().export_json_string(manifest)


def export_web_playwright_package_manifest_to_json_file(
    manifest: WebPlaywrightPackageManifest,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(manifest, path)


def export_web_playwright_package_manifest_to_markdown_string(
    manifest: WebPlaywrightPackageManifest,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(manifest, title=title)


def export_web_playwright_package_manifest_to_markdown_file(
    manifest: WebPlaywrightPackageManifest,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(manifest, path, title=title)


def export_draft_package_group_summary_to_json_string(group: DraftPackageGroupSummary) -> str:
    return ManualQAExporter().export_json_string(group)


def export_draft_package_group_summary_to_json_file(
    group: DraftPackageGroupSummary,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(group, path)


def export_draft_package_group_summary_to_markdown_string(
    group: DraftPackageGroupSummary,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(group, title=title)


def export_draft_package_group_summary_to_markdown_file(
    group: DraftPackageGroupSummary,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(group, path, title=title)


def export_unified_draft_package_summary_to_json_string(
    summary: UnifiedDraftPackageSummary,
) -> str:
    return ManualQAExporter().export_json_string(summary)


def export_unified_draft_package_summary_to_json_file(
    summary: UnifiedDraftPackageSummary,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(summary, path)


def export_unified_draft_package_summary_to_markdown_string(
    summary: UnifiedDraftPackageSummary,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(summary, title=title)


def export_unified_draft_package_summary_to_markdown_file(
    summary: UnifiedDraftPackageSummary,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(summary, path, title=title)


def export_execution_safety_policy_to_json_string(policy: ExecutionSafetyPolicy) -> str:
    return ManualQAExporter().export_json_string(policy)


def export_execution_safety_policy_to_json_file(
    policy: ExecutionSafetyPolicy,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(policy, path)


def export_execution_safety_policy_to_markdown_string(
    policy: ExecutionSafetyPolicy,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(policy, title=title)


def export_execution_safety_policy_to_markdown_file(
    policy: ExecutionSafetyPolicy,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(policy, path, title=title)


def export_execution_target_to_json_string(target: ExecutionTarget) -> str:
    return ManualQAExporter().export_json_string(target)


def export_execution_target_to_json_file(target: ExecutionTarget, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(target, path)


def export_execution_target_to_markdown_string(
    target: ExecutionTarget,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(target, title=title)


def export_execution_target_to_markdown_file(
    target: ExecutionTarget,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(target, path, title=title)


def export_execution_preflight_issue_to_json_string(issue: ExecutionPreflightIssue) -> str:
    return ManualQAExporter().export_json_string(issue)


def export_execution_preflight_issue_to_json_file(
    issue: ExecutionPreflightIssue,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(issue, path)


def export_execution_preflight_issue_to_markdown_string(
    issue: ExecutionPreflightIssue,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(issue, title=title)


def export_execution_preflight_issue_to_markdown_file(
    issue: ExecutionPreflightIssue,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(issue, path, title=title)


def export_execution_preflight_result_to_json_string(result: ExecutionPreflightResult) -> str:
    return ManualQAExporter().export_json_string(result)


def export_execution_preflight_result_to_json_file(
    result: ExecutionPreflightResult,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(result, path)


def export_execution_preflight_result_to_markdown_string(
    result: ExecutionPreflightResult,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(result, title=title)


def export_execution_preflight_result_to_markdown_file(
    result: ExecutionPreflightResult,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(result, path, title=title)


def export_execution_plan_to_json_string(plan: ExecutionPlan) -> str:
    return ManualQAExporter().export_json_string(plan)


def export_execution_plan_to_json_file(plan: ExecutionPlan, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(plan, path)


def export_execution_plan_to_markdown_string(
    plan: ExecutionPlan,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(plan, title=title)


def export_execution_plan_to_markdown_file(
    plan: ExecutionPlan,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(plan, path, title=title)


def export_api_execution_evidence_to_json_string(evidence: APIExecutionEvidence) -> str:
    return ManualQAExporter().export_json_string(evidence)


def export_api_execution_evidence_to_json_file(
    evidence: APIExecutionEvidence,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(evidence, path)


def export_api_execution_evidence_to_markdown_string(
    evidence: APIExecutionEvidence,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(evidence, title=title)


def export_api_execution_evidence_to_markdown_file(
    evidence: APIExecutionEvidence,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(evidence, path, title=title)


def export_api_execution_evidence_list_to_json_string(evidence_items: list[APIExecutionEvidence]) -> str:
    return ManualQAExporter().export_json_string(evidence_items)


def export_api_execution_evidence_list_to_json_file(
    evidence_items: list[APIExecutionEvidence],
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(evidence_items, path)


def export_api_execution_evidence_list_to_markdown_string(
    evidence_items: list[APIExecutionEvidence],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(evidence_items, title=title)


def export_api_execution_evidence_list_to_markdown_file(
    evidence_items: list[APIExecutionEvidence],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(evidence_items, path, title=title)


def export_api_execution_summary_to_json_string(summary: APIExecutionSummary) -> str:
    return ManualQAExporter().export_json_string(summary)


def export_api_execution_summary_to_json_file(
    summary: APIExecutionSummary,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(summary, path)


def export_api_execution_summary_to_markdown_string(
    summary: APIExecutionSummary,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(summary, title=title)


def export_api_execution_summary_to_markdown_file(
    summary: APIExecutionSummary,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(summary, path, title=title)


def export_api_execution_evidence_report_to_markdown_string(
    report: dict[str, object],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(report, title=title)


def export_api_execution_evidence_report_to_markdown_file(
    report: dict[str, object],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(report, path, title=title)


def export_api_execution_request_to_json_string(request: APIExecutionRequest) -> str:
    return ManualQAExporter().export_json_string(request)


def export_api_execution_request_to_json_file(
    request: APIExecutionRequest,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(request, path)


def export_api_execution_request_to_markdown_string(
    request: APIExecutionRequest,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(request, title=title)


def export_api_execution_request_to_markdown_file(
    request: APIExecutionRequest,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(request, path, title=title)


def export_api_execution_result_to_json_string(result: APIExecutionResult) -> str:
    return ManualQAExporter().export_json_string(result)


def export_api_execution_result_to_json_file(
    result: APIExecutionResult,
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(result, path)


def export_api_execution_result_to_markdown_string(
    result: APIExecutionResult,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(result, title=title)


def export_api_execution_result_to_markdown_file(
    result: APIExecutionResult,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(result, path, title=title)


def export_api_execution_results_to_json_string(results: list[APIExecutionResult]) -> str:
    return ManualQAExporter().export_json_string(results)


def export_api_execution_results_to_json_file(
    results: list[APIExecutionResult],
    path: Path | str,
) -> Path:
    return ManualQAExporter().export_json_file(results, path)


def export_api_execution_results_to_markdown_string(
    results: list[APIExecutionResult],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(results, title=title)


def export_api_execution_results_to_markdown_file(
    results: list[APIExecutionResult],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(results, path, title=title)
